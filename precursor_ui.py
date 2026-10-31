"""
precursor_ui.py — 전조 카드 화면 요소 (app.py에서 사용 · 2026-10-17 추가)
out/precursor.json을 읽어 (1) 4축 타임라인 + 정합성 띠, (2) 전조 카드 HTML, (3) 발언 구조화 HTML, (4) 유사 사례 HTML을 만든다.
화면 논리는 app.py와 같다: 관측 시각 H 이전에 알 수 있었던 것만 보여준다.
"""
import html, json, os
import plotly.graph_objects as go
from plotly.subplots import make_subplots

HERE = os.path.dirname(os.path.abspath(__file__))
AX = {"A": "#6c4ad6", "B": "#0f9d8a", "C": "#eb6834", "D": "#9a9a94"}
LVC = {"NONE": "#d9d8d2", "REVIEW": "#b5b4ad", "WATCH": "#fab219", "ALERT": "#ec835a", "CRITICAL": "#d03b3b"}
STATE = {"none": ("·", "#8a8a85", "신호 없음"), "watch": ("◇", "#8a8a85", "관찰"), "rhetoric_only": ("◆", "#6c4ad6", "수사 단독"),
         "partial": ("◐", "#e0a000", "부분 수렴"), "converged": ("●", "#d03b3b", "수렴"), "mismatch": ("⚡", "#8e24aa", "불일치")}
STATE_WHY = {
    "none": "어느 축에도 신호가 없습니다.",
    "watch": "한 축에 약한 신호만 있습니다. 카드는 만들지 않습니다.",
    "rhetoric_only": "공식 발언(축 A)만 강하고 서사(축 B)·은밀 증폭(축 C)은 조용합니다. 과거 라이브러리에는 사건 없는 급등 사례가 있어 공식 축 단독으로는 경보하지 않습니다.",
    "partial": "한 축만 기준을 넘었습니다. 다른 축의 변화를 기다립니다.",
    "converged": "두 축 이상이 같은 방향입니다. 공개 발언의 예고 시간창과 은밀 증폭이 겹치는 구간입니다.",
    "mismatch": "공식 발언은 완화됐는데 은밀 증폭은 오르고 있습니다. 말과 행동이 어긋나는 구간 — 공식 발언만 믿고 경계를 낮추지 않습니다.",
}
FIELD = {"conditional": ("조건부", "#6c4ad6"), "deadline": ("시한", "#d03b3b"), "place": ("장소", "#0f9d8a"),
         "means": ("수단", "#eb6834"), "blame": ("책임 전가", "#8a8a85"), "threat": ("위협", "#b23a48"),
         "announce": ("예고 서술어", "#7a5c00"), "soft": ("완화", "#2a78d6")}
TONE = {"threat": "위협", "soft": "완화", "neutral": "중립", "announce": "예고"}
RANK = {1: "대변인", 2: "차관급", 3: "군 총참모부", 4: "최고위"}
KIND_SYM = {"pretext": "circle", "victim": "triangle-up", "mobilization": "square", "other": "x"}
LADDER_C = {"확인": "#1baf7a", "부분": "#e0a000", "미확인": "#b5b4ad", "판단 불가": "#8a8a85"}


def load(path=None):
    path = path or os.path.join(HERE, "out", "precursor.json")
    return json.load(open(path, encoding="utf-8")) if os.path.exists(path) else None


def row_at(PRE, h):
    return next((s for s in PRE["series"] if s["h"] == h), PRE["series"][0])


