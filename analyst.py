"""
analyst.py — 분석관 판정 루프 · 결정론적 브리핑 초안 · 지휘관 요약 (2026-10-18 추가)

원칙
  · 시스템은 판정하지 않는다. 분석관이 burst 하나를 '정상(속보 동기화·자발적 공유)'으로 판정하면 그 burst를 근거에서 빼고
    의심 집단과 관찰 조건(의심 계정 5개 이상 + 외국어 출처)을 **다시 센다**. 그래도 단계는 자동으로 내려가지 않는다 —
    "해제 검토"로만 표시하고 해제는 분석관이 결정한다(기존 규칙: 단계 자동 하향 없음).
  · 모든 판정은 증거 체인(out/evidence_chain.jsonl)의 끝 해시에 이어 SHA-256으로 기록한다. 누가(가명 역할), 언제(벽시계),
    어느 시나리오 시각에, 어떤 burst를, 왜 판정했는지가 남는다. 판정을 지우거나 바꾸면 해시가 달라진다.
  · 브리핑 초안은 LLM 없이 카드의 구조화 필드만으로 만든다 → 오프라인·결정론적·검증 가능. 문장은 템플릿이고
    숫자는 전부 화면과 같은 파일에서 온다. "초안"이며 분석관 검토 전 문서임을 머리에 박는다.
  · 지휘관 요약은 같은 데이터를 숫자 3개 + 권고 1줄 + 하지 말 것으로 줄인 것이다. 새 판단을 더하지 않는다.

입력: out/accounts_score.csv(S), out/burst_members.csv(M), 화면이 가진 현재 시각·단계·권고·전조 행
출력: 함수 반환값(app.py·export_html.py가 같은 함수를 쓴다). 파일은 쓰지 않는다(판정 기록 내려받기는 화면에서).
"""
import hashlib, json, os
from datetime import datetime, timezone

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
CHAIN = os.path.join(OUT, "evidence_chain.jsonl")
MIN_SUSPECTS = 5
ROLE = "분석관(가명)"   # 실명·소속을 기록하지 않는다

JUDGMENTS = {
    "normal": ("정상 — 속보 동기화·자발적 공유", "이 burst는 근거에서 제외하고 의심 집단을 다시 센다"),
    "confirmed": ("조정 확인", "근거 유지. 분석관이 확인했다는 표시만 남긴다"),
    "hold": ("보류 — 추가 확인 필요", "근거는 유지하되 브리핑에 '확인 중'으로 적는다"),
}

LIMITS = [
    "합성 데이터의 계산값이며, 오탐률·조기성은 실데이터에서 검증되지 않았다",
    "뉴스 매체 사칭형(각자 시간에 게시)은 burst 층·URL-망 층 모두 놓친다(IRA 실데이터 0%)",
    "반박·팩트체크 답글도 같은 서사로 묶여 확산으로 집계될 수 있다(입장 판별 없음)",
    "전조 카드의 축 A·B 자료는 가상이고 추출은 규칙 기반이다. L5(국가 배후)는 공개 데이터로 판단 불가",
    "증거 체인은 내부 일관성만 증명한다(외부 타임스탬프 미연동)",
]

CONOPS = {
    "위치": "군 정보·사이버 분석관의 '외국발 서사 유입' 탐지 보조. 공개 데이터만 본다",
    "흐름": "탐지(관찰) → 근거 카드·증거 봉인 → 분석관 판정 → 지휘관 보고(이 화면) → 대응 수위 결정은 사람",
    "경계": "외국어 출처가 연결되지 않은 서사는 '국내 사안'으로 멈추고 올리지 않는다. 국내 대응·플랫폼 조치·수사는 관계 기관 이관 "
            "[확인 필요: 기관별 법적 근거·이관 절차]",
    "금지": "실존 개인 식별·추적·표적화 기능 없음. 일반 사용자는 집계로만, 가명 ID는 반복 조정 계정에만",
}


# ---------------------------------------------------------------- 판정 반영 재집계
def joined_times(S, M, nid, excluded=()):
    """제외한 burst를 뺀 뒤, 남은 burst에 2회 이상 참여한 의심 계정의 편입 시각(두 번째 남은 burst 종료) → {계정: 시각}.
    excluded가 비면 alerts.suspect_asof와 같은 결과"""
    sus = set(S[(S.narrative_id == nid) & (S.tier == "suspected")].account_id)
    m = M[(M.narrative_id == nid) & (M.account_id.isin(sus)) & (~M.burst_id.isin(list(excluded)))].copy()
    if m.empty:
        return {}
    m["burst_end"] = pd.to_datetime(m.burst_end)
    m = m.sort_values("burst_end")
    joined = m.groupby("account_id").burst_end.apply(lambda s: s.iloc[1] if len(s) >= 2 else pd.NaT).dropna()
    return joined.to_dict()


