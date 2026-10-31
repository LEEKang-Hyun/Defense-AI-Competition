"""
precursor.py — 전조 카드: 공식 신호(A) · 명분/동원 서사(B) · 은밀 증폭(C) · 물리 전조(D)의 정합성
(2026-10-17 추가 · 방산 AI 아이디어 경진대회 '전조카드' 확장. 기존 탐지 결과·숫자는 바꾸지 않는다)

입력 : data/official_statements.csv, data/narrative_items.csv   (gen_signals.py, 모두 가상)
       out/r_series.csv, out/bursts.csv, out/sources.json, out/policy.csv (기존 파이프라인 결과)
출력 : out/precursor.json          발언 구조화 결과·서사 분류·과거 사례 라이브러리·시간별 정합성
       out/precursor_series.csv    시각(1시간)별 축 수준·수렴 축 수·상태

설계 원칙
  1. 판정이 아니라 보조: 축별로 "어디까지 확인됐고 무엇은 모르는지"(증거 사다리 L1~L5)를 낸다. L5(국가 배후)는 공개 데이터로 판단 불가로 고정.
  2. 말의 양을 세지 않는다: 발언의 구조(발화자 격·조건부·수단·장소·시한·책임 전가·톤)를 뽑는다. 원문 구절 인용(span)이 없는 필드는 채우지 않는다.
  3. 기만을 기능으로: 공식 톤이 완화되는데 은밀 증폭이 오르면 '불일치', 공식 신호만 강하면 '수사 단독'.
  4. 시연에서는 규칙 기반 추출을 쓴다(오프라인·재현 가능). 운용 시 LLM 추출로 교체하되 스키마와 '원문 인용 필수' 규칙은 동일.
  5. 과거 사례 라이브러리는 공개 보도 기준의 실제 사건 7건(선행 사례 4·반례 2·오경보 1). 수치(선행 일수)는 보도 날짜 차이다.

실행 : python precursor.py
"""
import json, os, re
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA, OUT = os.path.join(HERE, "data"), os.path.join(HERE, "out")
C_LEVEL = {"NONE": 0, "REVIEW": 1, "WATCH": 2, "ALERT": 3, "CRITICAL": 4}
STATE_LABEL = {"none": "신호 없음", "watch": "관찰", "rhetoric_only": "수사 단독", "partial": "부분 수렴",
               "converged": "수렴", "mismatch": "불일치"}