def timeline_fig(PRE, h, height=430):
    """위: 4축 타임라인(관측 시각까지) · 아래: 수렴 축 수와 상태 띠"""
    max_h = PRE["max_h"]
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.68, 0.32], vertical_spacing=0.08)
    lanes = {"D": 0, "C": 1, "B": 2, "A": 3}
    # D: 데이터 없음
    fig.add_scatter(x=[0, max_h], y=[lanes["D"]] * 2, mode="lines", line=dict(color=AX["D"], width=1, dash="dot"),
                    hoverinfo="skip", showlegend=False, row=1, col=1)
    fig.add_annotation(x=max_h / 2, y=lanes["D"], text="데이터 없음 — 항만·선박·위성 전조는 연결 예정(T2-3·T2-4)", showarrow=False,
                       font=dict(size=11, color=AX["D"]), yshift=11, row=1, col=1)
    # C: 시각별 단계 (관측 시각까지)
    cs = [s for s in PRE["series"] if s["h"] <= h]
    fig.add_scatter(x=[s["h"] for s in cs], y=[lanes["C"]] * len(cs), mode="markers",
                    marker=dict(symbol="square", size=10, color=[LVC[s["c_label"]] for s in cs], line=dict(width=0)),
                    customdata=[s["c_label"] for s in cs], hovertemplate="%{x}시 · 축 C 단계 %{customdata}<extra></extra>",
                    name="C 은밀 증폭 단계", showlegend=False, row=1, col=1)
    # B: 서사 항목
    bi = [x for x in PRE["items"] if x["h"] <= h]
    if bi:
        fig.add_scatter(x=[x["h"] for x in bi], y=[lanes["B"]] * len(bi), mode="markers",
                        marker=dict(symbol=[KIND_SYM[x["kind"]] for x in bi], size=13, color=AX["B"], line=dict(color="white", width=1)),
                        text=[f"{x['ts']} · {x['lang']} · {x['outlet']}<br>{x['kind_label']}<br>{x['text_ko'][:60]}" for x in bi],
                        hovertemplate="%{text}<extra>B</extra>", showlegend=False, row=1, col=1)
    # A: 발언 (크기 = 수준, 빈 마름모 = 완화 톤)
    sa = [s for s in PRE["statements"] if s["h"] <= h]
    if sa:
        fig.add_scatter(x=[s["h"] for s in sa], y=[lanes["A"]] * len(sa), mode="markers+text",
                        marker=dict(symbol=["diamond-open" if s["tone"] == "soft" else "diamond" for s in sa],
                                    size=[10 + 5 * s["level"] for s in sa], color=AX["A"], line=dict(color=AX["A"], width=2)),
                        text=[f"{s['stmt_id']} L{s['level']}" for s in sa], textposition="top center", textfont=dict(size=11, color=AX["A"]),
                        customdata=[f"{s['ts']} · {s['channel']}<br>{s['level_why']} · 톤 {TONE[s['tone']]}<br>{s['text'][:70]}…" for s in sa],
                        hovertemplate="%{customdata}<extra>A</extra>", showlegend=False, row=1, col=1)
        # 예고 시간창 (시한이 있는 수준 3 발언): 발언 시각 + 시한 범위
        for s in sa:
            if s["level"] >= 3 and s.get("deadline_hours"):
                lo, hi = s["deadline_hours"]
                fig.add_shape(type="rect", x0=s["h"] + lo, x1=min(s["h"] + hi, max_h), y0=lanes["A"] - 0.28, y1=lanes["A"] + 0.28,
                              fillcolor=AX["A"], opacity=0.10, line=dict(color=AX["A"], width=1, dash="dot"), row=1, col=1)
    # 아래: 수렴 축 수 + 상태 띠
    xs = [s["h"] for s in cs]
    fig.add_scatter(x=xs, y=[s["conv"] for s in cs], mode="lines", line=dict(shape="hv", color="#1f1f1d", width=2),
                    fill="tozeroy", fillcolor="rgba(31,31,29,0.06)", hovertemplate="%{x}시 · 수렴 축 %{y}/3<extra></extra>",
                    showlegend=False, row=2, col=1)
    run_start, run_state = None, None
    for s in cs + [None]:
        st = s["state"] if s else None
        if st != run_state:
            if run_state in ("rhetoric_only", "converged", "mismatch"):
                fig.add_shape(type="rect", x0=run_start - 0.5, x1=(s["h"] if s else h) - 0.5, y0=0, y1=3.3,
                              fillcolor=STATE[run_state][1], opacity=0.12, line_width=0, row=2, col=1)
            run_start, run_state = (s["h"] if s else None), st
    for row in (1, 2):
        fig.add_vline(x=h, line_dash="dot", line_color="#6b6b66", row=row, col=1)
    fig.update_yaxes(tickvals=[0, 1, 2, 3], ticktext=["D 물리 전조", "C 은밀 증폭", "B 명분·동원", "A 공식 신호"],
                     range=[-0.6, 3.75], showgrid=True, gridcolor="#f0efe9", zeroline=False, row=1, col=1)
    fig.update_yaxes(range=[0, 3.3], tickvals=[0, 1, 2, 3], ticktext=["0", "1", "2", "3축"], gridcolor="#eee", row=2, col=1)
    fig.add_annotation(xref="paper", yref="paper", x=0, y=0.30, xanchor="left", yanchor="bottom", text="수렴 축 수 · 띠 = 상태",
                       showarrow=False, font=dict(size=11, color="#6b6b66"))
    fig.update_xaxes(range=[0, max_h], row=1, col=1)
    fig.update_xaxes(range=[0, max_h], title="시작 후 시간", row=2, col=1)
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=36, b=10), plot_bgcolor="white", paper_bgcolor="white",
                      title=dict(text="네 축의 전조 신호와 정합성 — 관측 시각까지 보이는 것만 · 보라 점선 띠 = 공식 발언의 예고 시간창", font=dict(size=14)),
                      font=dict(family="-apple-system, Apple SD Gothic Neo, sans-serif", size=12))
    return fig


