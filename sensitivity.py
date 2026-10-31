"""
sensitivity.py — 민감도 분석 · 대조 실험
가정값(burst 기준, 점수 가중치, 의심 임계, 경보 확률 기준)을 바꿔도 결론이 유지되는지 확인한다.
원래 결과(out/)는 건드리지 않고 임시 폴더에서 M3→M4→M7을 다시 돌린다.

추가 실험
  - 시간 셔플 대조: 계정마다 게시 시각을 무작위로 ±24시간 밀었을 때 생기는 burst·의심 계정 수 (우연 발생률)
  - 관할 제한 확인: 외국어 출처를 지우면 같은 공작 서사가 '국내 사안(REVIEW)'으로만 남는지
출력 : out/sensitivity.csv, out/sensitivity_extra.json
실행 : python sensitivity.py   (약 1~3분)
"""
import contextlib, io, json, os, shutil, tempfile
import numpy as np
import pandas as pd
import coordination as CO
import alerts as AL
import evaluate as EV

HERE = os.path.dirname(os.path.abspath(__file__))
DATA, OUT = os.path.join(HERE, "data"), os.path.join(HERE, "out")


def run(tmp_out, data_dir=DATA, co=None, al=None):
    """임시 폴더에서 M3, M4, M7 실행 후 metrics 반환"""
    saved = {}
    for mod, kv in ((CO, co or {}), (AL, al or {})):
        for k, v in kv.items():
            saved[(mod, k)] = getattr(mod, k); setattr(mod, k, v)
    for mod in (CO, AL, EV):
        saved[(mod, "OUT")] = mod.OUT; mod.OUT = tmp_out
    for mod in (CO, AL, EV):
        saved[(mod, "DATA")] = mod.DATA; mod.DATA = data_dir
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            CO.main(); AL.main(); EV.main()
        return json.load(open(os.path.join(tmp_out, "metrics.json"), encoding="utf-8"))
    finally:
        for (mod, k), v in saved.items():
            setattr(mod, k, v)


def fresh_tmp():
    d = tempfile.mkdtemp(prefix="fimi_sens_")
    for f in ("posts_nar.csv", "sources.json"):
        shutil.copy(os.path.join(OUT, f), d)
    return d