# ---------------------------------------------------------------- 축 A: 발언 구조화 (규칙 기반 · 원문 인용 필수)
# v1 (2026-10-17): 합성 시나리오 문장만 보고 만든 규칙. 실제 공개 담화 10문장에 돌리자 7건 중 L3는 1건뿐이었다(과적합).
# v2 (2026-10-18): 실제 담화 문장(data/cases_real.json의 한국어 인용 10문장)을 모두 본 뒤 고쳤다 → 그 문장들에 대한 결과는
#     '규칙이 실제 표현을 다룰 수 있는가'의 작동 확인이지 예측력 평가가 아니다(in-sample). 두 판본을 모두 남겨 비교한다.
RULES_V1 = {
    "conditional": r"(?:[가-힣\s·]{2,40}?(?:한다면|않는다면|할 경우|경우에는|보인다면))",
    "deadline": r"(수일 내|며칠 내|수 일 내|즉시|곧|[0-9]+시간 내|[0-9]+일 내|주 내)",
    "place": r"(국경 ?일대|국경 ?지역|접경 ?지역|서해|동해|해상|상공|수역|연결 ?도로)",
    "means": r"(살포|발사|사격|폭파|차단|요새화|집결|풍선|기구|드론|무인기|배치|대기 ?태세)",
    "blame": r"(남측 민간단체|남측 당국|남측|동맹국|상대측)",
    "threat": r"(상응한? 조치|조치|집행|감당|책임|경고)",
    "soft": r"(대화의 문|긴장 완화|재검토|성의|협상)",
}
RULES_V2 = {
    # 조건절: '…면/…경우/…때에는/…시' 앞 구절 전체를 인용
    "conditional": r"(?:[가-힣A-Za-z0-9\s·,]{2,50}?(?:한다면|않는다면|할 경우|강행할 경우|하는 경우|경우에는|보인다면|할 때에는|때에는|하면|되면|확인시|발생하면))",
    # 시한: 상대 표현 + 절대 날짜·시각 + '…부터/…까지/…이후'
    "deadline": r"(수일 내|며칠 내|수 일 내|즉시적으로|즉시|곧|[0-9]+시간 내|[0-9]+일 내|주 내|[0-9]{1,2}월 [0-9]{1,2}일(?: 이후| 이전|까지|부터)?|[0-9]{1,2}일 (?:[0-9]{1,2}시까지|이후|이전|까지|부터))",
    "place": r"(국경 ?일대|국경 ?지역|종심 ?지역|접경 ?지역|국경|서해|동해|해상|상공|령공|영공|영해|수역|연결 ?도로|도로와 철길|철길|연평도|평양시|수도)",
    "means": r"(살포|발사|사격|포사격|타격|폭파|차단|요새화|끊어버리|집결|풍선|기구|휴지장|오물짝|드론|무인기|배치|대기 ?태세|사격준비태세|사격대기태세|포병)",
    "blame": r"(남측 민간단체|남측 당국|남측|한국 것들|한국|대한민국|괴뢰|남조선|동맹국|상대측|미국)",
    # 위협: 조치·보복·타격·대가·'좌시하지 않' 등 + 안전 보장 불가 통보
    "threat": r"(상응한? 조치|조치|집행|감당|책임|경고|타격|보복|박멸|대가|좌시하지 않|불장난|징벌|참변|끔찍한 사태|주적|보장하기 어렵|보장할 수 없|적대국)",
    # 예고형 서술어: 앞으로 할 행동을 단정하는 어미 (위협 어휘가 없어도 '예고'다)
    "announce": r"(살포될 것|가해질 것|취해질 것|진행되게 된다|전환시키|타격해야 하는|집중 살포|감행할 것|대답할 것|될 것이다|될 것|할 것이다|지시하였다)",
    "soft": r"(대화의 문|긴장 완화|재검토|성의|협상|대응할 일고의 가치|일고의 가치)",
}
RULES = RULES_V2
DEADLINE_HOURS = {"즉시": (0, 24), "즉시적으로": (0, 24), "곧": (24, 72), "수일 내": (48, 168), "수 일 내": (48, 168), "며칠 내": (48, 168)}


def extract(text, rules=None):
    """원문에서 구조 필드를 뽑는다. 각 필드에 원문 구절(span)을 함께 돌려준다 — 인용 없는 필드는 없다.
    수준: L3 예고형 = 조건부+(시한|장소) / 시한+장소 / 예고 서술어+수단+(시한|장소) · L2 = 위협 또는 예고 서술어만 · L1 = 발언 존재"""
    rules = rules or RULES
    f, spans = {}, []
    for key, pat in rules.items():
        hits = list(re.finditer(pat, text))
        if not hits:
            continue
        vals = []
        for m in hits:
            s, e = m.span()
            q = text[s:e].strip()
            if key == "conditional":   # 조건절은 '…면' 앞 구절 전체
                q = q.strip(" ,.")
            vals.append(q)
            spans.append([s, e, key])
        f[key] = vals
    level, why = 0, []
    strong = bool(f.get("threat") or f.get("announce"))
    if strong and not f.get("soft"):
        level, why = 2, ["위협 표현" if f.get("threat") else "예고 서술어"]
        if f.get("conditional") and (f.get("deadline") or f.get("place")):
            level = 3
            why.append("조건부 위협 + " + " · ".join(k for k in ["시한", "장소"] if f.get({"시한": "deadline", "장소": "place"}[k])))
        elif f.get("deadline") and f.get("place"):
            level = 3
            why.append("시한·장소가 명시된 예고")
        elif f.get("announce") and f.get("means") and (f.get("deadline") or f.get("place")):
            level = 3
            why.append("예고 서술어 + 수단 + " + ("시한" if f.get("deadline") else "장소"))
    elif strong and f.get("soft"):
        level, why = 2, ["위협 표현(완화 톤과 혼재)"]
    elif text.strip():
        level, why = 1, ["발언 존재(위협·조건 없음)"]
    tone = "soft" if f.get("soft") else ("threat" if f.get("threat") else ("announce" if f.get("announce") else "neutral"))
    dl = None
    for d in f.get("deadline", []):
        if d in DEADLINE_HOURS:
            dl = DEADLINE_HOURS[d]
    # 겹치는 구간은 긴 것 우선으로 정리 (화면 밑줄용)
    spans.sort(key=lambda x: (x[0], -(x[1] - x[0])))
    return dict(fields=f, spans=spans, level=level, level_why=" · ".join(why), tone=tone,
                means_explicit=bool(f.get("means")), deadline_hours=dl)