def badge(state):
    ic, col, name = STATE[state]
    return f"<span style='color:{col};font-weight:700'>{ic} {name}</span>"


def base_statement(PRE, h):
    """기준 발언 = 관측 시각까지 수준이 가장 높은 발언(동률이면 최신). 구조·유사 사례는 이 발언으로 본다"""
    sa = [s for s in PRE["statements"] if s["h"] <= h]
    return max(sa, key=lambda s: (s["level"], s["h"])) if sa else None


def axis_chips(PRE, row):
    sa = [s for s in PRE["statements"] if s["h"] <= row["h"]]
    base = base_statement(PRE, row["h"])
    a_txt = f"L{row['a_level']}" + (f" · {base['stmt_id']} {base['level_why'].split(' · ')[-1]}" if base and row["a_level"] >= 2 else "")
    if row["a_tone"] == "soft" and sa:
        a_txt += f" · 최신 {sa[-1]['stmt_id']} 톤 완화"
    b_txt = {0: "없음", 1: f"항목 {row['b_items']}건", 2: f"다국어 명분 서사 확인 ({row['b_items']}건)"}[row["b_level"]]
    c_txt = row["c_label"]
    chips = [("A 공식 신호", a_txt, AX["A"], row["a_level"] >= 2), ("B 명분·동원", b_txt, AX["B"], row["b_level"] >= 2),
             ("C 은밀 증폭", c_txt, AX["C"], row["c_level"] >= 2), ("D 물리 전조", "데이터 없음", AX["D"], False)]
    out = []
    for name, txt, col, on in chips:
        out.append(f"<div style='flex:1;min-width:120px;border:1.5px solid {col if on else '#e6e5df'};border-radius:10px;padding:8px 10px;"
                   f"background:{col + '14' if on else '#fff'}'><div style='font-size:12px;color:{col};font-weight:700'>{name}</div>"
                   f"<div style='font-size:13px;margin-top:2px'>{html.escape(txt)}</div></div>")
    return "<div style='display:flex;gap:8px;flex-wrap:wrap'>" + "".join(out) + "</div>"


