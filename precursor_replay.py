"""
precursor_replay.py — 전조 카드 '역사 재생': 실제 공개 담화에 규칙 추출기를 돌려 당시 날짜에 어떤 수준이 나왔을지 재생 (2026-10-18 추가)

무엇을 하나
  data/cases_real.json (공개 보도에서 확인한 실제 사례 10건·발언 17건, 발화자는 기관·직책만, 인용문은 보도된 한국어 그대로)의
  한국어 인용문에 precursor.extract 를 v1·v2 규칙으로 각각 돌린다. 행동이 있었던 사례는 '첫 L3 → 행동'까지 며칠이 걸렸는지,
  행동이 없었던 사례(오경보)는 '공식 축만 봤다면 L3를 냈을지'를 센다.

정직하게 적어 둘 것 (화면에도 그대로 나간다)
  · v2 규칙은 이 10문장을 모두 본 뒤 고쳤다(in-sample). 결과는 "규칙이 실제 표현을 다룰 수 있는가"의 작동 확인이지 예측력이 아니다.
  · v1(합성 문장만 보고 만든 규칙)의 결과를 나란히 둔다 — 합성 데이터만으로 만든 규칙이 실제 담화에서 어떻게 무너지는지 보여준다.
  · 영어 원문 사례(A4 펠로시, C6 '2주', C7 Joint Sword)는 한국어 요약문뿐이라 추출기를 돌리지 않는다(요약은 인용이 아니다).
  · 날짜는 보도 날짜이고 송고 시각은 대부분 [확인 필요]. 선행은 '일' 단위로만 말한다.
  · 사례 수가 적다(추출 가능 7건). 정확도를 주장하지 않는다.

실행: python precursor_replay.py  →  out/precursor_replay.json
"""
import json, os
from datetime import date

import precursor as PC

HERE = os.path.dirname(os.path.abspath(__file__))
DATA, OUT = os.path.join(HERE, "data"), os.path.join(HERE, "out")
WINDOW_DAYS = 14          # 오경보 판정 창: 발언 뒤 14일 안에 행동이 없으면 '행동 없음'
IN_SAMPLE_V2 = ["A1_2024-05_balloon_notice", "A2_2024-06_balloon_conditional", "A3_2024-10_road_demolition", "A5_2010-11_yeonpyeong_sameday",
                "B1_2010-12_yeonpyeong_drill_no_response", "B2_2013-04_embassy_deadline", "B3_2022-08_covid_retaliation_speech"]
KIND_KO = {"precedent": "선행 사례", "false_alarm": "오경보 사례", "counter": "반례"}


def _d(s):
    return date.fromisoformat(s[:10])