# ---------------------------------------------------------------- 축 B: 명분·동원 서사 분류 (규칙 기반 · 다국어 키워드)
B_RULES = {
    "pretext": r"(挑衅|责任在|провокац|оправд|provocation|no choice|failure to|도발|책임은|정당화|먼저)",
    "victim": r"(恐慌|受害|пострада|panic|victim|피해|공포)",
    "mobilization": r"(入伍|志愿|动员|мобилиз|enlist|volunteer|입대|탄원|궐기|복대)",
}
B_LABEL = {"pretext": "명분(상대가 먼저)", "victim": "피해 서사", "mobilization": "동원 서사", "other": "분류 안 됨"}


def classify_item(text, text_ko=""):
    for k, pat in B_RULES.items():
        if re.search(pat, text) or (text_ko and re.search(pat, text_ko)):
            return k
    return "other"


# ---------------------------------------------------------------- 과거 사례 라이브러리 (실제 공개 보도, 2026-10-16 확인)
# lead_days = 공식 신호(또는 서사 시작) 보도일 → 행동일. kind: precedent(선행 사례) / counter(반례) / false_alarm(오경보)
CASES = [
    dict(id="C1", kind="precedent", name="2024.5 오물풍선 (한반도)",
         signal_date="2024-05-26", signal="국방성 부상 담화: \"휴지와 오물짝이 곧 국경지역에 뿌려질 것\" — 남측 전단에 대한 '맞대응' 예고",
         action_date="2024-05-28", action="5/28 밤~29 새벽 오물 풍선 살포 시작", lead_days=2.5,
         features=dict(conditional=1, deadline=1, place=1, means=1, rank=2), axes=["A", "B"],
         sources=["globalsecurity.org/wmd/library/news/dprk/2024/dprk-240528-voa01.htm", "aljazeera.com (2024-06-02)"]),
    dict(id="C2", kind="precedent", name="2024.10 남북 연결도로 폭파 (한반도)",
         signal_date="2024-10-09", signal="총참모부 발표: 도로·철길 차단 및 요새화 예고 → 10/11 외무성 '남측 무인기' 주장(명분) → 10/13 포병 사격대기",
         action_date="2024-10-15", action="경의선·동해선 연결도로 폭파, 이후 '청년 140만 입대 탄원' 선전(동원)", lead_days=6,
         features=dict(conditional=0, deadline=0, place=1, means=1, rank=3), axes=["A", "B"],
         sources=["newsis.com/view/NISX20241014_0002919198", "en.wikipedia.org (2024 drone intrusion / road bombing)"]),
    dict(id="C3", kind="precedent", name="2022.2 러시아의 우크라이나 침공",
         signal_date="2021-12-15", signal="침공 전 10주간 친크렘린 14개 매체에서 허위 서사 1만 건 이상(DFRLab) · 대피 발표 영상 사전 제작(메타데이터)",
         action_date="2022-02-24", action="전면 침공", lead_days=70,
         features=dict(conditional=0, deadline=0, place=1, means=0, rank=4), axes=["B"],
         sources=["dfrlab.org (2023-02-25) Narrative Warfare", "axios.com (2022-02-21)"]),
    dict(id="C4", kind="precedent", name="2026.8 대만 한광훈련 정보전",
         signal_date="2026-08-03", signal="관영 TV 특수부대 다큐 1주 전 방영 → 훈련 중 '총통 도주 리허설' 조작 서사가 관영매체→웨이보 블로거로 확산(전문가 보고)",
         action_date="2026-08-10", action="훈련 기간 중 조작 서사 집중 확산", lead_days=7,
         features=dict(conditional=0, deadline=0, place=0, means=0, rank=3), axes=["A", "B", "C"],
         sources=["taiwanplus.com (2026-08-17)"]),
    dict(id="X1", kind="counter", name="반례 · 2025.6 미국의 이란 타격 (기만)",
         signal_date="2025-06-19", signal="\"2주 안에 결정하겠다\" 공식 발언", action_date="2025-06-22", action="이틀 뒤 타격",
         lead_days=3, features=dict(conditional=0, deadline=1, place=0, means=0, rank=4), axes=["A"],
         note="공식 신호가 시간을 벌기 위한 기만으로 쓰임 — 공식 축 단독으로 판단하지 않는 이유",
         sources=["bostonglobe.com (2025-06-23)"]),
    dict(id="X2", kind="counter", name="반례 · 2024.5 Joint Sword-2024A (동시 선전)",
         signal_date="2024-05-23", signal="관영 선전이 훈련 개시와 동시에 시작(사전 신호 없음)", action_date="2024-05-23", action="대만 포위 훈련",
         lead_days=0, features=dict(conditional=0, deadline=0, place=1, means=1, rank=3), axes=["A"],
         note="공식 신호가 항상 선행하지는 않는다 — '신호 없음'도 정보로 표시하는 이유",
         sources=["koreatimes.co.kr (2024-05)"]),
    dict(id="F1", kind="false_alarm", name="오경보 · 2023.3 선전 지표 급등 (사건 없음)",
         signal_date="2023-03-01", signal="노동신문 1면 배치 이상 지표가 시계열 최고치로 급등(Mercatus 2024)", action_date=None, action="대응되는 사건 없음",
         lead_days=None, features=dict(conditional=0, deadline=0, place=0, means=0, rank=0), axes=["A"],
         note="공식 매체 신호만으로는 사건 없는 급등이 생긴다 — 다른 축과의 정합성이 필요한 이유",
         sources=["mercatus.org (2024-10) Predicting North Korea's Policy Changes Through Propaganda"]),
]
FEAT_KEYS = ["conditional", "deadline", "place", "means"]