def window_text(PRE, row, t0):
    """공식 발언의 시한 + 유사 사례 선행 일수로 '가능한 행동·시간창'을 만든다 (가상 시나리오 시각)"""
    import pandas as pd
    sa = [s for s in PRE["statements"] if s["h"] <= row["h"] and s["level"] >= 3 and s.get("deadline_hours")]
    if not sa:
        return "공식 발언에 시한이 없어 시간창을 만들지 않습니다."
    s = sa[-1]
    lo, hi = s["deadline_hours"]
    t_s = pd.Timestamp(t0) + pd.Timedelta(hours=s["h"])
    a, b = t_s + pd.Timedelta(hours=lo), t_s + pd.Timedelta(hours=hi)
    prec = [c for c in s["similar"] if c["kind"] == "precedent" and c["match"] >= 2 and "A" in c.get("axes", ["A"])]
    means = " · ".join(s["fields"].get("means", [])) or "수단 미명시(상응 조치)"
    place = " · ".join(dict.fromkeys(s["fields"].get("place", []))) or "장소 미명시"
    txt = (f"<b>{html.escape(means)}</b> 가능성 · 장소 <b>{html.escape(place)}</b> · 시한 '{html.escape(s['fields']['deadline'][0])}' → "
           f"<b>{a:%m-%d %H:%M} ~ {b:%m-%d %H:%M}</b> (발언 {s['stmt_id']} 기준, 가상 시나리오 시각)")
    if prec:
        txt += "<br><span class='muted'>유사 사례 선행: " + " · ".join(f"{c['name'].split(' (')[0]} {c['lead_days']}일" for c in prec) + \
               f" → 라이브러리 기준 {min(c['lead_days'] for c in prec)}~{max(c['lead_days'] for c in prec)}일</span>"
    return txt


def card_html(PRE, row, t0, pol=None):
    """전조 카드 본문 (왼쪽 열). pol: policy.csv의 그 시각 행(dict) 또는 None"""
    ladder = "".join(
        f"<div style='display:flex;align-items:center;gap:8px;margin:3px 0;font-size:13px'>"
        f"<span style='width:26px;font-weight:700;color:{LADDER_C[l['status']]}'>{l['level']}</span>"
        f"<span style='flex:1'>{l['name']}</span>"
        f"<span style='font-size:12px;padding:1px 8px;border-radius:10px;background:{LADDER_C[l['status']]}22;color:{LADDER_C[l['status']]};font-weight:700'>{l['status']}</span>"
        f"<span class='muted' style='width:42%;font-size:12px'>{html.escape(l['note'])}</span></div>" for l in row["ladder"])
    dn = ["공식 발언(축 A)만으로 경보 단계를 올리지 않기", "특정 일반 사용자 지목 금지"]
    if pol is not None and pol.get("do_not"):
        dn += [x for x in str(pol["do_not"]).split(" | ") if x and x not in dn]
    if row["state"] == "mismatch":
        dn.insert(0, "완화 발언을 근거로 경계·관찰을 낮추기")
    reeval = ["축 A 새 발언(톤·시한 변화)", "축 C burst 재발 또는 단계 상승", "예고 시한 경과 시 상태 재계산"]
    rec = pol["action_label"] if pol is not None else (row.get("policy") or "—")
    sa = [s for s in PRE["statements"] if s["h"] <= row["h"]]
    conf = {"none": "—", "watch": "낮음", "rhetoric_only": "낮음 (공개 1축)", "partial": "낮음~중간",
            "converged": "중간 (공개 2축 + 은밀 축 확인)" if row["c_level"] >= 2 else "중간 (공개 2축)",
            "mismatch": "중간 — 해석 주의"}[row["state"]]
    return f"""
<div style='font-size:13px;color:#6b6b66'>전조 카드 (분석관 보조 · 판정 아님 · 최종 결정은 사람)</div>
<div style='font-size:22px;margin:2px 0 10px'>{badge(row['state'])} <span style='font-size:14px;color:#6b6b66'>수렴 {row['conv']}/3축 · {row['h']}시</span></div>
{axis_chips(PRE, row)}
<div style='margin:10px 0 4px;font-size:14px'>{STATE_WHY[row['state']]}</div>
<div style='margin-top:10px'><b>가능한 행동·시간창</b><div style='font-size:14px;margin-top:2px'>{window_text(PRE, row, t0)}</div></div>
<div style='margin-top:10px'><b>증거 사다리</b> <span class='muted'>— 공개 데이터로 할 수 있는 주장의 단계</span>{ladder}</div>
<div style='display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:10px;font-size:14px'>
 <div><b>권고</b> {html.escape(str(rec))}<br><span class='muted'>대응 수위는 확산 단계(기존 권고)가 정하고, 전조 카드는 '언제·무엇을 경계할지'를 더한다</span></div>
 <div><b>하지 말 것</b><ul style='margin:4px 0;padding-left:18px'>{''.join(f'<li>{html.escape(x)}</li>' for x in dn)}</ul></div>
</div>
<div style='margin-top:6px;font-size:14px'><b>다음 재평가</b> {' · '.join(reeval)} · <b>신뢰도</b> {conf}</div>
<div class='muted' style='margin-top:6px'>축 A·B 자료는 가상(합성) · 추출·분류는 규칙 기반(시연, 운용 시 LLM 교체) · L5는 공개 데이터로 판단 불가.</div>"""


