"""
hawkes_r.py — 확산 모델 대안: Hawkes 외생/내생 분해의 분기비(branching ratio)와 과분산 보정 사후확률 (2026-10-26 추가)

왜: 기존 R̂는 6시간 창의 부모→자식 비율을 3시간 합산한 Gamma-포아송 사후분포다(alerts.py). 실제 SNS는 소수 대형 계정이 전파를
    주도해 과분산이 크므로 포아송 구간이 너무 좁고(PRD 한계 5), 공작 계정의 '투입'(외생)과 일반 사용자 간 '전파'(내생)를 같은
    숫자로 센다. 자기여기 점과정(Hawkes)은 λ(t) = μ + Σ α·exp(-β(t-tᵢ)) 로 외생 μ 와 내생 α를 나누고, 분기비 n* = α/β 가
    "한 글이 평균 몇 개의 후속 글을 낳나" = R의 자리를 대신한다(SEISMIC·HIP 계열, 서베이 arXiv 2005.11041).
방법   서사별 한국어 글 중 '그 시각에 의심 집단이 아닌 계정'(alerts.suspect_asof)의 글만 사건으로 쓴다(공작 투입은 μ에 남기지 않고 제외 —
       R이 일반 사용자 간 전파라는 기존 정의와 같음). 각 정시 t마다 직전 FIT_H 시간의 사건으로 (μ, α, β) 최대우도 추정 → n* = α/β.
       β는 격자(반감기 10분~6시간)로 두고 μ, α만 수치 최적화(안정성). 사건이 MIN_EVENTS 미만이면 비움.
과분산  기존 3시간 합산의 부모·자식 수에서 부모별 자식 수의 분산/평균 φ를 재고(φ>1 과분산), 유효 표본을 φ로 나눈 Gamma 사후확률
       p_gt08_nb 를 함께 낸다(준우도 보정). φ≤1이면 기존 값과 같다.
출력   out/r_series_hawkes.csv  서사×시각: n_events, mu, alpha, beta_halflife_min, n_star, p_gt08_pois(기존), phi, p_gt08_nb, n_star_gt08
       out/hawkes_summary.json  서사별 첫 '내생 확산 임박'(n* ≥ 0.8 연속 2시간) 시각 vs 기존 ALERT 41시
실행   python hawkes_r.py     (필요: pandas numpy scipy)   기존 out/·동결 숫자는 건드리지 않는다.
정직하게 합성 데이터의 전파는 생성기가 정한 R 곡선을 따르므로 n*가 그것을 재현하는지 '자기 일치' 확인일 뿐이다. 실데이터 라벨 없음.
"""
import json, os, sys
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import gamma as _gamma

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import alerts as AL
FIT_H = 12
MIN_EVENTS = 20
HALFLIVES = [10, 30, 60, 180, 360]      # 분


def nll(params, t, T, beta):
    mu, alpha = np.exp(params)
    # 재귀로 A_i = Σ_{j<i} exp(-β(t_i - t_j))
    A = np.zeros(len(t))
    for i in range(1, len(t)):
        A[i] = np.exp(-beta * (t[i] - t[i - 1])) * (1 + A[i - 1])
    lam = mu + alpha * A
    comp = mu * T + (alpha / beta) * np.sum(1 - np.exp(-beta * (T - t)))
    return -(np.sum(np.log(lam)) - comp)


def fit(t, T):
    best = None
    for hl in HALFLIVES:
        beta = np.log(2) / hl
        x0 = np.log([max(len(t) / T, 1e-3), 0.1 * beta])
        r = minimize(nll, x0, args=(t, T, beta), method="L-BFGS-B")
        if best is None or r.fun < best[0]:
            best = (r.fun, np.exp(r.x[0]), np.exp(r.x[1]), beta, hl)
    _, mu, alpha, beta, hl = best
    return mu, alpha, beta, hl, alpha / beta


