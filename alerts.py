"""
alerts.py — M4 일반 사용자 간 재생산수 R̂ · 경보 · 근거 카드

입력 : data/posts.csv (truth_* 읽지 않음), out/posts_nar.csv, out/accounts_score.csv,
       out/bursts.csv, out/burst_members.csv, out/sources.json
출력 : out/r_series.csv   서사×시각(1시간 간격) R̂, 의심 집단 크기, 경보 단계
       out/alerts.json    서사별 근거 카드 (첫 경보 시점 기준)

R̂(t) 정의 — 시각 t에 실제로 알 수 있는 정보만 사용
  부모 창  [t-12h, t-6h) 에 올라온 '일반 사용자' 게시물 수 = 부모 수
  자식     그 부모를 parent_id로 가리키는 '일반 사용자' 게시물 중 t 이전에 관측된 것
  R̂(t) = 자식 수 / 부모 수   (부모 수 < MIN_PARENTS 이면 계산 안 함)
  '일반 사용자' = 시각 t 기준 의심 집단(suspected 이면서 burst 2회가 t 이전에 끝난 계정)이 아닌 계정
  한계: 6시간 뒤에 올라오는 자식은 놓친다(과소추정). 실제 플랫폼에서는 리포스트·답글·인용으로 parent를 얻는다.

경보 단계
  WATCH    반복 조정 집단(의심 계정 >= MIN_SUSPECTS)이 이 서사를 밀고 있음
  ALERT    WATCH + P(R > 0.8) >= 0.5 (최근 3시간 합산 사후분포) → 일반 사용자 사이 자생 확산에 근접. 외국발이라고 말하며 대응하기 좋은 마지막 구간
  관할 제한: 외국어 출처가 연결되지 않은 서사는 조정 행위가 보여도 REVIEW(국내 사안 — 군 관할 아님)까지만 올린다
  R̂ 불확실성: 자식 수 ~ Poisson(R × 부모 수), 사전분포 Gamma(1, 2) → 사후 Gamma(1+자식, 2+부모)의 80% 구간과 P(R>1)
              경보는 점추정이 아니라 사후확률로 판단한다 (한 시간짜리 표본이 튀어 울리는 경보를 막기 위해).
              과분산이 큰 실데이터에서는 음이항 모형으로 구간을 더 넓혀야 한다(다음 단계).
  CRITICAL WATCH + P(R > 1.0) >= 0.5  → 자생 확산(출처 세탁 진행)
  REVIEW   반복 조정은 없지만 1회성 대규모 동시 게시(review 계정 >= MIN_SUSPECTS) — 팬덤·캠페인 등 정상일 수 있음
실행 : python alerts.py
"""
import json, os
import numpy as np
import pandas as pd
from scipy.stats import gamma as _gamma

HERE = os.path.dirname(os.path.abspath(__file__))
DATA, OUT = os.path.join(HERE, "data"), os.path.join(HERE, "out")
STEP = pd.Timedelta(hours=1)
PAR_LO, PAR_HI = pd.Timedelta(hours=12), pd.Timedelta(hours=6)
MIN_PARENTS = 5
MIN_SUSPECTS = 5
R_ALERT, R_CRIT = 0.8, 1.0
PRIOR_A, PRIOR_B = 1.0, 2.0      # R 사전분포 Gamma(1, 2): 평균 0.5, 부모 2건 분량의 약한 사전정보
POOL_H = 3                       # R 추정에 최근 3시간을 합산 (시간 단위 출렁임 완화)
P_LEVEL = 0.5                    # 경보 판단: 사후확률 P(R > 기준) >= 0.5
LEVELS = ["NONE", "REVIEW", "WATCH", "ALERT", "CRITICAL"]
ACTIONS = {
    "CRITICAL": ["출처(외국어 원문)와 확산 경로를 근거로 즉시 상부 보고",
                 "사실관계 공식 설명 준비 — 서사의 핵심 주장에 대응, 일반 사용자 비난 금지",
                 "플랫폼에 반복 조정 계정 묶음 신고(CIB 정책 근거)"],
    "ALERT": ["출처 증거 확보·봉인 (외국발이라고 말하며 대응하기 좋은 구간 — 일반 시민 확산 전)",
              "사전 반박(prebunking) 문안 준비 — 수법 공개 중심",
              "플랫폼 신고 준비, 확산 추세 1~2시간 단위 재확인"],
    "WATCH": ["관찰 유지 — 대응하지 않기도 선택지(작은 공작을 키우지 않기 위해)",
              "출처 후보와 burst 기록 보존"],
    "REVIEW": ["분석가 확인 — 정상적인 집단 행동(팬덤·캠페인)일 가능성 높음",
               "외국어 출처가 없으면 국내 사안 — 군 관할 아님, 필요 시 관계 기관 이관 검토",
               "외국어 출처·반복 조정 없음을 기록"],
}


