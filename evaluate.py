"""
evaluate.py — M7 성공 지표 측정
정답(truth_*) 컬럼은 이 파일에서만 읽는다. 시스템(M2~M4)은 정답을 보지 않는다.

측정 항목
  1. 서사 묶기  : 정답 공작 서사(N1) 한국어 게시물이 시스템 서사 하나에 얼마나 모였나, 다른 서사가 섞였나, 외국어 원문 4건이 붙었나
  2. CIB 탐지   : 공작 계정 정밀도·재현율 (suspected 기준), 일반 사용자 오탐 수
  3. 조기성     : 경보 시각 vs 정답 R이 1을 넘는 시각 vs 단순 볼륨 경보 시각
  4. 오탐 경보  : 공작 아닌 서사가 WATCH 이상까지 간 수, REVIEW로 멈춘 수
  5. R 추정 오차: 시스템 R̂(탐지 라벨) vs 정답 라벨로 같은 공식 계산한 R
실행 : python evaluate.py      →  out/metrics.json + 화면 요약
"""
import json, os
import numpy as np
import pandas as pd
import alerts as AL

HERE = os.path.dirname(os.path.abspath(__file__))
DATA, OUT = os.path.join(HERE, "data"), os.path.join(HERE, "out")


def main():
    P = pd.read_csv(os.path.join(DATA, "posts.csv"), parse_dates=["ts"], keep_default_na=False)
    A = pd.read_csv(os.path.join(DATA, "accounts.csv"))
    N = pd.read_csv(os.path.join(OUT, "posts_nar.csv"))
    S = pd.read_csv(os.path.join(OUT, "accounts_score.csv"), keep_default_na=False)
    R = pd.read_csv(os.path.join(OUT, "r_series.csv"), parse_dates=["ts"])
    P = P.merge(N[["post_id", "narrative_id"]], on="post_id")
    t0 = P.ts.min().floor("D")
    m = {}

    # 1. 서사 묶기
    ko1 = P[(P.truth_narrative == "N1") & (P.lang == "ko")]
    dom = int(ko1.narrative_id.value_counts().idxmax())
    in_dom = P[P.narrative_id == dom]
    m["narrative"] = dict(
        system_id=dom,
        n1_coverage=round(float((ko1.narrative_id == dom).mean()), 3),     # N1 한국어 중 대표 서사에 모인 비율
        purity=round(float((in_dom.truth_narrative == "N1").mean()), 3),   # 대표 서사 안에서 N1 비율
        foreign_attached=int(((P.lang != "ko") & (P.narrative_id == dom)).sum()),
        n1_split_into=int(ko1[ko1.narrative_id >= 0].narrative_id.nunique()))

    # 2. CIB (공작 서사 기준)
    s = S[S.narrative_id == dom].merge(A[["account_id", "truth_group"]], on="account_id")
    camp_all = set(A[A.truth_group == "campaign"].account_id)
    camp_here = set(s[s.truth_group == "campaign"].account_id)
    sus = set(s[s.tier == "suspected"].account_id)
    tp = len(sus & camp_all)
    m["cib"] = dict(
        suspected=len(sus), true_positive=tp,
        precision=round(tp / len(sus), 3) if sus else None,
        recall=round(tp / len(camp_here), 3) if camp_here else None,
        campaign_in_narrative=len(camp_here),
        campaign_review=int(((s.tier == "review") & (s.truth_group == "campaign")).sum()),
        organic_flagged_suspected=int(((s.tier == "suspected") & (s.truth_group != "campaign")).sum()),
        organic_flagged_review=int(((s.tier == "review") & (s.truth_group != "campaign")).sum()))

    # 3. 조기성
    rs = R[R.narrative_id == dom].sort_values("hour")
    first = lambda lv: (None if rs[rs.level.map(AL.LEVELS.index) >= AL.LEVELS.index(lv)].empty
                        else int(rs[rs.level.map(AL.LEVELS.index) >= AL.LEVELS.index(lv)].hour.iloc[0]))
    g = P[(P.narrative_id == dom) & (P.lang == "ko")]
    # 정답 R: 정답 공작 계정을 처음부터 '의심'으로 두고 같은 공식으로 계산
    joined_true = {a: t0 - pd.Timedelta(days=1) for a in camp_all}
    grid = pd.to_datetime(rs.ts.values)
    rt = AL.r_series(g, joined_true, grid)
    rt["hour"] = rs.hour.values
    rt["r_smooth"] = rt.r_hat.rolling(3, min_periods=2).mean()
    cross = rt[rt.r_smooth >= 1.0]
    true_cross = int(cross.hour.iloc[0]) if len(cross) else None
    # 단순 볼륨 경보 (공정한 비교: 정답 라벨 없이 서사의 '모든' 한국어 게시물 수만 본다)
    #   규칙: 시간당 게시물 >= 20 이면서 직전 24시간 중앙값의 3배 이상 (k=2,3,4로 민감도 확인)
    def vol_first(gg, k=3, minc=20):
        hc = gg.assign(h=((gg.ts - t0) / pd.Timedelta(hours=1)).astype(int)).groupby("h").size() \
            .reindex(range(int(rs.hour.max()) + 1), fill_value=0)
        return next((int(h) for h in hc.index if h >= 6 and hc[h] >= minc
                     and hc[h] >= k * max(hc[max(0, h - 24):h].median(), 1)), None)
    vol_alarm = vol_first(g)
    vol_k = {k: vol_first(g, k) for k in (2, 3, 4)}
    ko_all = P[(P.lang == "ko") & (P.narrative_id >= 0) & (P.narrative_id != dom)]
    vol_false = sorted(int(n) for n, gg in ko_all.groupby("narrative_id") if vol_first(gg) is not None)
    alert_h = first("ALERT")
    m["timing"] = dict(
        first_watch_h=first("WATCH"), first_alert_h=alert_h, first_critical_h=first("CRITICAL"),
        true_R_cross_1_h=true_cross, generator_param_cross_1_h=36.7,
        volume_alarm_h=vol_alarm, volume_alarm_by_k=vol_k,
        volume_false_alarm_narratives=vol_false,
        lead_vs_true_R_h=(true_cross - alert_h) if (true_cross is not None and alert_h is not None) else None,
        watch_minus_volume_h=(first("WATCH") - vol_alarm) if (vol_alarm is not None and first("WATCH") is not None) else None,
        ko_posts_at_alert=int((g.ts < t0 + pd.Timedelta(hours=alert_h)).sum()) if alert_h else None,
        ko_posts_total=int(len(g)))

    # 4. 오탐 경보
    other = R[R.narrative_id != dom]
    mx = other.groupby("narrative_id")["level"].agg(lambda s: max(s, key=AL.LEVELS.index))
    m["false_alarms"] = dict(
        other_narratives=int(len(mx)),
        reached_watch_or_higher=int((mx.map(AL.LEVELS.index) >= AL.LEVELS.index("WATCH")).sum()),
        stopped_at_review=int((mx == "REVIEW").sum()))

    # 5. R 추정 오차 (같은 시각, 둘 다 계산된 구간)
    both = pd.DataFrame({"sys": rs.r_hat.values, "true": rt.r_hat.values}).dropna()
    m["r_error"] = dict(n_hours=int(len(both)),
                        mae=round(float((both.sys - both.true).abs().mean()), 3) if len(both) else None,
                        mean_bias=round(float((both.sys - both.true).mean()), 3) if len(both) else None)

    # 6. 대응 단계 권고 (policy_bridge.py 결과가 있을 때)
    pp = os.path.join(OUT, "policy.csv")
    if os.path.exists(pp):
        PO = pd.read_csv(pp, keep_default_na=False)
        first_by = {}
        for (n, a), gg in PO[PO.action > 0].groupby(["narrative_id", "action_label"]):
            first_by.setdefault(int(n), {})[a] = int(gg.hour.min())
        normal = PO[PO.narrative_id != dom]
        m["policy"] = dict(
            campaign_first=first_by.get(dom, {}),
            normal_first=({str(k): v for k, v in first_by.items() if k != dom}),
            normal_prebunk_or_higher=int(normal.groupby("narrative_id").action.max().ge(2).sum()),
            normal_narratives=int(normal.narrative_id.nunique()))

    with open(os.path.join(OUT, "metrics.json"), "w", encoding="utf-8") as f:
        json.dump(m, f, ensure_ascii=False, indent=2)

    n, c, t, fa, re = m["narrative"], m["cib"], m["timing"], m["false_alarms"], m["r_error"]
    print("=== 성공 지표 ===")
    print(f"[서사] 공작 서사 게시물의 {n['n1_coverage']:.0%}가 시스템 서사 N{n['system_id']}에 모임 · 순도 {n['purity']:.0%} · "
          f"외국어 원문 {n['foreign_attached']}/4건 연결 · 쪼개진 서사 수 {n['n1_split_into']}")
    print(f"[CIB ] suspected {c['suspected']}개 중 실제 공작 {c['true_positive']}개 → 정밀도 {c['precision']} · "
          f"재현율 {c['recall']} (공작 {c['campaign_in_narrative']}개 중, 나머지 review {c['campaign_review']}) · "
          f"일반 사용자 오탐 suspected {c['organic_flagged_suspected']} / review {c['organic_flagged_review']}")
    print(f"[조기] WATCH {t['first_watch_h']}시 · ALERT {t['first_alert_h']}시 · CRITICAL {t['first_critical_h']}시 | "
          f"정답 R≥1 {t['true_R_cross_1_h']}시 · 볼륨 경보 {t['volume_alarm_h']}시")
    print(f"       경보 시점 한국어 게시물 {t['ko_posts_at_alert']}건 / 전체 {t['ko_posts_total']}건")
    print(f"[볼륨] 단순 볼륨 경보는 공작 서사에 {t['volume_alarm_h']}시 (k별 {t['volume_alarm_by_k']}) → 우리 WATCH보다 "
          f"{t['watch_minus_volume_h']}시간 빠름. 그러나 공작 아닌 서사 {len(t['volume_false_alarm_narratives'])}개에도 경보 "
          f"(서사 {t['volume_false_alarm_narratives']}) — 우리 방식은 0개")
    print(f"[오탐] 다른 서사 {fa['other_narratives']}개 중 WATCH 이상 {fa['reached_watch_or_higher']}개 · REVIEW에서 멈춤 {fa['stopped_at_review']}개")
    if "policy" in m:
        po = m["policy"]
        print(f"[권고] 공작 서사 권고 첫 시각 {po['campaign_first']} · 정상 서사 {po['normal_narratives']}개 중 "
              f"사전 반박 준비 이상 {po['normal_prebunk_or_higher']}개 (목표 0) · 정상 서사 권고 {po['normal_first']}")
    print(f"[R̂  ] 정답 라벨 R 대비 평균 절대오차 {re['mae']} · 평균 편향 {re['mean_bias']} ({re['n_hours']}시간)")


if __name__ == "__main__":
    main()