def statement_html(s):
    """원문에 구조 필드를 색으로 표시하고, 필드 표를 붙인다 (인용 없는 필드는 표에 없다)"""
    t, out, pos = s["text"], [], 0
    spans = sorted(s["spans"], key=lambda x: (x[0], -(x[1] - x[0])))
    last_end = 0
    for a, b, k in spans:
        if a < last_end:  # 겹치는 구간은 바깥 구간 우선
            continue
        out.append(html.escape(t[last_end:a]))
        name, col = FIELD[k]
        out.append(f"<span title='{name}' style='border-bottom:2px solid {col};background:{col}14;padding:0 1px'>{html.escape(t[a:b])}</span>")
        last_end = b
    out.append(html.escape(t[last_end:]))
    legend = " ".join(f"<span style='font-size:11px;color:{c};border-bottom:2px solid {c}'>{n}</span>" for n, c in FIELD.values())
    rows = [("발화자 격", f"{s['speaker']} ({RANK.get(s['speaker_rank'], '—')}) · {s['channel']} · {s['route']}"),
            ("조건", " / ".join(s["fields"].get("conditional", [])) or "없음"),
            ("시한", " / ".join(s["fields"].get("deadline", [])) or "없음"),
            ("장소", " / ".join(dict.fromkeys(s["fields"].get("place", []))) or "없음"),
            ("수단", " / ".join(dict.fromkeys(s["fields"].get("means", []))) or "미명시"),
            ("책임 전가 대상", " / ".join(dict.fromkeys(s["fields"].get("blame", []))) or "없음"),
            ("톤", TONE[s["tone"]] + (" — 위협 표현과 혼재" if s["tone"] == "soft" and s["fields"].get("threat") else ""))]
    tbl = "".join(f"<tr><td style='color:#6b6b66;white-space:nowrap;padding:3px 8px 3px 0'>{k}</td><td style='padding:3px 0'>{html.escape(v)}</td></tr>" for k, v in rows)
    return f"""<div style='font-size:12px;color:#6b6b66'>기준 공식 발언 {s['stmt_id']} · {s['ts']} · 수준 L{s['level']} ({s['level_why']}) · 원문은 가상 번역문</div>
<div style='font-size:15px;line-height:1.7;margin:6px 0;padding:10px 12px;border-left:3px solid {AX['A']};background:#faf9ff'>“{''.join(out)}”</div>
<div style='margin-bottom:6px'>{legend}</div><table style='font-size:13px;border-collapse:collapse'>{tbl}</table>
<div class='muted' style='margin-top:4px'>인용 구절이 없는 필드는 채우지 않는다(환각 차단). 규칙 기반 추출(시연).</div>"""