def main():
    W0 = dict(CO.W)
    configs = [
        ("기준값", {}, {}),
        ("burst 최소 계정 6", dict(MIN_DISTINCT=6), {}),
        ("burst 최소 계정 10", dict(MIN_DISTINCT=10), {}),
        ("burst 배율 3배", dict(MIN_RATIO=3.0), {}),
        ("burst 배율 8배", dict(MIN_RATIO=8.0), {}),
        ("burst 창 5분", dict(WIN=pd.Timedelta(minutes=5)), {}),
        ("burst 창 20분", dict(WIN=pd.Timedelta(minutes=20)), {}),
        ("가중치 균등", dict(W=dict(young=.25, burst=.25, burst_sim=.25, url_share=.25)), {}),
        ("신생 계정 신호 제외", dict(W=dict(young=0, burst=.45, burst_sim=.35, url_share=.20)), {}),
        ("동일 URL 신호 제외", dict(W=dict(young=.35, burst=.35, burst_sim=.30, url_share=0)), {}),
        ("의심 임계 0.5", dict(SUSPECT=0.5), {}),
        ("의심 임계 0.7", dict(SUSPECT=0.7), {}),
        ("경보 확률 기준 0.3", {}, dict(P_LEVEL=0.3)),
        ("경보 확률 기준 0.7", {}, dict(P_LEVEL=0.7)),
        ("R 합산 1시간", {}, dict(POOL_H=1)),
        ("R 합산 6시간", {}, dict(POOL_H=6)),
    ]
    rows = []
    for name, co, al in configs:
        tmp = fresh_tmp()
        try:
            m = run(tmp, co=co, al=al)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        c, t, fa = m["cib"], m["timing"], m["false_alarms"]
        rows.append(dict(설정=name, 정밀도=c["precision"], 재현율=c["recall"],
                         일반사용자오탐=c["organic_flagged_suspected"],
                         관찰_시=t["first_watch_h"], 경보_시=t["first_alert_h"], 위험_시=t["first_critical_h"],
                         다른서사_오경보=fa["reached_watch_or_higher"]))
        print(f"{name:14s} 정밀도 {c['precision']} 재현율 {c['recall']} 오탐 {c['organic_flagged_suspected']} "
              f"| WATCH {t['first_watch_h']} ALERT {t['first_alert_h']} CRIT {t['first_critical_h']} | 오경보 {fa['reached_watch_or_higher']}")
    CO.W = W0
    pd.DataFrame(rows).to_csv(os.path.join(OUT, "sensitivity.csv"), index=False)

    extra = {}
    # 시간 셔플 대조: 계정마다 게시 시각을 ±24시간 무작위 이동 (서사 배정은 그대로)
    P = pd.read_csv(os.path.join(DATA, "posts.csv"), keep_default_na=False, parse_dates=["ts"])
    A = pd.read_csv(os.path.join(DATA, "accounts.csv"))
    res = []
    for seed in range(3):
        r = np.random.default_rng(seed)
        sh = {a: pd.Timedelta(minutes=int(r.integers(-24 * 60, 24 * 60))) for a in P.account_id.unique()}
        Q = P.copy(); Q["ts"] = Q.ts + Q.account_id.map(sh)
        dd = tempfile.mkdtemp(prefix="fimi_null_data_")
        Q.to_csv(os.path.join(dd, "posts.csv"), index=False); A.to_csv(os.path.join(dd, "accounts.csv"), index=False)
        tmp = fresh_tmp()
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                saved = (CO.DATA, CO.OUT); CO.DATA, CO.OUT = dd, tmp
                CO.main(); CO.DATA, CO.OUT = saved
            b = pd.read_csv(os.path.join(tmp, "bursts.csv")) if os.path.getsize(os.path.join(tmp, "bursts.csv")) > 5 else pd.DataFrame()
            s = pd.read_csv(os.path.join(tmp, "accounts_score.csv"))
            res.append(dict(bursts=int(len(b)), suspected=int((s.tier == "suspected").sum())))
        finally:
            shutil.rmtree(tmp, ignore_errors=True); shutil.rmtree(dd, ignore_errors=True)
    base_b = len(pd.read_csv(os.path.join(OUT, "bursts.csv")))
    base_s = int((pd.read_csv(os.path.join(OUT, "accounts_score.csv")).tier == "suspected").sum())
    extra["time_shuffle"] = dict(observed_bursts=base_b, observed_suspected=base_s, shuffled=res)
    print(f"[시간 셔플] 실제 burst {base_b}, 의심 {base_s} → 셔플 {res}")

    # 관할 제한 확인: 외국어 출처 게시물을 지우고 M2 결과를 유지한 채 M3~M4 재실행
    dd = tempfile.mkdtemp(prefix="fimi_dom_data_")
    P[P.lang == "ko"].to_csv(os.path.join(dd, "posts.csv"), index=False)
    A.to_csv(os.path.join(dd, "accounts.csv"), index=False)
    tmp = fresh_tmp()
    try:
        src = json.load(open(os.path.join(tmp, "sources.json"), encoding="utf-8"))
        for v in src.values():
            v.update(n_foreign=0, foreign=[], lead_hours=None, first_foreign_ts=None)
        json.dump(src, open(os.path.join(tmp, "sources.json"), "w", encoding="utf-8"), ensure_ascii=False)
        saved = (CO.DATA, CO.OUT, AL.DATA, AL.OUT)
        CO.DATA, CO.OUT, AL.DATA, AL.OUT = dd, tmp, dd, tmp
        with contextlib.redirect_stdout(io.StringIO()):
            CO.main(); AL.main()
        CO.DATA, CO.OUT, AL.DATA, AL.OUT = saved
        cards = json.load(open(os.path.join(tmp, "alerts.json"), encoding="utf-8"))
        extra["no_foreign_source"] = [dict(narrative_id=c["narrative_id"], max_level=c["max_level"],
                                           jurisdiction=c["jurisdiction"]) for c in cards]
        print("[관할 제한] 외국어 출처 제거 시:", extra["no_foreign_source"])
    finally:
        shutil.rmtree(tmp, ignore_errors=True); shutil.rmtree(dd, ignore_errors=True)
    json.dump(extra, open(os.path.join(OUT, "sensitivity_extra.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    policy_grid()


def policy_grid():
    """대응 단계 권고 가정값 격자: ORGANIC_MIN × P_SPREAD (원래 out/policy.csv는 마지막에 기본값으로 다시 만든다)"""
    import response_policy as RP, policy_bridge as PB
    A = pd.read_csv(os.path.join(DATA, "posts.csv"), keep_default_na=False, usecols=["post_id", "truth_narrative"])
    N = pd.read_csv(os.path.join(OUT, "posts_nar.csv"))
    camp = int(A.merge(N, on="post_id").query("truth_narrative == 'N1'").narrative_id.value_counts().idxmax())
    base = (RP.ORGANIC_MIN, RP.P_SPREAD)
    rows = []
    try:
        for om in (3, 5, 8):
            for ps in (0.4, 0.5, 0.6):
                RP.ORGANIC_MIN, RP.P_SPREAD = om, ps
                with contextlib.redirect_stdout(io.StringIO()):
                    D = PB.build()
                c = D[D.narrative_id == camp]
                fh = lambda a: (int(c[c.action >= a].hour.min()) if (c.action >= a).any() else None)
                nm = D[D.narrative_id != camp].groupby("narrative_id").action.max()
                rows.append({"ORGANIC_MIN": om, "P_SPREAD": ps, "공작_준비_시": fh(2), "공작_실행검토_시": fh(3),
                             "공작_공식대응_시": fh(4), "정상서사_준비이상": int((nm >= 2).sum())})
    finally:
        RP.ORGANIC_MIN, RP.P_SPREAD = base
        with contextlib.redirect_stdout(io.StringIO()):
            PB.build()
    G = pd.DataFrame(rows)
    G.to_csv(os.path.join(OUT, "sensitivity_policy.csv"), index=False)
    print("[권고 민감도]"); print(G.to_string(index=False))


if __name__ == "__main__":
    main()