def suspects_asof(S, M, nid, t_now, excluded=()):
    """t_now까지 편입된 의심 계정 → {계정: 편입 시각}"""
    return {a: t for a, t in joined_times(S, M, nid, excluded).items() if t <= t_now}


def reassess(S, M, nid, t_now, excluded, foreign_seen, level):
    """판정 반영 전/후 의심 계정 수와 관찰 조건. 단계 자동 하향은 없다 — 문구로만 안내"""
    before = suspects_asof(S, M, nid, t_now)
    after = suspects_asof(S, M, nid, t_now, excluded)
    watch_met = len(after) >= MIN_SUSPECTS and bool(foreign_seen)
    if not excluded:
        note = "판정 없음 — 시스템 근거 그대로"
    elif level in ("WATCH", "ALERT", "CRITICAL") and not watch_met:
        note = (f"관찰 조건(의심 계정 {MIN_SUSPECTS}개 이상 + 외국어 출처) 미충족 → **단계 해제 검토**. "
                "자동 하향은 없다 — 해제는 분석관이 결정한다")
    elif level in ("ALERT", "CRITICAL"):
        note = "관찰 조건은 유지. 경보·위험 단계는 일반 사용자 간 R̂가 정하므로 burst 판정으로는 바뀌지 않는다"
    else:
        note = "관찰 조건 유지"
    return dict(n_before=len(before), n_after=len(after), watch_met=watch_met, note=note,
                removed=sorted(set(before) - set(after)), joined_after=after)


# ---------------------------------------------------------------- 판정 기록 (증거 체인에 이어 붙임)
def chain_end(path=CHAIN):
    if not os.path.exists(path):
        return "0" * 64
    last = None
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                last = json.loads(line)
    return (last or {}).get("record_sha256", "0" * 64)


def make_record(prev_hash, nid, hour, burst_id, judgment, reason, role=ROLE, recorded_at=None):
    body = dict(kind="analyst_judgment", narrative_id=int(nid), hour=int(hour), burst_id=int(burst_id),
                judgment=judgment, judgment_label=JUDGMENTS[judgment][0], reason=(reason or "").strip()[:300],
                role=role, recorded_at=recorded_at or datetime.now(timezone.utc).isoformat(timespec="seconds"),
                prev=prev_hash)
    body["record_sha256"] = hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
    return body


def verify_records(records, first_prev):
    """기록 묶음의 체인 검증: prev 연결 + 해시 재계산"""
    prev = first_prev
    for r in records:
        if r.get("prev") != prev:
            return False, f"연결 끊김 (burst {r.get('burst_id')})"
        body = {k: v for k, v in r.items() if k != "record_sha256"}
        h = hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
        if h != r.get("record_sha256"):
            return False, f"해시 불일치 (burst {r.get('burst_id')})"
        prev = h
    return True, f"기록 {len(records)}건 · 체인 끝 {prev[:12]}…"


# ---------------------------------------------------------------- 브리핑 초안 (템플릿 · LLM 없음)
def _f(x, nd=2, dash="—"):
    try:
        if x is None or (isinstance(x, float) and x != x):
            return dash
        return f"{float(x):.{nd}f}"
    except Exception:
        return dash


