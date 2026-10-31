"""
policy_bridge.py — 탐지 결과(시각 t) → 대응 단계 권고 연결 (작업 세션 작성)

입력 : data/posts.csv (truth_* 읽지 않음), out/r_series.csv, out/accounts_score.csv,
       out/burst_members.csv, out/sources.json, sensitive_tags.json(분석관 수동 태그)
출력 : out/policy.csv  — 서사 × 시각별 권고 (대시보드·demo.html·evaluate가 읽음)

시각 t 기준 매핑 (미래 정보 사용 금지)
  coord            : 그 시각 의심 계정(burst 2회 종료로 편입) 5개 이상 → STRONG,
                     경보 단계가 REVIEW(1회성 대규모 동시 게시·국내 사안) → WEAK, 그 외 NONE
  organic_engaged  : t 이전 한국어 게시물 중, t까지 끝난 burst에 한 번도 참여하지 않은 계정의 글 수 (집계값)
                     ※ burst 참여자를 빼는 이유: 아직 의심으로 확정 안 된 공작 계정이 '일반 반응'으로 세어지는 순환 문제 차단
  p (확산 확률)    : r_series의 RP.SPREAD_KEY 열(p_gt1 또는 p_gt08, 최근 3시간 합산 Gamma(1,2) 사후분포, 표본 부족이면 None)
  foreign_origin   : t 이전에 나타난 외국어 원문 수 (domestic 열이 참이면 0)
  sensitive_topic  : sensitive_tags.json 수동 태그 (자동 판단 안 함)
  bridge_event     : None = 데이터 없음(팔로워·언론 인용 정보 없음) → 4단계로 올리지 않고 "판단 불가" 표시
                     (대체 기준 "일반 반응 200건"은 섞인 큰 서사에서 오작동해 18:50 합의로 폐기)
  confidence       : 대시보드와 같은 식 0.4×조정 점수 + 0.3×외국 출처 + 0.3×min(R̂,1)
권고 단계는 자동으로 내려가지 않는다 (경보 단계와 같은 원칙, 해제는 분석관).

실행 : python policy_bridge.py                       # out/policy.csv 생성
       python policy_bridge.py --show 0:14,0:26,2:50  # 서사:시각 카드 출력
"""
import argparse, json, os
import numpy as np
import pandas as pd
import alerts as AL
import response_policy as RP

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
TAGS = os.path.join(HERE, "sensitive_tags.json")


