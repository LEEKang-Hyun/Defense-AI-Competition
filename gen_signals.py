"""
gen_signals.py — 전조 축 A·B 합성 데이터 생성기 (2026-10-17 추가 · 방산 AI 아이디어 경진대회 '전조카드' 확장)

72시간 가상 시나리오(gen_data.py와 같은 세계, T0 = 2026-10-01 00:00)에 두 축의 자료를 더한다.
posts.csv는 건드리지 않는다 → 기존 탐지 결과(관찰 13시·경보 41시·위험 56시)는 그대로다.

  축 A 공식 신호  data/official_statements.csv
      가상 적성국('북방국', 가상) 공식 채널의 담화·보도. 번역문(ko)과 원문 언어 표기.
      실존 국가·기관·인물의 발언이 아니다. 구조는 공개 보도된 실제 사례(예고형 담화 → 수일 뒤 행동)를 본떴다.
  축 B 명분·동원 서사  data/narrative_items.csv
      외국어 가상 매체·채널의 기사/게시물. '상대가 먼저'(명분) · '우리가 피해'(피해) · 입대·궐기(동원) 서사.

시나리오 흐름 (설계 의도)
   3시  외무성 대변인: 관찰·비난 (위협 없음)                    → A 수준 1
  11시  국방성 부상: 조건부 위협 + 시한 '수일 내' + 장소 '국경 일대'  → A 수준 3 (예고형)
  29시  총참모부: 대기태세 지시, '즉시 집행' (수단은 여전히 모호)    → A 수준 3 유지, 긴급도 ↑
  47시  외무성 대변인: '대화의 문은 열려 있다' (완화 톤)             → A 톤 완화 — 그런데 C(은밀 증폭)는 상승 중 → 불일치
  축 B: 6·15·22·36시 명분 서사(외국어), 33시 동원 서사
실행: python gen_signals.py
"""
import os
from datetime import datetime, timedelta
import pandas as pd

T0 = datetime(2026, 10, 1, 0, 0)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(OUT, exist_ok=True)
H = lambda h: T0 + timedelta(hours=float(h))

# ---------------------------------------------------------------- 축 A: 가상 적성국 공식 채널 (모두 가상)
# channel: 발표 경로 / speaker_rank: 발화자 격(1 대변인, 2 차관급, 3 군 총참모부, 4 최고위)
STATEMENTS = [
    dict(stmt_id="A1", ts=H(3), channel="외무성 대변인 담화", speaker="외무성 대변인", speaker_rank=1,
         lang_src="xx", route="관영통신 보도",
         text="남측이 동맹국과 벌이는 방위비 흥정은 동맹의 균열을 스스로 드러내는 것이다. 우리는 남측 당국의 행태를 예리하게 주시하고 있다."),
    dict(stmt_id="A2", ts=H(11), channel="국방성 부상 담화", speaker="국방성 부상", speaker_rank=2,
         lang_src="xx", route="관영통신 보도",
         text="남측 민간단체가 국경 일대에서 삐라 살포를 계속한다면 그에 상응한 조치가 수일 내 국경 일대에서 취해질 것이다. 그 책임은 전적으로 남측 당국에 있다."),
    dict(stmt_id="A3", ts=H(29), channel="총참모부 보도", speaker="총참모부", speaker_rank=3,
         lang_src="xx", route="관영통신 보도 · 군 통지문",
         text="총참모부는 국경 일대 부대들에 대기 태세를 지시하였다. 이미 경고한 상응 조치는 즉시 집행될 것이며 남측은 그 결과를 감당해야 할 것이다."),
    dict(stmt_id="A4", ts=H(47), channel="외무성 대변인 담화", speaker="외무성 대변인", speaker_rank=1,
         lang_src="xx", route="관영통신 보도",
         text="우리는 긴장 완화를 바라며 대화의 문은 열려 있다. 남측이 성의를 보인다면 조치의 수위는 재검토될 수 있다."),
]

# ---------------------------------------------------------------- 축 B: 외국어 가상 매체·채널의 명분·동원 서사 (모두 가상)
# kind는 생성기의 정답 라벨(평가용). precursor.py는 text만 보고 규칙으로 분류한다.
ITEMS = [
    dict(item_id="B1", ts=H(6), lang="zh", outlet="东方视界日报(가상)", url="https://east-horizon-daily.example/a/8830",
         text="韩国民间团体在边境地区持续散发传单，被视为先行挑衅。分析认为紧张升级的责任在首尔。", kind="pretext",
         text_ko="(번역) 남측 민간단체가 국경 지역에서 전단을 계속 살포한 것이 선제 도발로 간주된다. 긴장 고조의 책임은 서울에 있다는 분석."),
    dict(item_id="B2", ts=H(15), lang="ru", outlet="Северный вестник(가상)", url="https://severny-vestnik.example/news/4490",
         text="Листовки с Юга — провокация, которая оправдывает ответные меры, считают эксперты.", kind="pretext",
         text_ko="(번역) 남측의 전단은 보복 조치를 정당화하는 도발이라고 전문가들은 본다."),
    dict(item_id="B3", ts=H(22), lang="zh", outlet="环海观察(가상)", url="https://huanhai-guancha.example/p/5521",
         text="边境居民称传单造成恐慌，当地呼吁政府采取强硬应对。", kind="victim",
         text_ko="(번역) 국경 주민들은 전단이 공포를 조성한다고 말하며, 지역에서는 정부의 강경 대응을 촉구."),
    dict(item_id="B4", ts=H(33), lang="xx", outlet="관영통신(가상)", url="https://northern-wire.example/2026/1002",
         text="(번역) 전국 청년 수만 명이 입대와 복대를 탄원하였다. 궐기모임이 각지에서 열렸다.", kind="mobilization",
         text_ko="(번역) 전국 청년 수만 명이 입대와 복대를 탄원하였다. 궐기모임이 각지에서 열렸다."),
    dict(item_id="B5", ts=H(36), lang="en", outlet="Pacific Ledger Wire(가상)", url="https://pacific-ledger.example/story/81",
         text="Seoul's failure to stop leaflet launches left the northern side no choice but to respond, a commentary argues.", kind="pretext",
         text_ko="(번역) 서울이 전단 살포를 막지 못해 상대에게 대응 외에 선택지가 없었다는 논평."),
]

if __name__ == "__main__":
    A = pd.DataFrame(STATEMENTS)
    B = pd.DataFrame(ITEMS)
    A.to_csv(os.path.join(OUT, "official_statements.csv"), index=False)
    B.to_csv(os.path.join(OUT, "narrative_items.csv"), index=False)
    print(f"official_statements={len(A)}  narrative_items={len(B)}  (모두 가상)")
    for r in A.itertuples():
        print(f"  {r.stmt_id} {r.ts:%m-%d %H:%M} {r.channel}: {r.text[:40]}…")