def latest_note_html(PRE, h):
    """기준 발언과 최신 발언이 다를 때(예: 완화 담화) 최신 발언을 짧게 보여준다"""
    sa = [s for s in PRE["statements"] if s["h"] <= h]
    base = base_statement(PRE, h)
    if not sa or sa[-1] is base:
        return ""
    s = sa[-1]
    cond = " / ".join(s["fields"].get("conditional", []))
    return (f"<div style='margin-top:8px;padding:8px 12px;border-left:3px solid {FIELD['soft'][1] if s['tone']=='soft' else AX['A']};background:#f6f9fe;font-size:13px'>"
            f"<b>최신 발언 {s['stmt_id']}</b> · {s['ts']} · {s['channel']} · 톤 <b>{TONE[s['tone']]}</b>"
            f"{(' · 조건: ' + html.escape(cond)) if cond else ''}<br><span style='color:#1f1f1d'>“{html.escape(s['text'])}”</span>"
            f"<br><span class='muted'>기준 발언({base['stmt_id']})의 예고는 철회되지 않았다. 완화 발언은 톤 변화로만 기록한다.</span></div>")


def cases_html(s, cases, state=None):
    """유사 과거 사례: 선행 일수 막대 (반례·오경보 구분). 불일치 상태면 기만 반례를 맨 앞에 둔다"""
    byid = {c["id"]: c for c in cases}
    mx = 8.0
    rows = []
    sims = list(s["similar"])
    if state == "mismatch" and not any(m["id"] == "X1" for m in sims):
        x1 = byid["X1"]
        sims.insert(0, dict(id="X1", kind="counter", name=x1["name"], match=0, lead_days=x1["lead_days"], matched=[]))
    for m in sims:
        c = byid[m["id"]]
        ld = c["lead_days"]
        col = {"precedent": AX["A"], "counter": "#8e24aa", "false_alarm": "#8a8a85"}[c["kind"]]
        w = 0 if ld is None else min(ld, mx) / mx * 100
        lab = ("사건 없음" if ld is None else (f"{ld}일" if ld <= mx else f"{ld}일 (축 B 장기 축적)"))
        mt = (f"구조 일치 {m['match']}/4" + ((" · " + ", ".join(FIELD[k][0] for k in m["matched"])) if m["matched"] else "")) if m["match"] else "불일치 상태의 참고 반례"
        rows.append(f"<div style='margin:6px 0'><div style='display:flex;justify-content:space-between;font-size:13px'><span><b>{html.escape(c['name'])}</b>"
                    f" <span class='muted'>{mt}</span></span>"
                    f"<span style='color:{col};font-weight:700'>{lab}</span></div>"
                    f"<div style='height:8px;background:#f0efe9;border-radius:4px;margin-top:3px'><div style='width:{w:.0f}%;height:8px;border-radius:4px;background:{col}'></div></div>"
                    f"<div class='muted' style='font-size:12px;margin-top:2px'>{html.escape(c['signal'][:70])}… → {html.escape(c['action'][:40])}"
                    f"{(' · ' + html.escape(c['note'])) if c.get('note') else ''}</div></div>")
    return ("<div style='font-size:12px;color:#6b6b66'>유사 과거 사례 — 신호에서 행동까지 선행 일수 (공개 보도 기준 · 라이브러리 7건 · 규칙 기반 유사도)</div>"
            + "".join(rows) + "<div class='muted' style='font-size:12px'>보라 = 선행 사례 · 자주색 = 반례(기만·동시) · 회색 = 사건 없는 급등. 정확도 주장이 아니라 참고용.</div>")


def items_table_html(PRE, h):
    bi = [x for x in PRE["items"] if x["h"] <= h]
    if not bi:
        return "<div class='muted'>아직 관측된 외국어 서사 항목이 없습니다.</div>"
    rows = "".join(f"<tr><td>{x['ts']}</td><td><code>{x['lang']}</code></td><td>{html.escape(x['outlet'])}</td><td style='color:{AX['B']};font-weight:700'>{x['kind_label']}</td><td>{html.escape(x['text_ko'])}</td></tr>" for x in bi)
    return f"<table style='font-size:12px;width:100%;border-collapse:collapse'><tr><th>시각</th><th>언어</th><th>매체(가상)</th><th>분류(규칙)</th><th>번역</th></tr>{rows}</table>"


