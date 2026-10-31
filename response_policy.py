"""
response_policy.py — 대응 단계 권고 (A안)
※ 비판 검토 대화창 소유(프로젝트 문서 claude/response_policy.py.md, 19:05 최종판 · SPREAD_KEY=p_gt08 사용자 확정).
  작업 세션이 원문 그대로 반영.

탐지 신호를 "공작인가?"가 아니라 "지금 대응해야 하는가, 어떻게, 무엇을 하면 안 되는가"로 바꾼다.
판정이 아니라 분석관 보조다. 최종 결정은 사람이 한다.

설계 원칙
1. 대응 수위는 '조정 증거'가 아니라 '확산 단계'가 올린다.
   (일반인에게 번지지 않은 공작에 공개 대응하면 오히려 서사를 증폭시킨다)
2. '조정 증거'는 대응 수위가 아니라 '외국발이라고 말해도 되는가'를 정한다.
3. "대응 불필요"도 정답이 될 수 있어야 한다.
4. 모든 권고에 다음 재평가 조건(escalate_if)을 붙인다.

확산 단계는 Ben Nimmo의 Breakout Scale(2020)에서 착안해 단일 플랫폼용으로 단순화했다.
임계값은 모두 가정값이다 → 민감도 분석 대상.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import IntEnum
import math
from typing import Optional

# ── 가정값 (민감도 분석 대상) ──────────────────────────────
ORGANIC_MIN = 5        # S2 진입: 일반 사용자 반응(집계) 최소 건수
P_SPREAD = 0.5         # S3 진입: 확률 기준
SPREAD_KEY = "p_gt08"  # 사용자 확정(18:40): ALERT와 정렬. "p_gt1"이면 CRITICAL과 정렬


class Coord(IntEnum):
    """조정 증거 강도 (coordination.py 등급에서 매핑)"""
    NONE = 0     # 조정 신호 없음
    WEAK = 1     # 1회성 burst, 팬덤형 합의 게시 등
    STRONG = 2   # 반복 burst + 신생 계정 + 동일 원고/URL


class Stage(IntEnum):
    """확산 단계"""
    S1_INSIDE = 1   # 의심 집단 내부에서만 돈다
    S2_CONTACT = 2  # 일반인 반응이 생겼으나 재생산은 미약
    S3_SPREAD = 3   # 일반인 사이 자생 재생산 (P(R>1) 높음)
    S4_BRIDGE = 4   # 대형 일반 계정·언론이 인용 (교량 사건)


class Action(IntEnum):
    NONE = 0
    MONITOR = 1
    PREBUNK_READY = 2
    PREBUNK = 3
    OFFICIAL = 4


ACTION_LABEL = {
    Action.NONE: "대응 불필요",
    Action.MONITOR: "관찰·증거 봉인",
    Action.PREBUNK_READY: "사전 반박 준비",
    Action.PREBUNK: "사전 반박 실행 검토",
    Action.OFFICIAL: "공식 대응 검토",
}

STAGE_LABEL = {
    Stage.S1_INSIDE: "1단계 · 의심 집단 내부",
    Stage.S2_CONTACT: "2단계 · 일반인 접촉",
    Stage.S3_SPREAD: "3단계 · 일반인 자생 확산",
    Stage.S4_BRIDGE: "4단계 · 주류 진입",
}

# SPREAD_KEY 에 따라 바뀌는 문구 (호출 시점에 SPREAD_KEY 를 읽는다)
P_TEXT = {"p_gt1": "P(R>1)", "p_gt08": "P(R>0.8)"}
S3_TEXT = {"p_gt1": "3단계 · 일반인 자생 확산",
           "p_gt08": "3단계 · 일반인 자생 확산 임박(R≈1)"}


def p_label() -> str:
    return P_TEXT.get(SPREAD_KEY, SPREAD_KEY)


def stage_label(st: "Stage") -> str:
    if st == Stage.S3_SPREAD:
        return S3_TEXT.get(SPREAD_KEY, STAGE_LABEL[st])
    return STAGE_LABEL[st]


@dataclass
class Signals:
    narrative_id: str
    coord: Coord
    organic_engaged: int               # 일반 사용자 반응 수 (집계값만, 개별 ID 없음)
    p_r_gt_1: Optional[float] = None   # SPREAD_KEY 확률(P(R>1) 또는 P(R>0.8)); 표본 부족이면 None
    bridge_event: Optional[bool] = None  # 대형 일반 계정·언론 인용. None = 데이터 없음(판단 불가)
    foreign_origin_linked: int = 0     # 서사 중심에 연결된 외국어 원문 수
    sensitive_topic: bool = False      # 분석관이 붙이는 태그 (자동 판단 아님)
    detection_confidence: float = 0.5  # 탐지 단계 신뢰도 0~1


@dataclass
class Recommendation:
    narrative_id: str
    stage: Stage
    action: Action
    attribution: str                   # 외국발 언급 가능 / 보류 / 금지
    why_now: str
    why_level: str
    do_not: list[str] = field(default_factory=list)
    escalate_if: str = ""
    confidence: float = 0.5
    notes: list[str] = field(default_factory=list)
    domestic: bool = False
    stage_text: str = ""

    @property
    def action_label(self) -> str:
        if self.domestic and self.action == Action.MONITOR:
            return "관찰(집계만) — 국내 사안, 증거 봉인 대상 아님"
        return ACTION_LABEL[self.action]

    def card(self) -> str:
        lines = [
            f"[{self.narrative_id}] 권고: {self.action_label}",
            f"  확산 단계 : {self.stage_text or stage_label(self.stage)}",
            f"  출처 귀속 : {self.attribution}",
            f"  왜 지금   : {self.why_now}",
            f"  왜 이 수준: {self.why_level}",
        ]
        for d in self.do_not:
            lines.append(f"  하지 말 것: {d}")
        lines.append(f"  다음 재평가: {self.escalate_if}")
        for n in self.notes:
            lines.append(f"  참고     : {n}")
        lines.append(f"  신뢰도   : {self.confidence:.2f}  (판정이 아니라 분석관 보조)")
        return "\n".join(lines)


def signals_from_r_row(narrative_id: str, row: dict, coord: Coord, organic_engaged: int,
                       foreign_origin_linked: int, sensitive_topic: bool = False,
                       detection_confidence: float = 0.5, bridge_event: Optional[bool] = None) -> Signals:
    """out/r_series.csv 한 행(시각 t)에서 Signals 생성.
    p_gt1 이 비어 있으면(표본 부족) None. 'domestic' 열이 참이면 외국 출처 0으로 취급."""
    p = row.get(SPREAD_KEY)
    try:
        p = None if p in (None, "") else float(p)
        if p is not None and math.isnan(p):
            p = None
    except (TypeError, ValueError):
        p = None
    if str(row.get("domestic", "")).lower() in ("1", "true"):
        foreign_origin_linked = 0
    return Signals(narrative_id, coord, organic_engaged, p, bridge_event,
                   foreign_origin_linked, sensitive_topic, detection_confidence)


def classify_stage(s: Signals) -> Stage:
    if s.bridge_event is True:
        return Stage.S4_BRIDGE
    if s.p_r_gt_1 is not None and s.p_r_gt_1 >= P_SPREAD:
        return Stage.S3_SPREAD
    if s.organic_engaged >= ORGANIC_MIN:
        return Stage.S2_CONTACT
    return Stage.S1_INSIDE


def escalate(st: Stage) -> str:
    return {
        Stage.S1_INSIDE: f"일반 사용자 반응 {ORGANIC_MIN}건 이상",
        Stage.S2_CONTACT: f"{p_label()} ≥ {P_SPREAD}",
        Stage.S3_SPREAD: "대형 일반 계정 또는 언론 인용 발생 (교량 데이터 없으면 분석관 수동 확인)",
        Stage.S4_BRIDGE: "재평가 주기 단축, 대응 효과 추적",
    }[st]


def _attribution(s: Signals) -> str:
    if s.coord == Coord.STRONG and s.foreign_origin_linked > 0:
        return "외국발 근거 충분 (조정 증거 + 외국어 원문 연결, 봉인된 근거 첨부) — 공개 언급 여부는 대응 단계에 따름"
    if s.foreign_origin_linked == 0:
        return "국내 사안 — 군 관할 아님 (외국어 출처 연결 없음)"
    return "금지 (조정 증거 부족 — 자국민 표현일 수 있음)"


def recommend(s: Signals) -> Recommendation:
    st = classify_stage(s)
    do_not: list[str] = []
    notes: list[str] = []

    if s.coord == Coord.STRONG:
        if st == Stage.S1_INSIDE:
            act = Action.MONITOR
            why_level = "조정 증거는 강하지만 일반인에게 번지지 않음"
            do_not.append("공개 반박·공식 발표 (아무도 안 보는 서사를 키울 수 있음)")
            notes.append("플랫폼 신고 경로 검토")
        elif st == Stage.S2_CONTACT:
            act = Action.PREBUNK_READY
            why_level = "조정 증거 강함 + 일반인 접촉 시작"
            do_not.append("특정 일반 사용자 지목")
        elif st == Stage.S3_SPREAD:
            act = Action.PREBUNK
            why_level = ("일반인 자생 확산 임박" if SPREAD_KEY == "p_gt08" else "일반인 자생 확산 진입") \
                + " — 출처 근거가 아직 선명한 마지막 구간"
            do_not.append("일반 사용자 게시물 자체를 공작으로 규정")
        else:
            act = Action.OFFICIAL
            why_level = "주류 진입 — 대응 비용이 이미 커진 단계"
            do_not.append("일반 사용자 게시물 자체를 공작으로 규정")
    elif s.coord == Coord.WEAK:
        # 사전 반박은 '내용'에 문제가 있을 때만 의미가 있다. 확산 규모만으로 올리지 않는다.
        if st >= Stage.S3_SPREAD and s.sensitive_topic:
            act = Action.PREBUNK_READY
            why_level = "확산 크고 민감 주제, 조정 증거는 약함 — 출처 언급 없이 내용 대응만"
        else:
            act = Action.MONITOR
            why_level = "조정 신호가 약함 (팬덤·합의된 동시 게시 가능성)"
        do_not.append("외국 공작으로 지칭")
    else:  # NONE
        if st >= Stage.S3_SPREAD and s.sensitive_topic:
            act = Action.MONITOR
            why_level = "자연 확산이지만 민감 주제 — 내용 팩트체크만 검토"
        else:
            act = Action.NONE
            why_level = "조정 신호 없음 — 정상 여론으로 간주"
        do_not.append("외국 공작으로 지칭")

    # 관할 제한: 외국어 출처가 연결되지 않은 서사는 국내 사안 → 군은 관찰까지만
    if s.foreign_origin_linked == 0 and act > Action.MONITOR:
        act = Action.MONITOR
        why_level += " / 외국어 출처 없음 → 국내 사안, 군 관할 아님"
        notes.append("필요 시 민간 팩트체크·소관 기관 이관 검토")
    if s.bridge_event is None and st >= Stage.S3_SPREAD:
        notes.append("교량 사건: 데이터 없음 — 주류 진입 여부 판단 불가")

    domestic = s.foreign_origin_linked == 0

    if s.sensitive_topic and act >= Action.PREBUNK_READY:
        notes.append("군·안보 관련 주제 — 관련 기관 이관 검토 [국내 대응 주체 역할 분담 확인 필요]")
    if act >= Action.PREBUNK_READY:
        # 2026-10-26 추가: 사전 반박(접종) 효과의 지속 기간 근거 — Maertens 외 2025, Nature Communications (5개 종단 실험, N=11,759):
        # 텍스트·영상형 접종 효과는 약 1개월 지속, 게임형은 더 빨리 감소, 기억 부스터(재노출)로 연장. → 1회성 대응으로 끝내지 말 것.
        notes.append("사전 반박 효과는 약 1개월 지속(텍스트·영상형, Maertens 외 2025) — 감시창이 길면 부스터(재노출) 계획 포함")
        notes.append("대응 대상에 인프라(호스팅·등록대행·사칭 도메인) 포함 검토 — EEAS 4차 보고서(2026) 억지 플레이북 방향")

    conf = s.detection_confidence
    if s.p_r_gt_1 is None and st <= Stage.S2_CONTACT:
        notes.append("일반인 재생산 표본 부족 — 확산 단계 판단 불확실")
        conf *= 0.8

    return Recommendation(
        domestic=domestic,
        narrative_id=s.narrative_id,
        stage=st,
        action=act,
        attribution=_attribution(s),
        stage_text=stage_label(st),
        why_now=f"{stage_label(st)} (일반 반응 {s.organic_engaged}건, "
                f"{p_label()}={'표본 부족' if s.p_r_gt_1 is None else f'{s.p_r_gt_1:.2f}'})",
        why_level=why_level,
        do_not=do_not,
        escalate_if=("조정 신호(반복 burst·신생 계정 몰림) 발생" if act == Action.NONE
                     else escalate(st)),
        confidence=round(conf, 2),
        notes=notes,
    )


if __name__ == "__main__":
    # 시연 시나리오 (수치는 예시값 — 실제 연결 시 alerts.py 출력으로 대체)
    cases = [
        Signals("공작 14시", Coord.STRONG, organic_engaged=2, p_r_gt_1=None,
                foreign_origin_linked=4, sensitive_topic=True, detection_confidence=0.8),
        Signals("공작 26시", Coord.STRONG, organic_engaged=40, p_r_gt_1=0.62,
                foreign_origin_linked=4, sensitive_topic=True, detection_confidence=0.85),
        Signals("공작 50시", Coord.STRONG, organic_engaged=300, p_r_gt_1=0.9, bridge_event=True,
                foreign_origin_linked=4, sensitive_topic=True, detection_confidence=0.85),
        Signals("확산 실패형 공작", Coord.STRONG, organic_engaged=1, p_r_gt_1=None,
                foreign_origin_linked=2, detection_confidence=0.8),
        Signals("팬덤", Coord.WEAK, organic_engaged=120, p_r_gt_1=0.7, detection_confidence=0.5),
        Signals("약한 조정 + 민감 주제", Coord.WEAK, organic_engaged=120, p_r_gt_1=0.7,
                sensitive_topic=True, detection_confidence=0.5),
        Signals("자연 바이럴", Coord.NONE, organic_engaged=500, p_r_gt_1=0.95,
                bridge_event=True, detection_confidence=0.6),
        Signals("국내 조직 행동 (외국 출처 없음)", Coord.STRONG, organic_engaged=80, p_r_gt_1=0.7,
                foreign_origin_linked=0, sensitive_topic=True, detection_confidence=0.8),
    ]
    for c in cases:
        print(recommend(c).card())
        print()