def run(cases):
    out_cases = []
    for c in cases:
        stmts = []
        for s in c["statements"]:
            t = s["text_ko"]
            excluded = t.startswith("[한국어 요약]")
            row = dict(date=s["date"], time_kst=s.get("time_kst"), speaker_role=s["speaker_role"], text_ko=t,
                       source_url=s.get("source_url"), excluded=excluded)
            if not excluded:
                for tag, rules in (("v1", PC.RULES_V1), ("v2", PC.RULES_V2)):
                    ex = PC.extract(t, rules)
                    row[tag] = dict(level=ex["level"], level_why=ex["level_why"], tone=ex["tone"],
                                    fields={k: list(dict.fromkeys(v)) for k, v in ex["fields"].items()}, spans=ex["spans"])
            stmts.append(row)
        act = c.get("action")
        act_date = _d(act["date"]) if act and act.get("date") else None
        verdict = {}
        for tag in ("v1", "v2"):
            usable = [s for s in stmts if not s["excluded"]]
            lv = [(s["date"], s[tag]["level"]) for s in usable]
            max_lv = max([l for _, l in lv], default=None)
            first_l3 = next((d for d, l in lv if l >= 3), None)
            if not usable:
                verdict[tag] = dict(result="n/a", label="영어 원문·요약문 → 추출 제외, 사례 메모만", lead_days=None, max_level=None)
            elif c["kind"] == "precedent":
                if first_l3 and act_date:
                    lead = (act_date - _d(first_l3)).days
                    verdict[tag] = dict(result="hit", label=f"L3 선행 {lead}일", lead_days=lead, max_level=max_lv)
                else:
                    verdict[tag] = dict(result="miss", label=f"L3 없음 (최고 L{max_lv})" if max_lv is not None else "추출 제외", lead_days=None, max_level=max_lv)
            elif c["kind"] == "false_alarm":
                if max_lv is None:
                    verdict[tag] = dict(result="n/a", label="추출 제외", lead_days=None, max_level=None)
                elif max_lv >= 3:
                    verdict[tag] = dict(result="false_alarm", label="L3인데 14일 내 행동 없음 → 공식 축 단독이면 오경보", lead_days=None, max_level=max_lv)
                else:
                    verdict[tag] = dict(result="ok", label=f"최고 L{max_lv} → 수사 단독, 경보 아님", lead_days=None, max_level=max_lv)
            else:
                verdict[tag] = dict(result="n/a", label="영어 원문·요약문 → 추출 제외, 사례 메모만", lead_days=None, max_level=max_lv)
        # 타임라인용: 행동일 기준 상대 일수 (행동 없으면 첫 발언 기준)
        # 선행 사례는 행동일, 오경보·반례는 첫 발언일을 0으로 둔다 (오경보 사례의 '행동'은 연결되지 않은 통상 활동일 수 있다)
        ref = act_date if (act_date and c["kind"] == "precedent") else _d(stmts[0]["date"])
        for s in stmts:
            s["rel_days"] = (_d(s["date"]) - ref).days
        action_rel = (act_date - ref).days if act_date else None
        out_cases.append(dict(case_id=c["case_id"], kind=c["kind"], kind_ko=KIND_KO.get(c["kind"], c["kind"]), name=c["name"],
                              statements=stmts, action=act, action_date=act["date"] if act else None,
                              lead_days_reported=c.get("lead_days"), verified=c.get("verified"), notes=c.get("notes", ""),
                              in_sample_v2=c["case_id"] in IN_SAMPLE_V2, verdict=verdict, ref_date=ref.isoformat(), action_rel_days=action_rel,
                              window_days=WINDOW_DAYS))
    summ = {}
    for tag in ("v1", "v2"):
        pre = [c for c in out_cases if c["kind"] == "precedent" and c["verdict"][tag]["result"] in ("hit", "miss")]
        fa = [c for c in out_cases if c["kind"] == "false_alarm" and c["verdict"][tag]["result"] in ("false_alarm", "ok")]
        hits = [c for c in pre if c["verdict"][tag]["result"] == "hit"]
        summ[tag] = dict(n_precedent=len(pre), n_hit=len(hits),
                         leads=[c["verdict"][tag]["lead_days"] for c in hits],
                         n_false_alarm_cases=len(fa), n_false_alarm_l3=sum(1 for c in fa if c["verdict"][tag]["result"] == "false_alarm"),
                         n_excluded=sum(1 for c in out_cases if c["verdict"][tag]["result"] == "n/a"))
    return dict(cases=out_cases, summary=summ, window_days=WINDOW_DAYS,
                notes=["v2 규칙은 이 사례의 한국어 인용 10문장을 모두 본 뒤 고쳤다(in-sample) — 작동 확인이지 예측력 평가가 아니다",
                       "v1은 합성 시나리오 문장만 보고 만든 규칙 — 실제 담화에서 무너지는 모습을 그대로 둔다",
                       "영어 원문 사례(A4·C6·C7)는 한국어 요약문뿐이라 추출하지 않는다(요약은 인용이 아니다)",
                       "날짜는 보도 날짜, 송고 시각은 대부분 [확인 필요] → 선행은 일 단위로만",
                       f"오경보 판정 창 {WINDOW_DAYS}일은 가정값", "사례 7건(추출 가능)으로 정확도를 주장하지 않는다"],
                source_file="data/cases_real.json (공개 보도 확인 2026-10-18 · 발화자는 기관·직책만 · 인용문은 보도된 그대로)")


if __name__ == "__main__":
    cases = json.load(open(os.path.join(DATA, "cases_real.json"), encoding="utf-8"))
    res = run(cases)
    os.makedirs(OUT, exist_ok=True)
    json.dump(res, open(os.path.join(OUT, "precursor_replay.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for c in res["cases"]:
        v1, v2 = c["verdict"]["v1"], c["verdict"]["v2"]
        print(f"{c['case_id'][:2]} {c['kind_ko']:6s} {c['name'][:34]:36s} v1: {v1['label']:28s} v2: {v2['label']}")
    print("summary:", json.dumps(res["summary"], ensure_ascii=False))