def library_table_html(cases):
    rows = "".join(f"<tr><td>{c['id']}</td><td>{html.escape(c['name'])}</td><td>{c['signal_date']}</td><td>{c['action_date'] or '—'}</td>"
                   f"<td>{'—' if c['lead_days'] is None else c['lead_days']}</td><td>{html.escape(c['signal'])}</td><td>{html.escape(c['action'])}</td>"
                   f"<td style='font-size:11px'>{'<br>'.join(html.escape(u) for u in c['sources'])}</td></tr>" for c in cases)
    return f"<table style='font-size:12px;width:100%;border-collapse:collapse'><tr><th>ID</th><th>사례</th><th>신호일</th><th>행동일</th><th>선행(일)</th><th>신호</th><th>행동</th><th>출처</th></tr>{rows}</table>"


# ---------------------------------------------------------------- 역사 재생 (실제 공개 담화 백테스트) — out/precursor_replay.json
LV_C = {0: "#d9d8d2", 1: "#b5b4ad", 2: "#e0a000", 3: "#d03b3b"}
VERDICT_C = {"hit": "#1baf7a", "miss": "#8a8a85", "false_alarm": "#d03b3b", "ok": "#1baf7a", "n/a": "#b5b4ad"}


def load_replay():
    rp = os.path.join(HERE, "out", "precursor_replay.json")
    return json.load(open(rp, encoding="utf-8")) if os.path.exists(rp) else None


def replay_fig(RP, tag="v2"):
    """사례별 한 줄: x = 행동일 기준 상대 일수(행동 없으면 첫 발언 기준), 마름모 = 발언(색 = 규칙 수준), 검은 세로선 = 행동, 회색 띠 = 14일 창(행동 없음)"""
    cases = [c for c in RP["cases"] if c["verdict"][tag]["result"] != "n/a"]
    fig = go.Figure()
    shapes, ann = [], []
    for i, c in enumerate(cases):
        y = len(cases) - 1 - i
        if c["kind"] == "precedent" and c["action_date"]:
            shapes.append(dict(type="line", x0=0, x1=0, y0=y - .42, y1=y + .42, line=dict(color="#1f1f1d", width=3)))
        else:
            shapes.append(dict(type="rect", x0=0, x1=c["window_days"], y0=y - .3, y1=y + .3, fillcolor="#9a9a94", opacity=.12, line=dict(width=0)))
            ann.append(dict(x=c["window_days"] / 2, y=y + .33, text=f"{c['window_days']}일 창 — 연결된 행동 없음", showarrow=False, font=dict(size=10, color="#6b6b66")))
            if c.get("action_rel_days") is not None:
                shapes.append(dict(type="line", x0=c["action_rel_days"], x1=c["action_rel_days"], y0=y - .3, y1=y + .3, line=dict(color="#9a9a94", width=2, dash="dot")))
                ann.append(dict(x=c["action_rel_days"], y=y - .42, text="통상 활동(연결 안 됨)", showarrow=False, font=dict(size=9, color="#8a8a85")))
        for s in c["statements"]:
            if s["excluded"]:
                continue
            lv = s[tag]["level"]
            fig.add_scatter(x=[s["rel_days"]], y=[y], mode="markers+text", showlegend=False,
                            marker=dict(symbol="diamond", size=12 + 5 * lv, color=LV_C[lv], line=dict(color="#fff", width=1)),
                            text=[f"L{lv}"], textposition="top center", textfont=dict(size=10, color=LV_C[lv] if lv >= 2 else "#6b6b66"),
                            hovertemplate=(f"{s['date']} · {html.escape(s['speaker_role'])}<br>{tag} L{lv} ({s[tag]['level_why']})<br>"
                                           + html.escape(s["text_ko"][:90]) + "…<extra></extra>"))
    fig.update_layout(height=60 + 46 * len(cases), margin=dict(l=10, r=10, t=36, b=36), plot_bgcolor="white", shapes=shapes, annotations=ann,
                      title=dict(text=f"실제 공개 담화 재생 — 규칙 {tag} · 마름모 = 발언(색 = 수준) · 검은 선 = 실제 행동일 · 회색 띠 = 행동 없음", font=dict(size=13)),
                      xaxis=dict(title="상대 일수 (선행 사례: 행동일 = 0 · 행동 없는 사례: 첫 발언 = 0)", range=[-9, 15.5], zeroline=False, gridcolor="#f0efe9", dtick=2),
                      yaxis=dict(automargin=True, tickvals=list(range(len(cases))),
                                 ticktext=[f"{c['case_id'][:2]} {c['name'].split('(')[0][:22]}…" for c in reversed(cases)],
                                 tickfont=dict(size=11), range=[-.6, len(cases) - .4]))
    return fig