# DISARM 후보 기법 (공식 저장소 techniques_index 대조 완료, 2026-10-10). 최종 태깅은 분석관이 한다.
DISARM = [
    ("burst", "T0049.005", "Conduct Swarming", "여러 계정이 짧은 시간에 몰려 같은 서사를 게시"),
    ("copypasta", "T0084.001", "Use Copypasta", "burst 안에서 거의 같은 문장을 여러 계정이 반복"),
    ("url", "T0049.003", "Bots Amplify via Automated Forwarding and Reposting", "같은 링크를 여러 계정이 동시에 재게시 (자동화 여부는 미확인)"),
    ("young", "T0092", "Build Network", "신생 계정들이 한 집단으로 함께 움직임"),
    ("foreign", "T0101", "Create Localised Content", "외국어 원문이 한국어 원고로 바뀌어 등장"),
]


def disarm_candidates(n_bursts, max_text_sim, url_share, young, foreign_linked):
    on = dict(burst=n_bursts >= 1, copypasta=max_text_sim >= 0.5, url=url_share >= 0.5,
              young=young >= 0.5, foreign=foreign_linked and n_bursts >= 1)
    return [dict(id=i, name=n, why=w) for k, i, n, w in DISARM if on[k]]


def volume_alarm_hour(hourly, k=3, min_count=20, warmup=6):
    """비교용 단순 볼륨 감시: 시간당 게시물 >= min_count 이면서 직전 24시간 중앙값의 k배 이상. 라벨을 쓰지 않는다."""
    hourly = list(hourly)
    for h in range(warmup, len(hourly)):
        prev = sorted(hourly[max(0, h - 24):h])
        med = prev[len(prev) // 2] if prev else 0
        if hourly[h] >= min_count and hourly[h] >= k * max(med, 1):
            return h
    return None


def load():
    P = pd.read_csv(os.path.join(DATA, "posts.csv"), parse_dates=["ts"], keep_default_na=False,
                    usecols=["post_id", "ts", "account_id", "lang", "text", "url", "parent_id"])
    N = pd.read_csv(os.path.join(OUT, "posts_nar.csv"))
    P = P.merge(N[["post_id", "narrative_id"]], on="post_id")
    S = pd.read_csv(os.path.join(OUT, "accounts_score.csv"), keep_default_na=False)
    B = pd.read_csv(os.path.join(OUT, "bursts.csv"), parse_dates=["start", "end"], keep_default_na=False)
    M = pd.read_csv(os.path.join(OUT, "burst_members.csv"), parse_dates=["burst_end"])
    with open(os.path.join(OUT, "sources.json"), encoding="utf-8") as f:
        SRC = json.load(f)
    return P, S, B, M, SRC


def suspect_asof(S, M, nid):
    """계정 → 의심 집단에 들어간 시각 (두 번째 burst 종료 시각). suspected 아닌 계정은 없음"""
    sus = set(S[(S.narrative_id == nid) & (S.tier == "suspected")].account_id)
    m = M[(M.narrative_id == nid) & (M.account_id.isin(sus))].sort_values("burst_end")
    return m.groupby("account_id").burst_end.apply(lambda s: s.iloc[1] if len(s) >= 2 else pd.NaT).dropna().to_dict()


def r_series(g, joined_at, grid):
    """g: 한 서사의 한국어 게시물. joined_at: {account: 의심 집단 편입 시각}. 정답 R 계산에도 재사용"""
    g = g.sort_values("ts")
    rows = []
    for t in grid:
        def ordinary(acc):
            j = joined_at.get(acc)
            return j is None or pd.isna(j) or j > t
        par = g[(g.ts >= t - PAR_LO) & (g.ts < t - PAR_HI)]
        par = par[par.account_id.map(ordinary).astype(bool).values] if len(par) else par
        pids = set(par.post_id)
        ch = g[(g.ts < t) & (g.parent_id.isin(pids))]
        ch = ch[ch.account_id.map(ordinary).astype(bool).values] if len(ch) else ch
        n_par, n_ch = len(par), len(ch)
        rows.append(dict(ts=t, n_parents=n_par, n_children=n_ch,
                         r_hat=(n_ch / n_par) if n_par >= MIN_PARENTS else np.nan,
                         n_susp=sum(1 for v in joined_at.values() if pd.notna(v) and v <= t),
                         n_posts_sofar=int((g.ts < t).sum())))
    return pd.DataFrame(rows)


def pool_posterior(rs, hours=None):
    """최근 hours시간의 부모·자식을 합산해 R의 사후분포 Gamma(A+자식, B+부모)를 계산"""
    hours = hours or POOL_H
    cp = rs.n_parents.rolling(hours, min_periods=1).sum()
    cc = rs.n_children.rolling(hours, min_periods=1).sum()
    a_, b_ = PRIOR_A + cc, PRIOR_B + cp
    ok = cp >= MIN_PARENTS
    rs["r_pool"] = np.where(ok, cc / cp.clip(lower=1), np.nan)
    rs["r_lo"] = np.where(ok, _gamma.ppf(0.1, a_, scale=1 / b_), np.nan)
    rs["r_hi"] = np.where(ok, _gamma.ppf(0.9, a_, scale=1 / b_), np.nan)
    rs["p_gt08"] = np.where(ok, _gamma.sf(R_ALERT, a_, scale=1 / b_), np.nan)
    rs["p_gt1"] = np.where(ok, _gamma.sf(R_CRIT, a_, scale=1 / b_), np.nan)
    return rs


def main():
    P, S, B, M, SRC = load()
    P = P[(P.narrative_id >= 0)]
    t0 = P.ts.min().floor("D")
    grid = pd.date_range(t0 + STEP, P.ts.max().ceil("h"), freq=STEP)
    series, cards = [], []
    for nid, gall in P.groupby("narrative_id"):
        g = gall[gall.lang == "ko"]
        joined = suspect_asof(S, M, nid)
        rs = r_series(g, joined, grid)
        rs = pool_posterior(rs)
        rs["narrative_id"] = nid
        rs["hour"] = ((rs.ts - t0) / pd.Timedelta(hours=1)).astype(int)
        # 1회성 대규모 동시 게시(REVIEW): review 계정이 한 burst에 MIN_SUSPECTS 이상
        rev = set(S[(S.narrative_id == nid) & (S.tier == "review")].account_id)
        mb = M[(M.narrative_id == nid) & (M.account_id.isin(rev))]
        rev_time = mb.groupby("burst_id").filter(lambda x: len(x) >= MIN_SUSPECTS).burst_end.min() \
            if len(mb) else pd.NaT

        fo_first = gall[gall.lang != "ko"].ts.min()    # 외국어 출처가 서사에 처음 나타난 시각
        rs["foreign_seen"] = rs.ts > fo_first if pd.notna(fo_first) else False
        rs["domestic"] = (rs.n_susp >= MIN_SUSPECTS) & ~rs.foreign_seen

        def level(r):
            if r.n_susp >= MIN_SUSPECTS and not r.foreign_seen:
                return "REVIEW"                      # 국내 사안: 군 관할 아님 → 검토 권장까지만
            if r.n_susp >= MIN_SUSPECTS:
                if pd.notna(r.p_gt1) and r.p_gt1 >= P_LEVEL: return "CRITICAL"
                if pd.notna(r.p_gt08) and r.p_gt08 >= P_LEVEL: return "ALERT"
                return "WATCH"
            if pd.notna(rev_time) and r.ts >= rev_time: return "REVIEW"
            return "NONE"
        rs["level"] = rs.apply(level, axis=1)
        # 한번 올라간 경보 단계는 자동으로 내려가지 않는다 (해제는 분석관 판단). R̂의 시간 단위 출렁임 대응
        idx = rs.level.map(LEVELS.index).cummax()
        rs["level"] = idx.map(lambda i: LEVELS[i])
        series.append(rs)

        if (rs.level == "NONE").all():
            continue
        cards.append(make_card(nid, g, gall, rs, S, B, SRC.get(str(nid)), t0))

    R = pd.concat(series, ignore_index=True)
    R.to_csv(os.path.join(OUT, "r_series.csv"), index=False)
    cards.sort(key=lambda c: -LEVELS.index(c["max_level"]))
    with open(os.path.join(OUT, "alerts.json"), "w", encoding="utf-8") as f:
        json.dump(cards, f, ensure_ascii=False, indent=2, default=str)
    for c in cards:
        print(f"N{c['narrative_id']}: max={c['max_level']:8s} first_watch={c['first']['WATCH']}  "
              f"first_alert={c['first']['ALERT']}  first_critical={c['first']['CRITICAL']}  conf={c['confidence']}")


def first_time(rs, lv):
    hit = rs[rs.level.map(LEVELS.index) >= LEVELS.index(lv)]
    return None if hit.empty else str(hit.ts.iloc[0])


def samples_for(kg, bb):
    """서사 예시: 동시 게시 burst에 올라온 글을 우선 (잡담이 섞인 서사에서도 문제 글을 보여주기 위해)"""
    if len(bb):
        b = bb.iloc[0]
        inb = kg[(kg.ts >= b.start) & (kg.ts <= b.end)]
        if len(inb):
            return list(inb.text.drop_duplicates().head(3))
    return list(kg.text.drop_duplicates().head(3))


def make_card(nid, g, gall, rs, S, B, src, t0):
    lv_max = max(rs.level, key=LEVELS.index)
    first = {lv: first_time(rs, lv) for lv in ["REVIEW", "WATCH", "ALERT", "CRITICAL"]}
    anchor_ts = pd.Timestamp(first["ALERT"] or first["WATCH"] or first["REVIEW"])
    at = rs[rs.ts == anchor_ts].iloc[0]

    # R̂ 추세: 직전 12시간 선형 추세로 1 도달까지 남은 시간 추정 (추정치임을 카드에 명시)
    w = rs[(rs.ts <= anchor_ts) & (rs.ts > anchor_ts - pd.Timedelta(hours=12))].dropna(subset=["r_pool"])
    slope, eta = None, None
    if len(w) >= 4:
        x = (w.ts - w.ts.iloc[0]) / pd.Timedelta(hours=1)
        slope = float(np.polyfit(x, w.r_pool, 1)[0])
        if slope > 0 and pd.notna(at.r_pool) and at.r_pool < 1:
            eta = round((1 - at.r_pool) / slope, 1)

    s = S[(S.narrative_id == nid)]
    sus = s[s.tier == "suspected"]
    bb = B[B.narrative_id == nid]
    coord = float(sus.score.mean()) if len(sus) else 0.0
    foreign = bool(src and src.get("n_foreign", 0) > 0 and (src.get("lead_hours") or 0) > 0)
    r_now = float(at.r_pool) if pd.notna(at.r_pool) else 0.0
    conf_v = 0.4 * coord + 0.3 * float(foreign) + 0.3 * min(r_now, 1.0)
    conf = "높음" if conf_v >= 0.7 else ("중간" if conf_v >= 0.45 else "낮음")

    kg = g.sort_values("ts")
    return dict(
        narrative_id=int(nid), max_level=lv_max, first=first,
        anchor_level=str(at.level), anchor_ts=str(anchor_ts),
        anchor_hour=int((anchor_ts - t0) / pd.Timedelta(hours=1)),
        narrative_samples=samples_for(kg, bb),
        n_posts_ko_total=int(len(kg)), n_posts_at_anchor=int((kg.ts < anchor_ts).sum()),
        source=dict(foreign_linked=foreign,
                    lead_hours=src.get("lead_hours") if src else None,
                    foreign=(src.get("foreign") if src else []),
                    shared_urls=(src.get("shared_urls") if src else {})),
        bursts=[dict(start=str(r.start), end=str(r.end), n_accounts=int(r.n_accounts),
                     text_sim=float(r.mean_text_sim), url=r.top_url) for r in bb.itertuples()],
        group=dict(n_suspected=int(len(sus)), n_review=int((s.tier == "review").sum()),
                   mean_score=round(coord, 3),
                   signal_means={k: round(float(sus[k].mean()), 3) if len(sus) else 0.0
                                 for k in ["young", "burst_sim", "url_share"]},
                   mean_bursts=round(float(sus.n_bursts.mean()), 2) if len(sus) else 0.0,
                   example_evidence=list(sus.sort_values("score", ascending=False).evidence.head(3))),
        r=dict(r_hat=round(r_now, 3), p_gt1=None if pd.isna(at.p_gt1) else round(float(at.p_gt1), 3),
               interval80=None if pd.isna(at.r_lo) else [round(float(at.r_lo), 2), round(float(at.r_hi), 2)],
               slope_per_h=None if slope is None else round(slope, 4),
               eta_to_1_hours=eta, note="R̂는 최근 3시간 합산·6시간 창 기반(과소추정 경향), 구간은 Gamma 사후분포 80%, 1 도달 시각은 선형 추세 추정치"),
        confidence=conf, confidence_value=round(conf_v, 3),
        recommended=ACTIONS.get(str(at.level), []),
        domestic=bool(rs.domestic.any()),
        jurisdiction=("외국발 서사 유입 — 탐지 대상" if foreign else
                      ("국내 사안 — 외국어 출처 연결 없음. 군 관할 아님(필요 시 관계 기관 이관 검토)" if rs.domestic.any()
                       else "외국어 출처 없음 — 국내 집단 행동으로 보임(검토 권장, 군 관할 아님)")),
        disclaimer="이 카드는 판정이 아니라 분석가 보조 자료입니다. 계정은 가명 ID이며 일반 사용자는 집계로만 다룹니다. 최종 판단은 분석가가 합니다.",
    )


if __name__ == "__main__":
    main()