def similar_cases(ex):
    """현재 발언 구조와 사례 특징의 일치 수(0~4) + 발화자 격 근접도로 유사도. 규칙 기반이며 해석은 분석관이 한다."""
    cur = dict(conditional=int(bool(ex["fields"].get("conditional"))), deadline=int(bool(ex["fields"].get("deadline"))),
               place=int(bool(ex["fields"].get("place"))), means=int(ex["means_explicit"]))
    out = []
    for c in CASES:
        match = sum(1 for k in FEAT_KEYS if c["features"][k] == cur[k])
        out.append(dict(id=c["id"], kind=c["kind"], name=c["name"], match=match, lead_days=c["lead_days"], axes=c["axes"],
                        matched=[k for k in FEAT_KEYS if c["features"][k] == cur[k] == 1]))
    return sorted(out, key=lambda x: (-x["match"], x["kind"] != "precedent"))


def main():
    A = pd.read_csv(os.path.join(DATA, "official_statements.csv"), parse_dates=["ts"])
    Bi = pd.read_csv(os.path.join(DATA, "narrative_items.csv"), parse_dates=["ts"], keep_default_na=False)
    R = pd.read_csv(os.path.join(OUT, "r_series.csv"), parse_dates=["ts"])
    Bu = pd.read_csv(os.path.join(OUT, "bursts.csv"), parse_dates=["start", "end"], keep_default_na=False)
    SRC = json.load(open(os.path.join(OUT, "sources.json"), encoding="utf-8"))
    pp = os.path.join(OUT, "policy.csv")
    POL = pd.read_csv(pp, keep_default_na=False) if os.path.exists(pp) else None
    t0 = R.ts.min().floor("D")
    hr = lambda ts: (pd.Timestamp(ts) - t0) / pd.Timedelta(hours=1)
    max_h = int(R.hour.max())
    # 축 C는 외국어 출처가 연결된 공작 서사(경보 단계가 가장 높은 서사)를 쓴다
    camp = R.groupby("narrative_id")["level"].apply(lambda s: max(C_LEVEL[x] for x in s)).idxmax()
    rc = R[R.narrative_id == camp].sort_values("hour")
    src = SRC.get(str(int(camp)), {})

    # ---- A
    stmts = []
    for r in A.itertuples():
        ex = extract(r.text)
        stmts.append(dict(stmt_id=r.stmt_id, h=round(hr(r.ts), 2), ts=f"{r.ts:%m-%d %H:%M}", channel=r.channel,
                          speaker=r.speaker, speaker_rank=int(r.speaker_rank), route=r.route, lang_src=r.lang_src,
                          text=r.text, **ex, similar=similar_cases(ex)[:4]))
    # ---- B
    items = []
    for r in Bi.itertuples():
        k = classify_item(r.text, r.text_ko)
        items.append(dict(item_id=r.item_id, h=round(hr(r.ts), 2), ts=f"{r.ts:%m-%d %H:%M}", lang=r.lang, outlet=r.outlet,
                          url=r.url, text=r.text, text_ko=r.text_ko, kind=k, kind_label=B_LABEL[k]))

    # ---- 시각별 정합성
    series, prev_state = [], None
    for h in range(1, max_h + 1):
        sa = [s for s in stmts if s["h"] <= h]
        a_level = max([s["level"] for s in sa], default=0)
        a_tone = sa[-1]["tone"] if sa else None
        a_last = sa[-1]["stmt_id"] if sa else None
        bi = [x for x in items if x["h"] <= h and x["kind"] != "other"]
        pre = [x for x in bi if x["kind"] in ("pretext", "victim")]
        b_level = 0 if not bi else (2 if len(pre) >= 2 and len({x["lang"] for x in pre}) >= 2 else 1)
        rr = rc[rc.hour == h]
        rr = rr.iloc[0] if len(rr) else None
        c_lv = rr.level if rr is not None else "NONE"
        c_level = C_LEVEL[c_lv]
        c_rising = False
        if rr is not None:
            w = rc[(rc.hour <= h) & (rc.hour > h - 6)]
            c_rising = len(w) >= 2 and C_LEVEL[w.level.iloc[-1]] > C_LEVEL[w.level.iloc[0]] or c_level >= 3
        conv = sum([a_level >= 2, b_level >= 2, c_level >= 2])
        if a_tone == "soft" and c_level >= 3 and c_rising:
            state = "mismatch"
        elif conv >= 2:
            state = "converged"
        elif a_level >= 2 and b_level < 2 and c_level < 2:
            state = "rhetoric_only"
        elif conv == 1:
            state = "partial"
        elif a_level >= 1 or b_level >= 1 or c_level >= 1:
            state = "watch"
        else:
            state = "none"
        # 증거 사다리 (공개 데이터로 할 수 있는 주장의 단계)
        n_posts = int(rr.n_posts_sofar) if rr is not None else 0
        bursts_done = int((Bu[(Bu.narrative_id == camp)].end < t0 + pd.Timedelta(hours=h)).sum())
        fo_seen = bool(rr.foreign_seen) if rr is not None else False
        ladder = [
            dict(level="L1", name="서사가 존재하고 커진다", status="확인" if n_posts >= 10 else ("부분" if n_posts > 0 else "미확인"),
                 note=f"한국어 게시물 {n_posts}건"),
            dict(level="L2", name="외국어 원문이 먼저 나왔다", status="확인" if fo_seen and src.get("lead_hours", 0) else "미확인",
                 note=(f"외국어 원문 {src.get('n_foreign', 0)}건, 한국어보다 {src.get('lead_hours')}시간 선행" if fo_seen else "아직 외국어 원문 연결 없음")),
            dict(level="L3", name="유포 인프라가 비정상이다", status="확인" if bursts_done >= 2 else ("부분" if bursts_done == 1 else "미확인"),
                 note=f"10분 동시 게시 burst {bursts_done}회"),
            dict(level="L4", name="조직된 계정이 증폭한다", status="확인" if c_level >= 2 else "미확인",
                 note=f"반복 조정 의심 계정 {int(rr.n_susp) if rr is not None else 0}개" + (" (5개 이상)" if c_level >= 2 else "")),
            dict(level="L5", name="특정 국가가 배후다", status="판단 불가", note="공개 데이터로는 입증 불가 — 카드에 쓰지 않음"),
        ]
        pol = None
        if POL is not None:
            q = POL[(POL.narrative_id == camp) & (POL.hour == h)]
            pol = q.iloc[0].action_label if len(q) else None
        series.append(dict(h=h, a_level=a_level, a_tone=a_tone, a_last=a_last, b_level=b_level, b_items=len(bi),
                           c_level=c_level, c_label=c_lv, d_level=None, conv=conv, state=state,
                           state_label=STATE_LABEL[state], ladder=ladder, policy=pol,
                           changed=(state != prev_state)))
        prev_state = state

    # ---- 시연용 요약 숫자 (모두 이 파일의 계산값)
    a_first3 = next((s for s in stmts if s["level"] >= 3), None)
    first_watch = next((x["h"] for x in series if x["c_level"] >= 2), None)
    first_alert = next((x["h"] for x in series if x["c_level"] >= 3), None)
    first_conv = next((x["h"] for x in series if x["state"] == "converged"), None)
    first_mis = next((x["h"] for x in series if x["state"] == "mismatch"), None)
    summary = dict(campaign_narrative=int(camp), a_first_level3_h=a_first3["h"] if a_first3 else None,
                   a_first_level3_id=a_first3["stmt_id"] if a_first3 else None,
                   c_first_watch_h=first_watch, c_first_alert_h=first_alert,
                   first_converged_h=first_conv, first_mismatch_h=first_mis,
                   a_to_watch_h=(first_watch - a_first3["h"]) if (a_first3 and first_watch) else None,
                   precedents=[dict(id=c["id"], name=c["name"], lead_days=c["lead_days"]) for c in CASES if c["kind"] == "precedent"],
                   lead_window_days=[min(c["lead_days"] for c in CASES if c["kind"] == "precedent" and "A" in c["axes"]),
                                     max(c["lead_days"] for c in CASES if c["kind"] == "precedent" and "A" in c["axes"])])
    out = dict(t0=str(t0), max_h=max_h, statements=stmts, items=items, series=series, cases=CASES, summary=summary,
               notes=["축 A·B 자료는 가상(합성)이며 실존 국가·기관·인물의 발언이 아니다.",
                      "추출·분류는 규칙 기반(시연용). 운용 시 LLM 추출로 교체하되 스키마와 '원문 인용 필수'는 동일.",
                      "과거 사례 라이브러리의 날짜·선행 일수는 공개 보도 기준이며 7건뿐이다 — 정확도 주장이 아니라 참고용.",
                      "L5(국가 배후)는 공개 데이터로 판단 불가로 고정한다."])
    json.dump(out, open(os.path.join(OUT, "precursor.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    pd.DataFrame([{k: v for k, v in s.items() if k != "ladder"} for s in series]).to_csv(
        os.path.join(OUT, "precursor_series.csv"), index=False)
    print(f"statements={len(stmts)} items={len(items)} campaign=N{camp}")
    for s in stmts:
        print(f"  {s['stmt_id']} {s['h']:>5}h L{s['level']} tone={s['tone']:7s} {s['level_why']} | means={s['means_explicit']} dl={s['deadline_hours']}")
    print("  B:", [(x["item_id"], x["kind"]) for x in items])
    print("  summary:", {k: v for k, v in summary.items() if k != "precedents"})
    ch = [(x["h"], x["state"]) for x in series if x["changed"]]
    print("  state changes:", ch)


if __name__ == "__main__":
    main()