def replay_summary_text(RP):
    s1, s2 = RP["summary"]["v1"], RP["summary"]["v2"]
    return (f"실제 공개 담화 재생 (추출 가능 {s2['n_precedent'] + s2['n_false_alarm_cases']}건) — "
            f"<b>v2 규칙</b>: 행동으로 이어진 {s2['n_precedent']}건 중 L3 선행 <b>{s2['n_hit']}건</b>"
            f"({' · '.join(str(x) + '일' for x in s2['leads'])}), 행동 없던 {s2['n_false_alarm_cases']}건 중 L3 <b>{s2['n_false_alarm_l3']}건</b> "
            f"→ 공식 축 단독이면 오경보 {s2['n_false_alarm_l3']}/{s2['n_false_alarm_cases']} — 축 C(은밀 증폭)와의 정합성이 필요한 이유. "
            f"<b>v1 규칙</b>(합성 문장만 보고 만든 것): 선행 {s1['n_hit']}/{s1['n_precedent']} · 오경보 {s1['n_false_alarm_l3']}/{s1['n_false_alarm_cases']} — 합성 데이터 과적합 그대로.")


def replay_table_html(RP):
    rows = []
    for c in RP["cases"]:
        v1, v2 = c["verdict"]["v1"], c["verdict"]["v2"]
        for k, s in enumerate(c["statements"]):
            lvtxt = "요약문 — 추출 제외" if s["excluded"] else f"v1 L{s['v1']['level']} → <b style='color:{LV_C[s['v2']['level']]}'>v2 L{s['v2']['level']}</b>"
            flds = "" if s["excluded"] else " · ".join(f"<span style='color:{FIELD[kk][1]}'>{FIELD[kk][0]}</span>" for kk in s["v2"]["fields"] if kk in FIELD)
            first = k == 0
            rows.append(
                "<tr>" + (f"<td rowspan='{len(c['statements'])}' style='vertical-align:top'><b>{c['case_id'][:2]}</b> {html.escape(c['name'])}<br>"
                          f"<span style='color:#6b6b66'>{c['kind_ko']}{' · 규칙 설계에 사용' if c['in_sample_v2'] else ''}</span><br>"
                          f"<span style='color:{VERDICT_C[v2['result']]};font-weight:700'>{html.escape(v2['label'])}</span></td>" if first else "")
                + f"<td style='white-space:nowrap'>{s['date']}</td><td>{html.escape(s['speaker_role'])}</td>"
                f"<td style='max-width:420px'>{html.escape(s['text_ko'][:140])}{'…' if len(s['text_ko']) > 140 else ''}</td>"
                f"<td style='white-space:nowrap'>{lvtxt}</td><td>{flds}</td>"
                + (f"<td rowspan='{len(c['statements'])}' style='vertical-align:top;white-space:nowrap'>{c['action_date'] or '—'}</td>" if first else "") + "</tr>")
    return ("<table style='font-size:12px;border-collapse:collapse;width:100%'><tr><th>사례</th><th>발언일</th><th>발화 기관</th><th>인용(보도된 그대로, 발췌)</th>"
            "<th>규칙 수준</th><th>v2 추출 필드</th><th>행동일</th></tr>" + "".join(rows) + "</table>")