def main():
    P, S, B, M, SRC = AL.load()
    t0 = P[P.narrative_id >= 0].ts.min().floor("D")
    grid = pd.date_range(t0 + AL.STEP, P[P.narrative_id >= 0].ts.max().ceil("h"), freq=AL.STEP)
    rows, summ = [], {}
    for nid in sorted(P[P.narrative_id >= 0].narrative_id.unique()):
        gall = P[P.narrative_id == nid]; g = gall[gall.lang == "ko"].sort_values("ts")
        joined = AL.suspect_asof(S, M, nid)
        rs = AL.pool_posterior(AL.r_series(g, joined, grid))
        first_endo = None; streak = 0
        for i, t in enumerate(grid):
            ok = g.account_id.map(lambda a: (joined.get(a) is None) or pd.isna(joined.get(a)) or joined.get(a) > t).astype(bool).values
            e = g[ok & (g.ts >= t - pd.Timedelta(hours=FIT_H)) & (g.ts < t)]
            rec = dict(narrative_id=int(nid), ts=t, hour=int((t - t0) / pd.Timedelta(hours=1)), n_events=len(e),
                       p_gt08_pois=rs.p_gt08.iloc[i], r_pool=rs.r_pool.iloc[i])
            if len(e) >= MIN_EVENTS:
                tt = ((e.ts - (t - pd.Timedelta(hours=FIT_H))) / pd.Timedelta(minutes=1)).values.astype(float)
                tt = np.sort(tt + np.random.default_rng(0).uniform(0, 1e-3, len(tt)))
                mu, alpha, beta, hl, nstar = fit(tt, FIT_H * 60.0)
                rec.update(mu_per_min=round(mu, 4), alpha=round(alpha, 4), beta_halflife_min=hl, n_star=round(nstar, 3))
                streak = streak + 1 if nstar >= AL.R_ALERT else 0
                if first_endo is None and streak >= 2 and rec["hour"] > 0:
                    first_endo = rec["hour"]
            # 과분산 보정: 최근 POOL_H 시간의 부모별 자식 수 분산/평균
            par = g[(g.ts >= t - pd.Timedelta(hours=AL.POOL_H) - AL.PAR_LO) & (g.ts < t - AL.PAR_HI)]
            par = par[par.account_id.map(lambda a: (joined.get(a) is None) or pd.isna(joined.get(a)) or joined.get(a) > t).astype(bool).values] if len(par) else par
            if len(par) >= AL.MIN_PARENTS:
                ch = g[(g.ts < t) & g.parent_id.isin(set(par.post_id))]
                cnt = ch.parent_id.value_counts().reindex(par.post_id, fill_value=0).values.astype(float)
                m = cnt.mean(); phi = (cnt.var() / m) if m > 0 else 1.0
                phi = max(1.0, float(phi))
                a_, b_ = AL.PRIOR_A + cnt.sum() / phi, AL.PRIOR_B + len(par) / phi
                rec.update(phi=round(phi, 2), p_gt08_nb=float(_gamma.sf(AL.R_ALERT, a_, scale=1 / b_)), p_gt1_nb=float(_gamma.sf(AL.R_CRIT, a_, scale=1 / b_)))
            rows.append(rec)
        R = pd.DataFrame([r for r in rows if r["narrative_id"] == nid])
        fa_pois = R[(R.p_gt08_pois >= AL.P_LEVEL)].hour.min() if (R.p_gt08_pois >= AL.P_LEVEL).any() else None
        fa_nb = R[(R.get("p_gt08_nb", pd.Series(dtype=float)) >= AL.P_LEVEL)].hour.min() if "p_gt08_nb" in R and (R.p_gt08_nb >= AL.P_LEVEL).any() else None
        summ[int(nid)] = dict(first_endogenous_nstar08=first_endo, first_p08_poisson=(int(fa_pois) if fa_pois is not None else None),
                              first_p08_overdispersed=(int(fa_nb) if fa_nb is not None else None),
                              phi_median=(round(float(R.phi.median()), 2) if "phi" in R else None),
                              nstar_at_41=(float(R[R.hour == 41].n_star.iloc[0]) if "n_star" in R and (R.hour == 41).any() and pd.notna(R[R.hour == 41].n_star.iloc[0]) else None))
        print(f"narrative {nid}: {summ[int(nid)]}", flush=True)
    pd.DataFrame(rows).to_csv(os.path.join(AL.OUT, "r_series_hawkes.csv"), index=False)
    json.dump(dict(params=dict(FIT_H=FIT_H, MIN_EVENTS=MIN_EVENTS, HALFLIVES=HALFLIVES), narratives=summ),
              open(os.path.join(AL.OUT, "hawkes_summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