def briefing_md(ctx):
    """ctx: dict — nid, now, hour, level, level_name, policy(dict|None), foreign(list), bursts(list), reassess(dict),
    r(dict|None), disarm(list), pre(dict|None), judgments(list), confidence(str), chain_end(str)"""
    c = ctx
    L = []
    L.append(f"# 브리핑 초안 — 서사 N{c['nid']} · {c['now']} (시작 후 {c['hour']}시)")
    L.append("시스템 생성 초안(규칙 기반 템플릿 · LLM 미사용) · 분석관 검토 전 · 판정이 아니라 보조 자료 · 합성 데이터 시연")
    L.append("")
    pol = c.get("policy") or {}
    L.append("## 1. 요약")
    L.append(f"- 탐지 단계 **{c['level']} ({c['level_name']})** · 대응 권고 **{pol.get('action_label', '—')}** · 카드 신뢰도 {c.get('confidence', '—')}")
    fo = c.get("foreign") or []
    bb = c.get("bursts") or []
    ra = c.get("reassess") or {}
    lead = [f["lead_h"] for f in fo if f.get("lead_h") is not None and f["lead_h"] > 0]
    L.append(f"- 외국어 원문 {len(fo)}건" + (f"(한국어 첫 게시보다 최대 {max(lead):.1f}시간 앞섬)" if lead else "")
             + f" · 반복 동시 게시 burst {len(bb)}회 · 의심 계정 {ra.get('n_after', ra.get('n_before', '—'))}개"
             + (f"(판정 전 {ra['n_before']}개)" if ra.get("removed") else ""))
    pre = c.get("pre")
    if pre:
        L.append(f"- 전조 정합성 **{pre['state_label']}** (수렴 {pre['conv']}/3축)" + (f" · {pre['note']}" if pre.get("note") else ""))
    L.append("")
    L.append("## 2. 근거 (시각 t까지 알 수 있던 것만)")
    if fo:
        L.append("**외국어 출처 → 한국어 유입**")
        for f in fo:
            L.append(f"- `{f['lang']}` {f['ts']} · {f['url']}" + (f" · {f['lead_h']:.1f}시간 선행" if f.get("lead_h") else ""))
    else:
        L.append("- 외국어 출처 연결 없음 → 국내 사안(군 관할 아님)으로 분류, 단계 상향 없음")
    L.append("**조정 행위(동시 게시 burst)**")
    for b in bb:
        j = b.get("judgment")
        tag = f" · 분석관 판정: {JUDGMENTS[j][0]}" if j else ""
        L.append(f"- {b['start']}–{b['end']} · 계정 {b['n']}개 · 문장 유사도 {_f(b['sim'])}" + (f" · {b['url']}" if b.get("url") else "") + tag)
    r = c.get("r")
    if r and r.get("r") is not None:
        L.append(f"**일반 사용자 간 확산** R̂ {_f(r['r'])} (80% 구간 {_f(r.get('lo'))}~{_f(r.get('hi'))}) · P(R>1) {_f((r.get('p1') or 0) * 100, 0)}% · P(R>0.8) {_f((r.get('p08') or 0) * 100, 0)}%")
    dis = c.get("disarm") or []
    if dis:
        L.append("**DISARM 후보 기법** (후보이며 확정은 분석관): " + ", ".join(f"`{d['id']}` {d['name']}" for d in dis))
    if pre and pre.get("a_text"):
        L.append(f"**공식 신호(축 A)** {pre['a_text']}")
    if pre and pre.get("window"):
        L.append(f"**가능한 행동·시간창** {pre['window']}")
    L.append("")
    L.append("## 3. 권고와 하지 말 것")
    if pol:
        L.append(f"- **{pol.get('action_label', '—')}** — 확산 단계 {pol.get('stage_label', '—')} · 출처 귀속 {pol.get('attribution', '—')}")
        if pol.get("why_now"):
            L.append(f"- 왜 지금: {pol['why_now']}")
        if pol.get("why_level"):
            L.append(f"- 왜 이 수준: {pol['why_level']}")
    dn = c.get("do_not") or []
    if dn:
        L.append("- 하지 말 것: " + " / ".join(dn))
    if pol.get("escalate_if"):
        L.append(f"- 다음 재평가: {pol['escalate_if']}")
    L.append("")
    L.append("## 4. 분석관 판정 반영")
    js = c.get("judgments") or []
    if js:
        for j in js:
            L.append(f"- [{j['recorded_at']}] {j['hour']}시 · burst {j['burst_id']} → {j['judgment_label']}" + (f" ({j['reason']})" if j.get("reason") else "") + f" · 기록 {j['record_sha256'][:12]}…")
        L.append(f"- 재집계: {ra.get('note', '')}".replace("**", ""))
    else:
        L.append("- 판정 없음 — 시스템 근거 그대로")
    L.append("")
    L.append("## 5. 신뢰도와 한계")
    for x in LIMITS:
        L.append(f"- {x}")
    L.append("")
    L.append(f"증거 체인 끝 `{(c.get('chain_end') or '')[:16]}…` · 이 문서의 숫자는 모두 화면과 같은 파일(out/)에서 생성됨")
    return "\n".join(L)


def commander_summary(ctx):
    """지휘관 1화면 재료: 숫자 3개 + 권고 1줄 + 하지 말 것 + 다음 재평가. 새 판단을 더하지 않는다"""
    c = ctx
    pol = c.get("policy") or {}
    fo = c.get("foreign") or []
    lead = [f["lead_h"] for f in fo if f.get("lead_h") is not None and f["lead_h"] > 0]
    r = c.get("r") or {}
    ra = c.get("reassess") or {}
    pre = c.get("pre")
    return dict(
        headline=f"N{c['nid']} · {c['level']} {c['level_name']} · {pol.get('action_label', '권고 없음')}",
        numbers=[("의심 계정 (행동 기준)", f"{ra.get('n_after', ra.get('n_before', '—'))}개", (f"판정 전 {ra['n_before']}개" if ra.get("removed") else "판정 없음")),
                 ("외국어 원문 선행", f"{len(fo)}건", (f"한국어보다 최대 {max(lead):.1f}시간 앞섬" if lead else "연결 없음")),
                 ("자생 확산 확률 P(R>1)", "—" if r.get("p1") is None else f"{r['p1']:.0%}", ("R̂ " + _f(r.get("r"))) if r.get("r") is not None else "표본 부족")],
        precursor=((pre['state_label'], f"수렴 {pre['conv']}/3축") if pre else ("—", "해당 없음")),
        do_not=(c.get("do_not") or [])[:3],
        next_eval=pol.get("escalate_if", "—"),
        confidence=c.get("confidence", "—"),
        judgments=len(c.get("judgments") or []),
        conops=CONOPS,
    )