def load_tags():
    if not os.path.exists(TAGS):
        json.dump({"_설명": "분석관이 서사별로 붙이는 민감 주제 태그. 자동 판단 아님. 키 = 서사 번호",
                   "0": True}, open(TAGS, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    d = json.load(open(TAGS, encoding="utf-8"))
    return {int(k): bool(v) for k, v in d.items() if not k.startswith("_")}


def build():
    P, S, B, M, SRC = AL.load()
    R = pd.read_csv(os.path.join(OUT, "r_series.csv"), parse_dates=["ts"])
    tags = load_tags()
    t0 = P.ts.min().floor("D")
    rows = []
    for nid, rs in R.groupby("narrative_id"):
        g = P[(P.narrative_id == nid) & (P.lang == "ko")]
        fo = P[(P.narrative_id == nid) & (P.lang != "ko")].ts
        mm = M[M.narrative_id == nid]
        joined = AL.suspect_asof(S, M, nid)
        sc = S[S.narrative_id == nid].set_index("account_id").score
        best = None
        for r in rs.sort_values("hour").itertuples():
            t = r.ts
            gg = g[g.ts < t]
            bm = set(mm[mm.burst_end < t].account_id)
            organic = int((~gg.account_id.isin(bm)).sum())
            coord = RP.Coord.STRONG if r.n_susp >= AL.MIN_SUSPECTS else (
                RP.Coord.WEAK if r.level == "REVIEW" else RP.Coord.NONE)
            n_fo = int((fo < t).sum())
            sus_now = [a for a, j in joined.items() if j <= t]
            coord_score = float(sc.reindex(sus_now).mean()) if sus_now else 0.0
            rv = 0.0 if pd.isna(r.r_pool) else min(float(r.r_pool), 1.0)
            conf = 0.4 * coord_score + 0.3 * float(n_fo > 0) + 0.3 * rv
            nan2blank = lambda v: "" if pd.isna(v) else v          # NaN → 표본 부족(None)
            sig = RP.signals_from_r_row(
                f"N{nid}", {"p_gt1": nan2blank(r.p_gt1), "p_gt08": nan2blank(r.p_gt08),
                            "domestic": r.domestic}, coord, organic, n_fo,
                sensitive_topic=tags.get(int(nid), False), detection_confidence=conf, bridge_event=None)
            rec = RP.recommend(sig)
            if organic > 0:
                rec.notes.append("일반 반응 수에는 반박·비판 답글도 포함될 수 있음 (입장 구분 안 함)")
            if RP.SPREAD_KEY != "p_gt1" and pd.notna(r.p_gt1):
                rec.notes.append(f"P(R>1)={r.p_gt1:.2f}" + (" — 자생 확산 '진입' 확률도 50% 이상" if r.p_gt1 >= RP.P_SPREAD else ""))
            sticky = False
            if best is not None and rec.action < best.action:
                rec, sticky = best, True       # 권고 단계 유지 (해제는 분석관)
            else:
                best = rec
            rows.append(dict(narrative_id=int(nid), hour=int(r.hour), stage=int(rec.stage),
                             stage_label=rec.stage_text or RP.stage_label(rec.stage), action=int(rec.action),
                             action_label=rec.action_label, attribution=rec.attribution,
                             why_now=rec.why_now, why_level=rec.why_level, do_not=" | ".join(rec.do_not),
                             escalate_if=rec.escalate_if, notes=" | ".join(rec.notes),
                             confidence=rec.confidence, sticky=sticky, organic_now=organic,
                             coord=int(coord), foreign_now=n_fo))
    D = pd.DataFrame(rows)
    D.to_csv(os.path.join(OUT, "policy.csv"), index=False)
    return D


def show(D, spec):
    for item in spec.split(","):
        n, h = (int(x) for x in item.split(":"))
        r = D[(D.narrative_id == n) & (D.hour == h)]
        if r.empty:
            print(f"[N{n} {h}시] 데이터 없음\n"); continue
        r = r.iloc[0]
        print(f"[N{n} · {h}시] 권고: {r.action_label}" + ("  (이전 단계 유지)" if r.sticky else ""))
        print(f"  확산 단계 : {r.stage_label}   | 입력: 조정 {['NONE','WEAK','STRONG'][r.coord]}, 일반 반응 {r.organic_now}, 외국 원문 {r.foreign_now}")
        print(f"  출처 귀속 : {r.attribution}")
        print(f"  왜 지금   : {r.why_now}")
        print(f"  왜 이 수준: {r.why_level}")
        for d in str(r.do_not).split(" | "):
            if d and d != "nan": print(f"  하지 말 것: {d}")
        print(f"  다음 재평가: {r.escalate_if}")
        for x in str(r.notes).split(" | "):
            if x and x != "nan": print(f"  참고     : {x}")
        print(f"  신뢰도   : {r.confidence:.2f}  (판정이 아니라 분석관 보조)\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", default="")
    a = ap.parse_args()
    D = build()
    first = D[D.action > 0].groupby(["narrative_id", "action_label"]).hour.min().reset_index()
    print("서사별 권고가 처음 나온 시각:")
    for r in first.sort_values(["narrative_id", "hour"]).itertuples():
        print(f"  N{r.narrative_id}: {r.hour}시 {r.action_label}")
    if a.show:
        print(); show(D, a.show)
