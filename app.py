"""
app.py — M5 대시보드
실행 : streamlit run app.py
입력 : data/posts.csv(truth_* 읽지 않음), out/* (M2~M4, M6 결과)
화면 : 시간 슬라이더를 움직이면 '그 시각에 분석관이 볼 수 있었던 것'만 보여준다.
"""
import json, os, time
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import alerts as AL

HERE = os.path.dirname(os.path.abspath(__file__))
DATA, OUT = os.path.join(HERE, "data"), os.path.join(HERE, "out")

# 색: 범주 1~3슬롯(일반 사용자/의심 집단/외국어 출처), 단계는 상태 색 + 아이콘 + 글자
C_ORD, C_SUS, C_SRC = "#2a78d6", "#eb6834", "#1baf7a"
LV_STYLE = {"NONE": ("·", "#8a8a85", "경보 없음"), "REVIEW": ("◇", "#8a8a85", "검토 권장"),
            "WATCH": ("●", "#fab219", "관찰"), "ALERT": ("▲", "#ec835a", "경보"),
            "CRITICAL": ("■", "#d03b3b", "위험")}

st.set_page_config(page_title="FIMI 서사 조기경보", layout="wide")


def out_stamp():
    """결과 파일이 바뀌면 캐시를 새로 읽도록 out/ 파일 수정 시각을 키로 쓴다"""
    return tuple(sorted((f, os.path.getmtime(os.path.join(OUT, f))) for f in os.listdir(OUT) if f.endswith((".csv", ".json"))))


@st.cache_data
def load_all(stamp_key=None):
    P, S, B, M, SRC = AL.load()
    R = pd.read_csv(os.path.join(OUT, "r_series.csv"), parse_dates=["ts"])
    with open(os.path.join(OUT, "alerts.json"), encoding="utf-8") as f:
        cards = json.load(f)
    return P, S, B, M, SRC, R, cards


P, S, B, M, SRC, R, cards = load_all(out_stamp())


@st.cache_data
def load_policy(stamp_key=None):
    p = os.path.join(OUT, "policy.csv")
    return pd.read_csv(p, keep_default_na=False) if os.path.exists(p) else None


POL = load_policy(out_stamp())
ACT_STYLE = {0: ("○", "#8a8a85"), 1: ("●", "#2a78d6"), 2: ("◆", "#e0a000"), 3: ("▲", "#ec835a"), 4: ("■", "#d03b3b")}


@st.cache_data
def load_precursor(stamp_key=None):
    import precursor_ui as PU
    return PU.load()


PRE = load_precursor(out_stamp())      # 전조 카드(축 A·B·정합성) — out/precursor.json, 없으면 섹션 생략
import redteam_ui as RT                 # 회피 내성(레드팀) — out/redteam.json, real/urlnet_ira_results.json


@st.cache_data
def load_redteam(stamp_key=None):
    return RT.load()


RED, IRA_URL = load_redteam(out_stamp())
URLNET = (json.load(open(os.path.join(OUT, "urlnet_summary.json"), encoding="utf-8"))
          if os.path.exists(os.path.join(OUT, "urlnet_summary.json")) else None)
t0 = P.ts.min().floor("D")
max_h = int(R.hour.max())

# ---------------------------------------------------------------- 사이드바
st.sidebar.title("FIMI 서사 조기경보")
st.sidebar.caption("합성 데이터 시연 · 모든 계정·매체는 가상 · 계정은 가명 ID")
# 재생 컨트롤: 72시간 가상 시나리오를 다음 발표 지점까지 브라우저 안에서 부드럽게 재생 (현실 시간과 무관)
STOPS = (13, 41, 47, 56, 72)  # 관찰 · 경보 · 불일치(전조 카드) · 위험 · 끝
ss = st.session_state
if "hour" not in ss:
    ss.hour = int(os.environ.get("FIMI_HOUR", 13))


def _play_all():
    ss.anim_from = 0
    ss.hour = max_h


def _play():
    ss.anim_from = ss.hour
    ss.hour = next((x for x in STOPS if x > ss.hour), ss.hour)


def _reset():
    ss.hour = 13


nxt_stop = next((x for x in STOPS if x > ss.hour), None)
st.sidebar.button(f"▶ 처음부터 끝까지 재생 (0→{max_h}시)", on_click=_play_all, type="primary")
st.sidebar.button(f"⏭ {nxt_stop}시까지만 재생" if nxt_stop else "⏭ 끝까지 재생함", on_click=_play,
                  disabled=nxt_stop is None)
st.sidebar.button("⏮ 13시로 되돌리기", on_click=_reset)
speed = st.sidebar.select_slider("재생 속도", options=["느리게", "보통", "빠르게"], value="보통")
hour = st.sidebar.slider("관측 시각 (시작 후 시간)", 1, max_h, step=1, key="hour")
anim_from = ss.pop("anim_from", None)
t_now = t0 + pd.Timedelta(hours=hour)
st.sidebar.markdown(f"**현재 시각** `{t_now:%m-%d %H:%M}`")

now_lv = R[R.hour == hour].set_index("narrative_id").level.to_dict()
card_by = {c["narrative_id"]: c for c in cards}
order = sorted(now_lv, key=lambda n: -AL.LEVELS.index(now_lv[n]))
cand = [n for n in order if n in card_by] or order[:1]


def lv_badge(lv):
    ic, col, name = LV_STYLE[lv]
    return f"<span style='color:{col};font-weight:700'>{ic} {lv}</span> <span style='color:#6b6b66'>{name}</span>"


st.sidebar.markdown("**서사별 현재 단계**")
for n in cand:
    samp = card_by[n]["narrative_samples"][0][:26] if n in card_by else ""
    st.sidebar.markdown(f"N{n} {lv_badge(now_lv.get(n, 'NONE'))}<br><small>{samp}…</small>",
                        unsafe_allow_html=True)
nid = st.sidebar.selectbox("서사 선택", cand, format_func=lambda n: f"N{n}")
mode = st.sidebar.radio("판단 기준", ["행동 (우리 방식)", "내용 (비교용)"],
                        help="내용 기준 = 이 서사를 말한 계정을 모두 의심. 행동 기준 = 반복 동시 게시한 계정만 의심")
content_mode = mode.startswith("내용")
role = st.sidebar.radio("화면", ["분석관", "지휘관"], horizontal=True,
                        help="지휘관 화면 = 같은 데이터를 숫자 3개 + 권고 1줄 + 하지 말 것으로 줄인 1화면. 새 판단을 더하지 않는다")

card = card_by.get(nid)
g_all = P[(P.narrative_id == nid)]
g = g_all[g_all.ts < t_now]
r_now = R[(R.narrative_id == nid) & (R.hour == hour)].iloc[0]
import analyst as ANL                   # 분석관 판정 루프 · 브리핑 초안 · 지휘관 요약 (2026-10-18)
if "judgments" not in ss:
    ss.judgments = {}                        # (narrative_id, burst_id) → dict(judgment, reason, record)
if "jrecords" not in ss:
    ss.jrecords = []                         # 판정 기록 체인 (증거 체인 끝 해시에 이어 붙임)
excluded = {b for (n, b), j in ss.judgments.items() if n == nid and j["judgment"] == "normal"}
joined = ANL.joined_times(S, M, nid, excluded) if excluded else AL.suspect_asof(S, M, nid)
is_sus_beh = lambda a: (a in joined) and joined[a] <= t_now
said = set(g[g.lang == "ko"].account_id)          # 지금까지 이 서사를 말한 계정
is_sus = (lambda a: a in said) if content_mode else is_sus_beh

# ---------------------------------------------------------------- 재생 패널 (▶ 버튼을 눌렀을 때만)
if anim_from is not None and anim_from < hour:
    import anim as AN
    st.caption(f"▶ 재생 {anim_from}시 → {hour}시 · 72시간 가상 시나리오를 15분 단위로 재생 · 아래 화면은 {hour}시 기준")
    polh = {} if POL is None else POL[POL.narrative_id == nid].set_index("hour").action_label.to_dict()
    fo_urls = {f["url"]: f["post_id"] for f in SRC.get(str(nid), {}).get("foreign", []) if f.get("url")}
    st.iframe(AN.build(g_all[["post_id", "parent_id", "ts", "account_id", "lang", "url"]], t0,
                       R[R.narrative_id == nid].sort_values("hour"), polh, joined, content_mode, anim_from, hour,
                       max_h, (C_ORD, C_SUS, C_SRC), LV_STYLE, fo_urls, AL.R_ALERT, AL.R_CRIT,
                       {"느리게": 90, "보통": 45, "빠르게": 20}[speed]), height=870)

# ---------------------------------------------------------------- 상단 지표
lv = r_now.level
st.markdown(f"### N{nid} · {lv_badge(lv)}", unsafe_allow_html=True)
if card:
    st.caption("서사 예시: " + " / ".join(card["narrative_samples"][:2]))
src = SRC.get(str(nid), {})
fo_seen = [f for f in src.get("foreign", []) if pd.Timestamp(f["ts"]) < t_now]
# ---------------------------------------------------------------- 브리핑·지휘관 요약 재료 (근거 카드와 같은 숫자)
_prow = None
if POL is not None:
    _p = POL[(POL.narrative_id == nid) & (POL.hour == hour)]
    _prow = _p.iloc[0] if len(_p) else None
_bb = B[(B.narrative_id == nid) & (B.end < t_now)]
_first_ko = g[g.lang == "ko"].ts.min() if len(g) else pd.NaT
_cur = S[(S.narrative_id == nid) & (S.account_id.map(is_sus_beh))]
_coord = float(_cur.score.mean()) if len(_cur) else 0.0
_rv = 0.0 if pd.isna(r_now.r_pool) else min(float(r_now.r_pool), 1.0)
_conf_v = 0.4 * _coord + 0.3 * float(bool(fo_seen)) + 0.3 * _rv
_conf = ("높음" if _conf_v >= 0.7 else ("중간" if _conf_v >= 0.45 else "낮음")) + f" ({_conf_v:.2f})"
_reas = ANL.reassess(S, M, nid, t_now, excluded, bool(fo_seen), lv)
_pre_ctx = None
if PRE and nid == PRE["summary"]["campaign_narrative"]:
    import precursor_ui as _PU
    _pr_ = _PU.row_at(PRE, hour)
    _bs = _PU.base_statement(PRE, hour)
    _pre_ctx = dict(state_label=_pr_["state_label"], conv=_pr_["conv"],
                    note={"mismatch": "공식 발언 완화 + 은밀 증폭 상승 — 완화 발언을 근거로 경계를 낮추지 않는다",
                          "converged": "공개 발언의 예고 시간창과 은밀 증폭이 겹치는 구간"}.get(_pr_["state"], ""),
                    a_text=(f"{_bs['stmt_id']} {_bs['ts']} · 수준 L{_bs['level']} ({_bs['level_why']})" if _bs else None),
                    window=(__import__("re").sub(r"<[^>]+>", "", _PU.window_text(PRE, _pr_, t0).replace("<br>", " ")) if _bs else None))
_dn = [x for x in str(_prow.do_not).split(" | ") if x] if _prow is not None else []
_sm = {k: float(_cur[k].mean()) if len(_cur) else 0.0 for k in ["young", "url_share"]}
_cands = AL.disarm_candidates(len(_bb), float(_bb.mean_text_sim.max()) if len(_bb) else 0.0,
                              _sm["url_share"], _sm["young"], bool(fo_seen)) if lv != "NONE" else []
CTX = dict(nid=nid, now=f"{t_now:%m-%d %H:%M}", hour=hour, level=lv, level_name=LV_STYLE[lv][2],
           policy=(dict(action_label=_prow.action_label, stage_label=_prow.stage_label, attribution=_prow.attribution,
                        why_now=_prow.why_now, why_level=_prow.why_level, escalate_if=_prow.escalate_if) if _prow is not None else None),
           foreign=[dict(lang=f["lang"], ts=f["ts"][:16], url=f["url"],
                         lead_h=((_first_ko - pd.Timestamp(f["ts"])) / pd.Timedelta(hours=1) if pd.notna(_first_ko) else None))
                    for f in fo_seen],
           bursts=[dict(id=int(r.burst_id), start=f"{r.start:%m-%d %H:%M}", end=f"{r.end:%H:%M}", n=int(r.n_accounts),
                        sim=float(r.mean_text_sim), url=r.top_url or "",
                        judgment=ss.judgments.get((nid, int(r.burst_id)), {}).get("judgment"))
                   for r in _bb.itertuples()],
           reassess=_reas,
           r=(None if pd.isna(r_now.r_pool) else dict(r=float(r_now.r_pool), lo=float(r_now.r_lo), hi=float(r_now.r_hi),
                                                        p1=float(r_now.p_gt1), p08=float(r_now.p_gt08))),
           disarm=_cands, pre=_pre_ctx, do_not=_dn, confidence=_conf,
           judgments=[j["record"] for (n, b), j in ss.judgments.items() if n == nid],
           chain_end=ANL.chain_end())

if role == "지휘관":
    cs = ANL.commander_summary(CTX)
    with st.container(border=True):
        st.markdown(f"<div style='font-size:13px;color:#6b6b66'>지휘관 요약 — 같은 데이터를 줄인 1화면 · 판정 아님 · 최종 결정은 사람</div>"
                    f"<div style='font-size:24px;font-weight:700;margin:2px 0 8px'>{cs['headline']}</div>", unsafe_allow_html=True)
        k1, k2, k3, k4 = st.columns(4)
        for col_, (kk, vv, dd) in zip((k1, k2, k3), cs["numbers"]):
            col_.metric(kk, vv, delta=dd, delta_color="off")
        k4.metric("전조 정합성", cs["precursor"][0], delta=cs["precursor"][1], delta_color="off")
        ca, cb = st.columns([3, 2])
        with ca:
            if cs["do_not"]:
                st.markdown("**하지 말 것**\n" + "\n".join(f"- {x}" for x in cs["do_not"]))
            st.markdown(f"**다음 재평가** {cs['next_eval']}  \n**카드 신뢰도** {cs['confidence']} · **분석관 판정** {cs['judgments']}건")
        with cb:
            st.markdown("**운용 위치와 경계**")
            for kk, vv in cs["conops"].items():
                st.markdown(f"- **{kk}** {vv}")
    with st.expander("브리핑 초안 (규칙 기반 템플릿 · LLM 미사용 · 분석관 검토 전)", expanded=False):
        _md = ANL.briefing_md(CTX)
        st.download_button("브리핑 초안 내려받기 (.md)", _md, file_name=f"briefing_N{nid}_{hour:02d}h.md", mime="text/markdown")
        st.markdown(_md)
    st.caption("상세 근거·차트는 사이드바에서 '분석관' 화면으로 전환하면 보입니다.")
    st.stop()

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("일반 사용자 간 R̂", "—" if pd.isna(r_now.r_pool) else f"{r_now.r_pool:.2f}",
          delta=None if pd.isna(r_now.p_gt1) else f"P(R>1) {r_now.p_gt1:.0%}", delta_color="off",
          help="최근 3시간 동안 일반 사용자 게시물 1건이 이후 몇 건의 일반 사용자 게시를 낳았나. 1 이상이면 자생 확산. P(R>1)은 사후확률")
c2.metric("의심 계정 (" + ("내용 기준" if content_mode else "행동 기준") + ")", sum(1 for a in said if is_sus(a)))
c3.metric("이 서사 게시물(지금까지)", int(r_now.n_posts_sofar))
src = SRC.get(str(nid), {})
fo_seen = [f for f in src.get("foreign", []) if pd.Timestamp(f["ts"]) < t_now]
c4.metric("외국어 출처 연결", f"{len(fo_seen)}건" if fo_seen else "없음",
          help="다국어 임베딩으로 같은 서사에 묶인 외국어 게시물")
if PRE and nid == PRE["summary"]["campaign_narrative"]:
    import precursor_ui as PU
    _pr = PU.row_at(PRE, hour)
    c5.metric("전조 정합성", f"{PU.STATE[_pr['state']][0]} {_pr['state_label']}", delta=f"수렴 {_pr['conv']}/3축", delta_color="off",
              help="공식 신호(A)·명분 서사(B)·은밀 증폭(C) 중 기준을 넘은 축의 수. 불일치 = 공식 발언 완화 + 은밀 증폭 상승. 아래 '전조 카드' 참조")
else:
    c5.metric("전조 정합성", "—", help="전조 카드는 외국어 출처가 연결된 공작 서사에만 만듭니다")
n_beh = sum(1 for a in said if is_sus_beh(a))
if len(said):
    (st.warning if content_mode else st.info)(
        f"**내용 기준**이면 이 서사를 말한 계정 **{len(said):,}개** 전부가 의심 대상 → "
        f"**행동 기준**이면 **{n_beh}개**. 같은 주장을 하는 일반 시민을 공작으로 몰지 않기 위해 우리는 행동을 봅니다.")

# ---------------------------------------------------------------- 차트 1, 2: 볼륨과 R̂ (축을 공유하지 않는 두 차트)
gk = g_all[g_all.lang == "ko"].copy()
gk["hour"] = ((gk.ts - t0) / pd.Timedelta(hours=1)).astype(int)
gk["grp"] = ["의심 집단" if is_sus(a) else "일반 사용자" for a in gk.account_id]  # 현재 시각에 아는 분류로 소급 표시
vol = gk[gk.hour < hour].groupby(["hour", "grp"]).size().unstack(fill_value=0) \
    .reindex(range(0, max_h + 1), fill_value=0)
for col in ["일반 사용자", "의심 집단"]:
    if col not in vol: vol[col] = 0

left, right = st.columns(2)
with left:
    f1 = go.Figure()
    f1.add_bar(x=vol.index, y=vol["일반 사용자"], name="일반 사용자", marker_color=C_ORD,
               hovertemplate="%{x}시 · 일반 사용자 %{y}건<extra></extra>")
    f1.add_bar(x=vol.index, y=vol["의심 집단"], name="의심 집단", marker_color=C_SUS,
               hovertemplate="%{x}시 · 의심 집단 %{y}건<extra></extra>")
    for b in B[(B.narrative_id == nid) & (B.end < t_now)].itertuples():
        f1.add_vrect(x0=(b.start - t0) / pd.Timedelta(hours=1) - 0.4,
                     x1=(b.end - t0) / pd.Timedelta(hours=1) + 0.4,
                     fillcolor="#8a8a85", opacity=0.12, line_width=0)
    f1.add_vline(x=hour, line_dash="dot", line_color="#6b6b66")
    vol_h = AL.volume_alarm_hour(gk.groupby("hour").size().reindex(range(0, max_h + 1), fill_value=0).values)
    if vol_h is not None and vol_h <= hour:
        f1.add_vline(x=vol_h, line_color="#8a8a85", line_width=1.5,
                     annotation_text="단순 볼륨 경보", annotation_position="top right")
    f1.update_layout(barmode="stack", bargap=0.15, height=300, title="시간당 게시물 (회색 띠 = 동시 게시 burst)",
                     margin=dict(l=10, r=10, t=60, b=10), legend=dict(orientation="h", y=1.12, x=0),
                     xaxis=dict(range=[0, max_h], title="시작 후 시간"), yaxis=dict(gridcolor="#eee"),
                     plot_bgcolor="white")
    st.plotly_chart(f1, width="stretch")
with right:
    rs = R[(R.narrative_id == nid) & (R.hour <= hour)]
    f2 = go.Figure()
    f2.add_hrect(y0=AL.R_ALERT, y1=AL.R_CRIT, fillcolor="#ec835a", opacity=0.10, line_width=0)
    f2.add_hline(y=1.0, line_color="#d03b3b", line_width=1,
                 annotation_text="R=1 자생 확산", annotation_position="top left")
    f2.add_scatter(x=list(rs.hour) + list(rs.hour[::-1]), y=list(rs.r_hi) + list(rs.r_lo[::-1]),
                   fill="toself", fillcolor="rgba(42,120,214,0.15)", line=dict(width=0),
                   hoverinfo="skip", name="80% 구간")
    f2.add_scatter(x=rs.hour, y=rs.r_pool, mode="lines+markers", line=dict(color=C_ORD, width=2),
                   marker=dict(size=6), name="R̂", connectgaps=False,
                   customdata=np.stack([rs.r_lo, rs.r_hi, rs.p_gt1], axis=-1),
                   hovertemplate="%{x}시 · R̂ %{y:.2f} (80% %{customdata[0]:.2f}~%{customdata[1]:.2f}) · P(R>1) %{customdata[2]:.0%}<extra></extra>")
    f2.add_vline(x=hour, line_dash="dot", line_color="#6b6b66")
    f2.update_layout(height=280, title="일반 사용자 간 R̂ · 파란 띠 = 80% 구간",
                     margin=dict(l=10, r=10, t=40, b=10), showlegend=False,
                     xaxis=dict(range=[0, max_h], title="시작 후 시간"),
                     yaxis=dict(range=[0, max(1.6, float(np.nanmax(rs.r_hi)) + 0.1) if rs.r_hi.notna().any() else 1.6],
                                gridcolor="#eee"), plot_bgcolor="white")
    st.plotly_chart(f2, width="stretch")

# ---------------------------------------------------------------- 차트 3: 확산 경로 (출처 → 의심 집단 → 일반 사용자)
with st.expander("단순 볼륨 감시와 비교 — 서사별 (지금 시각 기준)"):
    rows = []
    for n in sorted(P.narrative_id.unique()):
        if n < 0: continue
        kk = P[(P.narrative_id == n) & (P.lang == "ko")]
        hc = kk.assign(h=((kk.ts - t0) / pd.Timedelta(hours=1)).astype(int)).groupby("h").size() \
            .reindex(range(0, max_h + 1), fill_value=0).values
        vh = AL.volume_alarm_hour(hc)
        ours = now_lv.get(n, "NONE")
        if vh is None and ours == "NONE": continue
        rows.append({"서사": f"N{n}", "예시": (card_by[n]["narrative_samples"][0][:28] + "…") if n in card_by
                     else kk.text.iloc[0][:28] + "…",
                     "볼륨 감시": (f"{vh}시 경보" if vh <= hour else "아직") if vh is not None else "경보 없음",
                     "우리 단계": f"{LV_STYLE[ours][0]} {ours}"})
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    st.caption("단순 볼륨 감시 = 시간당 게시물 20건 이상이면서 직전 24시간 중앙값의 3배 이상. "
               "볼륨 감시는 빨리 울리지만 자연 바이럴에도 울린다. 우리의 장점은 속도가 아니라 구분력이다.")

st.markdown("#### 확산 그래프 재생 — 계정 네트워크")
st.caption("점 = 계정(일반 사용자는 이름표 없음, 가명 ID는 외국어 출처·의심 확정 계정만) · 회색 선 = 리포스트·답글 · "
           "초록 선 = 외국어 출처 URL 공유 · 주황 선 = 반복 동시 게시로 묶인 의심 계정 · 그래프 안 ▶ 로 지금 시각부터 재생")


@st.cache_data(show_spinner=False)
def graph_html(nid_, start_, stamp_key=None):
    import obsgraph as OG
    return OG.build_html(int(nid_), float(start_), autoplay=False, P=P, S=S, M=M, SRC=SRC, R=R, POL=POL)


st.iframe(graph_html(nid, hour, out_stamp()), height=760)

st.markdown("#### 확산 경로 (시간축) — 외국어 출처에서 일반 사용자까지")
gg = g.sort_values("ts").copy()
pos = {}
depth = {}
for r in gg.itertuples():
    if r.lang != "ko":
        depth[r.post_id] = 0
    else:
        depth[r.post_id] = depth.get(r.parent_id, 0) + 1 if r.parent_id else 1
rng = np.random.default_rng(0)
gg["x"] = (gg.ts - t0) / pd.Timedelta(hours=1)
gg["d"] = gg.post_id.map(depth)
gg["y"] = gg.d + rng.uniform(-0.25, 0.25, len(gg))
# 일반 사용자는 개별 점이 아니라 (1시간, 단계) 단위 집계 노드로만 표시한다 — 시민 개인을 추적하지 않기 위해
ordm = (gg.lang == "ko") & ~gg.account_id.map(is_sus_beh).astype(bool)
gg.loc[ordm, "x"] = np.floor(gg.loc[ordm, "x"]) + 0.5
gg.loc[ordm, "y"] = gg.loc[ordm, "d"].astype(float)
gg["grp"] = np.where(gg.lang != "ko", "외국어 출처",
                     np.where([is_sus(a) for a in gg.account_id], "의심 집단", "일반 사용자"))
xy = gg.set_index("post_id")[["x", "y"]].to_dict("index")
ex, ey = [], []
for r in gg.itertuples():
    p = xy.get(r.parent_id)
    if p:
        ex += [p["x"], r.x, None]; ey += [p["y"], r.y, None]
# 부모가 없어도 같은 URL을 공유하면 출처와 점선으로 잇는다
src_url = {f["url"]: f["post_id"] for f in fo_seen if f.get("url")}
ux, uy = [], []
for r in gg[(gg.lang == "ko") & (gg.url.isin(src_url))].itertuples():
    p = xy.get(src_url[r.url])
    if p and not r.parent_id:
        ux += [p["x"], r.x, None]; uy += [p["y"], r.y, None]
f3 = go.Figure()
f3.add_scatter(x=ux, y=uy, mode="lines", line=dict(color=C_SRC, width=1, dash="dot"),
               opacity=0.5, hoverinfo="skip", name="동일 URL 공유")
f3.add_scatter(x=ex, y=ey, mode="lines", line=dict(color="#b5b4ad", width=1),
               opacity=0.6, hoverinfo="skip", name="리포스트·답글 관계")
for name, col in [("일반 사용자", C_ORD), ("의심 집단", C_SUS), ("외국어 출처", C_SRC)]:
    d = gg[gg.grp == name]
    if not len(d): continue
    beh = d.account_id.map(is_sus_beh).astype(bool) | (d.lang != "ko")
    di, da = d[beh], d[~beh]
    if len(di):   # 행동 기준 의심 계정과 외국어 출처만 개별 표시 (가명 ID)
        f3.add_scatter(x=di.x, y=di.y, mode="markers", name=name,
                       marker=dict(color=col, size=11 if name == "외국어 출처" else 8, line=dict(color="white", width=1)),
                       customdata=np.stack([di.account_id, di.lang, di.text.str[:40]], axis=-1),
                       hovertemplate="%{customdata[0]} · %{customdata[1]}<br>%{customdata[2]}<extra>" + name + "</extra>")
    if len(da):   # 일반 사용자: 집계 노드 (크기 = 게시물 수, 계정 정보 없음)
        agg = da.groupby(["x", "y"]).size().reset_index(name="n")
        f3.add_scatter(x=agg.x, y=agg.y, mode="markers", name=name + " (집계)",
                       marker=dict(color=col, size=6 + 3 * np.sqrt(agg.n), opacity=0.75, line=dict(color="white", width=1)),
                       customdata=agg.n, hovertemplate="일반 사용자 %{customdata}건 (집계 · 개별 계정 표시 안 함)<extra></extra>")
f3.update_layout(height=360, margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="white",
                 legend=dict(orientation="h", y=-0.15),
                 xaxis=dict(range=[0, max_h], title="시작 후 시간"),
                 yaxis=dict(title="출처로부터 단계(0=외국어 원문)", gridcolor="#eee", dtick=1))
st.plotly_chart(f3, width="stretch")
st.caption("일반 사용자는 개별 계정이 아니라 시간·단계별 집계 노드로만 표시합니다. 개별 가명 ID는 행동 기준 의심 계정에만 보입니다.")

# ---------------------------------------------------------------- 근거 카드
st.markdown("#### 근거 카드")
prow = None
if POL is not None:
    _p = POL[(POL.narrative_id == nid) & (POL.hour == hour)]
    prow = _p.iloc[0] if len(_p) else None
if prow is not None and (int(prow.action) > 0 or lv != "NONE"):
    ic, col = ACT_STYLE.get(int(prow.action), ("·", "#8a8a85"))
    with st.container(border=True):
        st.markdown(f"<div style='font-size:13px;color:#6b6b66'>대응 단계 권고 (분석관 보조 · 최종 결정은 사람)</div>"
                    f"<div style='font-size:22px;font-weight:700;color:{col}'>{ic} {prow.action_label}"
                    + ("<span style='font-size:13px;color:#6b6b66;font-weight:400'> · 이전 단계 유지(해제는 분석관)</span>" if str(prow.sticky) == "True" else "")
                    + "</div>", unsafe_allow_html=True)
        pa, pb = st.columns([3, 2])
        with pa:
            st.markdown(f"**확산 단계** {prow.stage_label}  \n**출처 귀속** {prow.attribution}  \n"
                        f"**왜 지금** {prow.why_now}  \n**왜 이 수준** {prow.why_level}")
        with pb:
            dn = [x for x in str(prow.do_not).split(" | ") if x]
            if dn:
                st.markdown("**하지 말 것**\n" + "\n".join(f"- {x}" for x in dn))
            st.markdown(f"**다음 재평가** {prow.escalate_if}")
        nts = [x for x in str(prow.notes).split(" | ") if x]
        if nts:
            st.caption(" · ".join(nts))
        st.caption(f"신뢰도 {float(prow.confidence):.2f} · 판정이 아니라 분석관 보조")
if lv == "NONE" or not card:
    st.info("이 시각에는 경보가 없습니다. 반복 조정 집단이 확인되면 카드가 생성됩니다.")
else:
    cur = S[(S.narrative_id == nid) & (S.account_id.map(is_sus_beh))]
    coord = float(cur.score.mean()) if len(cur) else 0.0
    rv = 0.0 if pd.isna(r_now.r_pool) else min(float(r_now.r_pool), 1.0)
    conf_v = 0.4 * coord + 0.3 * float(bool(fo_seen)) + 0.3 * rv
    conf = "높음" if conf_v >= 0.7 else ("중간" if conf_v >= 0.45 else "낮음")
    sm = {k: float(cur[k].mean()) if len(cur) else 0.0 for k in ["young", "url_share"]}
    mb = float(cur.n_bursts.mean()) if len(cur) else 0.0
    n_rev = int((S[(S.narrative_id == nid)].tier == "review").sum())
    a, b = st.columns([3, 2])
    with a:
        st.markdown(f"**단계** {lv_badge(lv)} · **신뢰도** {conf} ({conf_v:.2f})",
                    unsafe_allow_html=True)
        if bool(r_now.domestic):
            st.warning("**국내 사안 — 군 관할 아님.** 반복 조정 행위는 보이지만 외국어 출처가 연결되지 않았습니다. "
                       "경보 단계를 올리지 않으며, 필요 시 관계 기관 이관을 검토합니다.")
        elif fo_seen:
            st.caption("관할: 외국발 서사 유입 — 탐지 대상")
        if fo_seen:
            st.markdown("**출처 (외국어 원문 → 한국어)**")
            first_ko = gk[gk.ts < t_now].ts.min()
            for f in fo_seen:
                lead = (first_ko - pd.Timestamp(f["ts"])) / pd.Timedelta(hours=1) if pd.notna(first_ko) else None
                st.markdown(f"- `{f['lang']}` {f['ts'][:16]} · {f['url']}"
                            + (f" · 한국어 첫 게시보다 **{lead:.1f}시간 앞섬**" if lead and lead > 0 else ""))
        bb = B[(B.narrative_id == nid) & (B.end < t_now)]
        st.markdown(f"**동시 게시 burst {len(bb)}회**")
        for r in bb.itertuples():
            _j = ss.judgments.get((nid, int(r.burst_id)))
            _tag = ""
            if _j:
                _lab = ANL.JUDGMENTS[_j["judgment"]][0]
                _col = {"normal": "#2a78d6", "confirmed": "#1baf7a", "hold": "#e0a000"}[_j["judgment"]]
                _tag = f" · <span style='color:{_col};font-weight:700'>분석관 판정: {_lab}</span>"
            st.markdown(f"- {r.start:%m-%d %H:%M}–{r.end:%H:%M} · 계정 {r.n_accounts}개 · "
                        f"문장 유사도 {r.mean_text_sim:.2f}" + (f" · URL {r.top_url}" if r.top_url else "") + _tag,
                        unsafe_allow_html=True)
        st.markdown(f"**의심 집단** 반복 조정 {len(cur)}개 계정 · 평균 burst 참여 {mb:.1f}회"
                    + (f" · 1회성 대규모 동시 게시 계정 {n_rev}개(검토 권장)" if lv == "REVIEW" else "")
                    + (f" · <span style='color:#2a78d6'>판정 반영: {_reas['n_before']} → {_reas['n_after']}개</span>" if _reas["removed"] else ""),
                    unsafe_allow_html=True)
        if _reas["removed"]:
            (st.warning if not _reas["watch_met"] else st.info)(_reas["note"])
        with st.expander("분석관 판정 — 이 burst는 정상인가? (판정은 체인에 기록되고, 근거 재집계에 반영됩니다)",
                         expanded=any(n == nid for (n, _b) in ss.judgments)):
            if len(bb):
                _opts = {int(r.burst_id): f"burst {int(r.burst_id)} · {r.start:%m-%d %H:%M}–{r.end:%H:%M} · 계정 {r.n_accounts}개"
                         + (f" · {r.top_url}" if r.top_url else "") for r in bb.itertuples()}
                _bid = st.selectbox("대상 burst", list(_opts), format_func=lambda k: _opts[k], key=f"jb_{nid}_{hour}")
                _jk = st.radio("판정", list(ANL.JUDGMENTS), format_func=lambda k: ANL.JUDGMENTS[k][0], horizontal=True, key=f"jk_{nid}_{hour}")
                st.caption(ANL.JUDGMENTS[_jk][1])
                _why = st.text_input("근거 (한 줄 · 보고서에 그대로 들어감)", key=f"jw_{nid}_{hour}",
                                     placeholder="예: 10-01 08시 묶음은 같은 속보 기사를 공유한 일반 계정으로 확인")
                cj1, cj2, cj3 = st.columns([1, 1, 2])
                if cj1.button("판정 기록", type="primary", key=f"jbtn_{nid}_{hour}"):
                    _prev = ss.jrecords[-1]["record_sha256"] if ss.jrecords else ANL.chain_end()
                    _rec = ANL.make_record(_prev, nid, hour, _bid, _jk, _why)
                    ss.judgments[(nid, _bid)] = dict(judgment=_jk, reason=_why, record=_rec)
                    ss.jrecords.append(_rec)
                    st.rerun()
                if cj2.button("판정 모두 초기화", key=f"jclr_{nid}_{hour}"):
                    ss.judgments = {}; ss.jrecords = []
                    st.rerun()
                if ss.jrecords:
                    _ok, _msg = ANL.verify_records(ss.jrecords, ANL.chain_end())
                    cj3.markdown(("✅ " if _ok else "❌ ") + f"판정 체인 {_msg} · 증거 체인 끝에 이어 붙임")
                    st.download_button("판정 기록 내려받기 (.jsonl)", "\n".join(json.dumps(x, ensure_ascii=False) for x in ss.jrecords),
                                       file_name="analyst_judgments.jsonl", mime="application/json", key=f"jdl_{nid}_{hour}")
                    for x in ss.jrecords:
                        st.caption(f"[{x['recorded_at']}] N{x['narrative_id']} {x['hour']}시 · burst {x['burst_id']} → {x['judgment_label']}"
                                   + (f" · {x['reason']}" if x["reason"] else "") + f" · {x['record_sha256'][:12]}…")
                st.caption("판정은 시스템 숫자를 덮어쓰지 않습니다. '정상' 판정은 해당 burst를 근거에서 빼고 의심 집단·관찰 조건을 다시 셀 뿐, "
                           "단계 자동 하향은 없습니다(해제는 분석관). 역할은 가명으로만 기록합니다.")
            else:
                st.caption("아직 관측된 burst가 없습니다.")
        with st.expander("브리핑 초안 — 규칙 기반 템플릿 · LLM 미사용 · 분석관 검토 전", expanded=False):
            _md = ANL.briefing_md(CTX)
            st.download_button("브리핑 초안 내려받기 (.md)", _md, file_name=f"briefing_N{nid}_{hour:02d}h.md", mime="text/markdown", key=f"bdl_{nid}_{hour}")
            st.markdown(_md)
        st.caption("신뢰도 = 0.4×집단 조정 점수 + 0.3×외국어 출처 연결 + 0.3×min(R̂,1). 가중치는 가정값입니다.")
        if not pd.isna(r_now.r_pool):
            rr = R[(R.narrative_id == nid) & (R.hour <= hour) & (R.hour > hour - 12)].dropna(subset=["r_pool"])
            msg = (f"**R̂ {r_now.r_pool:.2f}** (80% 구간 {r_now.r_lo:.2f}~{r_now.r_hi:.2f}) · "
                   f"**P(R>1) {r_now.p_gt1:.0%}** · P(R>0.8) {r_now.p_gt08:.0%}")
            if len(rr) >= 4:
                sl = np.polyfit(rr.hour, rr.r_pool, 1)[0]
                msg += f" · 최근 12시간 추세 시간당 {sl:+.3f}"
                if sl > 0 and r_now.r_pool < 1:
                    msg += f" → 약 **{(1 - r_now.r_pool) / sl:.0f}시간 뒤 1 도달 (추정)**"
            st.markdown(msg)
        cands = AL.disarm_candidates(len(bb), float(bb.mean_text_sim.max()) if len(bb) else 0.0,
                                     sm["url_share"], sm["young"], bool(fo_seen))
        if cands:
            st.markdown("**DISARM 후보 기법** <small style='color:#6b6b66'>(신호와 기법의 연결은 해석이며 최종 태깅은 분석관)</small>",
                        unsafe_allow_html=True)
            for c in cands:
                st.markdown(f"- `{c['id']}` {c['name']} — {c['why']}")
        st.markdown("**탐지 단계별 기본 조치** <small style='color:#6b6b66'>(대응 수위는 위 권고를 따름)</small>", unsafe_allow_html=True)
        for x in AL.ACTIONS.get(lv, []):
            st.markdown(f"- {x}")
        if URLNET is not None:
            if URLNET.get("n_urls", 0) < 10:
                st.markdown(f"**제2 신호층 (URL 공유 네트워크)** <small style='color:#6b6b66'>판정 보류 — 이 시나리오에는 링크가 {URLNET['n_urls']}개뿐이라 "
                            f"검정력이 없다(의심 묶음 {URLNET['flagged_components']}). 시각을 흩뜨린 공격에 대한 보강은 아래 '회피 내성' 참고</small>", unsafe_allow_html=True)
            else:
                st.markdown(f"**제2 신호층 (URL 공유 네트워크)** 의심 묶음 {URLNET['flagged_components']} · 계정 {URLNET['n_flagged_accounts']} "
                            f"<small style='color:#6b6b66'>(72시간 안 희귀 링크 2개 이상 함께 공유 · 대조군 우연 수준 {URLNET.get('null_flagged_mean', 0):.0f}개)</small>", unsafe_allow_html=True)
    with b:
        f4 = go.Figure(go.Bar(x=[sm["young"], min(mb / 2, 1.0), sm["url_share"]],
                              y=["신생 계정", "반복 burst", "동일 URL"], orientation="h",
                              marker_color=C_SUS, text=[f"{sm['young']:.2f}", f"{mb:.1f}회",
                                                         f"{sm['url_share']:.2f}"],
                              textposition="outside", hoverinfo="skip"))
        f4.update_layout(height=200, margin=dict(l=10, r=40, t=30, b=10), title="의심 집단의 신호 (평균)",
                         xaxis=dict(range=[0, 1.3], showgrid=False, visible=False), plot_bgcolor="white")
        st.plotly_chart(f4, width="stretch")
        st.caption("신호는 내용이 아니라 행동만 봅니다. 신호 하나만으로는 의심 집단이 되지 않습니다.")
    sus_tbl = S[(S.narrative_id == nid) & (S.tier != "normal")].copy()
    sus_tbl["편입"] = sus_tbl.account_id.map(lambda a: "지금 의심" if is_sus_beh(a) else "아직 아님")
    with st.expander(f"계정 근거 표 ({len(sus_tbl)}개, 가명 ID)"):
        st.dataframe(sus_tbl[["account_id", "tier", "편입", "score", "age_days", "n_bursts", "evidence"]]
                     .sort_values("score", ascending=False), width="stretch", hide_index=True)

# ---------------------------------------------------------------- 전조 카드 (축 A 공식 신호 · B 명분/동원 서사 · C 은밀 증폭 · D 물리 전조)
if PRE:
    import precursor_ui as PU
    camp = PRE["summary"]["campaign_narrative"]
    st.markdown("#### 전조 카드 — 공식 신호 · 명분 서사 · 은밀 증폭의 정합성")
    st.caption("회색지대 도발은 행동 전에 정보 환경이 먼저 준비된다는 가설을 네 축으로 나눠 봅니다. 축 A·B는 가상 자료(합성), 축 C는 위 탐지 결과 그대로, "
               "축 D(항만·선박·위성)는 연결 인터페이스만 둡니다. 말의 양을 세지 않고 발언의 구조(조건·시한·장소·수단·톤)를 뽑으며, 원문 인용이 없는 필드는 채우지 않습니다.")
    if nid != camp:
        st.info(f"전조 카드는 외국어 출처가 연결된 공작 서사 **N{camp}** 기준으로 만듭니다. 아래는 N{camp}의 카드입니다.")
    pre_row = PU.row_at(PRE, hour)
    st.plotly_chart(PU.timeline_fig(PRE, hour), width="stretch")
    st.caption("◆ 공식 발언(크기 = 수준 L1~L3, 빈 마름모 = 완화 톤) · ● 명분 ▲ 피해 ■ 동원 서사 · 사각형 색 = 축 C 경보 단계 · "
               "아래 띠: 보라 = 수사 단독, 주황 = 수렴, 자주 = 불일치")
    pol_row = None
    if POL is not None:
        _q = POL[(POL.narrative_id == camp) & (POL.hour == hour)]
        pol_row = _q.iloc[0].to_dict() if len(_q) else None
    pl, pr_ = st.columns([3, 2])
    with pl:
        with st.container(border=True):
            st.markdown(PU.card_html(PRE, pre_row, PRE["t0"], pol_row), unsafe_allow_html=True)
    with pr_:
        base = PU.base_statement(PRE, hour)
        if base:
            with st.container(border=True):
                st.markdown(PU.statement_html(base) + PU.latest_note_html(PRE, hour), unsafe_allow_html=True)
            with st.container(border=True):
                st.markdown(PU.cases_html(base, PRE["cases"], pre_row["state"]), unsafe_allow_html=True)
        else:
            st.info("이 시각에는 아직 공식 발언이 없습니다. 발언이 들어오면 구조화 결과와 유사 사례가 여기 표시됩니다.")
    with st.expander("축 B — 외국어 서사 항목 (지금까지 관측, 규칙 기반 분류)"):
        st.markdown(PU.items_table_html(PRE, hour), unsafe_allow_html=True)
    with st.expander("과거 사례 라이브러리 — 공개 보도 기준 7건 (선행 4 · 반례 2 · 오경보 1)"):
        st.markdown(PU.library_table_html(PRE["cases"]), unsafe_allow_html=True)
        st.caption("날짜·선행 일수는 보도 날짜 차이입니다. 사례 수가 적어 정확도를 주장하지 않고, 구조 일치 사례의 선행 범위만 참고합니다.")
    RP = PU.load_replay()
    if RP:
        with st.expander("역사 재생 — 실제 공개 담화에 같은 규칙을 돌리면? (10건 · 작동 확인, 정확도 주장 아님)", expanded=False):
            st.markdown(PU.replay_summary_text(RP), unsafe_allow_html=True)
            rp_tag = st.radio("규칙 판본", ["v2 (실제 담화를 보고 고친 규칙)", "v1 (합성 문장만 보고 만든 규칙)"], horizontal=True, key="rp_tag")
            st.plotly_chart(PU.replay_fig(RP, "v2" if rp_tag.startswith("v2") else "v1"), width="stretch")
            st.markdown(PU.replay_table_html(RP), unsafe_allow_html=True)
            st.markdown("**정직하게 적어 둘 것**\n" + "\n".join(f"- {x}" for x in RP["notes"]))
            st.caption(f"출처: {RP['source_file']} · 사례별 출처 URL과 확인 상태는 `출처_실사례_라이브러리.md`")
    sm = PRE["summary"]
    st.caption(f"이 시나리오에서: 공식 예고형 발언 {sm['a_first_level3_id']}({sm['a_first_level3_h']:.0f}시) → 은밀 증폭 관찰 {sm['c_first_watch_h']}시 "
               f"(발언 {sm['a_to_watch_h']:.0f}시간 뒤) → 수렴 {sm['first_converged_h']}시 → 공식 톤 완화와 은밀 증폭 상승이 어긋나는 불일치 {sm['first_mismatch_h']}시. "
               "모두 합성 데이터의 계산값입니다.")

# ---------------------------------------------------------------- 증거 봉인 (M6)
seal_path = os.path.join(OUT, "evidence_chain.jsonl")
st.markdown("#### 증거 봉인")
if os.path.exists(seal_path):
    import seal
    ok, msg = seal.verify(seal_path)
    st.markdown(("✅ " if ok else "❌ ") + msg)
    st.caption("관찰·경보·위험 단계에 처음 들어선 시점마다(관찰 = 일반 시민 사이 자생 확산 전) 출처·시간 순서·게시물 해시를 묶어 체인으로 이어 기록합니다. 원본 한 글자라도 바뀌면 검증이 실패합니다(변조 탐지). 자체 보관 체인이라 내부 일관성만 증명하며, 외부 타임스탬프 연동은 다음 단계입니다.")
else:
    st.caption("아직 봉인 기록이 없습니다. `python seal.py` 를 실행하세요.")

# ---------------------------------------------------------------- 민감도 분석
sens_path = os.path.join(OUT, "sensitivity.csv")
if os.path.exists(sens_path):
    with st.expander("민감도 분석 — 가정값을 바꿔도 결론이 유지되는가"):
        st.dataframe(pd.read_csv(sens_path), hide_index=True, width="stretch")
        ex_path = os.path.join(OUT, "sensitivity_extra.json")
        if os.path.exists(ex_path):
            EX = json.load(open(ex_path, encoding="utf-8"))
            ts_ = EX.get("time_shuffle", {})
            st.markdown(f"- **시간 셔플 대조:** 계정마다 게시 시각을 ±24시간 무작위로 밀면 burst "
                        f"{ts_.get('observed_bursts')}건 → {[x['bursts'] for x in ts_.get('shuffled', [])]}, "
                        f"의심 계정 {ts_.get('observed_suspected')}개 → {[x['suspected'] for x in ts_.get('shuffled', [])]}")
            for x in EX.get("no_foreign_source", []):
                st.markdown(f"- **외국어 출처를 지우면** N{x['narrative_id']}: 최고 {x['max_level']} · {x['jurisdiction']}")
        spp = os.path.join(OUT, "sensitivity_policy.csv")
        if os.path.exists(spp):
            st.markdown("**대응 단계 권고의 가정값 격자** (일반 반응 기준 × 확산 확률 기준)")
            st.dataframe(pd.read_csv(spp), hide_index=True, width="stretch")
        st.caption("공작 계정 탐지는 설정에 견고하다(합성 데이터의 신호가 강한 탓도 있음). 경보(ALERT) 시점은 R 합산 시간·확률 기준에 민감하므로 "
                   "운영 정책(오경보 허용 수준)으로 정해야 하는 값이다. 관찰(WATCH)과 위험(CRITICAL)은 안정적이다.")


# ---------------------------------------------------------------- 회피 내성 (레드팀) — 제2 신호층 URL 공유 네트워크
if RED is not None:
    st.divider()
    st.markdown("### 회피 내성 — 공격자가 게시 시각을 흩뜨리면?")
    st.caption("위 탐지(burst 층)는 '짧은 시간에 몰린 게시'를 봅니다. 공작자가 시각만 흩뜨리면 어떻게 되는지, 그리고 시각과 무관하게 "
               "'무엇을 함께 미는가'를 보는 제2 신호층(URL 공유 네트워크)이 얼마나 받쳐 주는지를 공격자 정교함 7단계로 쟀습니다. "
               "합성 데이터(정상 속보 대조군 포함) · 변형당 시드 3개 평균 · 서사 배정은 정답 라벨로 고정(burst 층에 유리한 조건).")
    rows = RT.curve_rows(RED)
    labels = [r[1] for r in rows]
    rd_l, rd_r = st.columns([3, 2])
    with rd_l:
        pick = st.select_slider("공격자 정교함 (왼쪽 → 오른쪽으로 갈수록 회피에 능숙)", options=labels, value=labels[0])
        i = labels.index(pick); r = rows[i]
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("burst 층 재현율", f"{r[2]:.2f}", help="공작 계정 중 '반복 동시 게시'로 의심 표시된 비율")
        m2.metric("URL-망 층 재현율", f"{r[3]:.2f}", help="공작 계정 중 '72시간 안 희귀 링크 2개 이상 함께 공유' 묶음(크기 5·밀도 0.3 이상)에 든 비율")
        m3.metric("합집합", f"{r[4]:.2f}")
        m4.metric("오탐 (burst / URL-망)", f"{r[5]:.0f} / {r[6]:.0f}", help="공작이 아닌 계정 중 의심 표시 수 — 거의 전부 속보 기사를 3번 재공유한 일반 계정")
        f6 = go.Figure()
        xs = list(range(len(rows)))
        f6.add_scatter(x=xs, y=[x[2] for x in rows], mode="lines+markers", name="burst 층(동시 게시)", line=dict(color=RT.C_BURST, width=3), marker=dict(size=9))
        f6.add_scatter(x=xs, y=[x[3] for x in rows], mode="lines+markers", name="URL-망 층(함께 미는 링크)", line=dict(color=RT.C_URL, width=3), marker=dict(size=9))
        f6.add_scatter(x=xs, y=[x[4] for x in rows], mode="lines", name="합집합", line=dict(color=RT.C_UNION, width=1.5, dash="dot"))
        f6.add_vrect(x0=i - 0.5, x1=i + 0.5, fillcolor="#1f1f1d", opacity=0.06, line_width=0)
        short = {"base": "기본<br>(동시 게시)", "jitter20": "시각<br>±20분", "jitter60": "시각<br>±60분", "jitter180": "시각<br>±180분",
                 "newsfeed": "뉴스<br>사칭형", "newsfeed_mix": "+ 인기 링크<br>희석 50%", "newsfeed_uniq": "+ 고유<br>단축 URL"}
        f6.update_layout(height=360, margin=dict(l=40, r=10, t=72, b=60), plot_bgcolor="white", title=dict(text="신호 생존 곡선 — 공격자 정교함에 따른 공작 계정 재현율", y=0.97, yanchor="top"),
                         xaxis=dict(tickvals=xs, ticktext=[short.get(x[0], x[1]) for x in rows], tickfont=dict(size=11), range=[-0.5, len(rows) - 0.5]),
                         yaxis=dict(range=[-0.05, 1.08], title="재현율", gridcolor="#eee"), legend=dict(orientation="h", y=1.13, x=0, font=dict(size=11)))
        st.plotly_chart(f6, width="stretch")
    with rd_r:
        net = RT.network_payload(RED, rows[i][0])
        if net and net["nodes"]:
            f7 = go.Figure()
            ex_, ey_ = [], []
            for e in net["edges"]:
                ex_ += [e["x0"], e["x1"], None]; ey_ += [e["y0"], e["y1"], None]
            f7.add_scatter(x=ex_, y=ey_, mode="lines", line=dict(color="#c9c8c0", width=0.8), opacity=0.7, hoverinfo="skip", showlegend=False)
            for kind, col in [("공작 계정", RT.C_SUS), ("속보 참여 일반 계정", RT.C_ORD), ("일반 계정", RT.C_GREY)]:
                nn = [n for n in net["nodes"] if n["kind"] == kind]
                if nn:
                    f7.add_scatter(x=[n["x"] for n in nn], y=[n["y"] for n in nn], mode="markers", name=kind,
                                   marker=dict(size=13, color=col, line=dict(color="#fff", width=1.5)),
                                   text=[n["id"] for n in nn], hovertemplate="%{text}<extra>" + kind + "</extra>")
            f7.update_layout(height=320, margin=dict(l=10, r=10, t=40, b=10), plot_bgcolor="white",
                             title=f"URL 공유 네트워크 — {pick} (시드 1)", xaxis=dict(visible=False), yaxis=dict(visible=False, scaleanchor="x"),
                             legend=dict(orientation="h", y=-0.02, x=0, font=dict(size=11)))
            st.plotly_chart(f7, width="stretch")
            comps = [c for c in net["components"] if c["flagged"]]
            comp_txt = ", ".join("크기 %d·밀도 %.2f" % (c["size"], c["density"]) for c in comps) or "없음"
            st.caption(f"선 = 72시간 안에 희귀 링크 2개 이상을 함께 공유(대조군 99.9 백분위 초과) · 의심 묶음 {len(comps)}개 "
                       f"({comp_txt}) · 묶인 계정 {net['flagged']}개 중 공작 {net['camp_in_flagged']}개. "
                       "파란 묶음은 같은 속보 기사를 3번 재공유한 일반 계정 — 이 층의 오탐이며 경보 단계에서는 걸러진다(실험 1).")
        else:
            st.info("이 변형에서는 임계값을 넘는 링크 공유 쌍이 없습니다 — 네트워크가 비어 있습니다(= 탐지 실패).")
    st.markdown("**읽는 법**")
    for t in RT.findings_text(RED, IRA_URL):
        st.markdown(f"- {t}")
    with st.expander("규칙·가정·격자 — 결과를 본 뒤 바꾼 것까지"):
        up = RED.get("urlnet_params", {})
        st.markdown(f"- **URL-망 규칙:** 두 계정이 {up.get('window_h', 72)}시간 안에 같은 희귀 링크(링크 공유 계정의 {up.get('rare_frac', 0.2):.0%} 이하가 공유)를 "
                    f"{up.get('min_shared', 2)}개 이상 함께 공유하면 쌍 점수(IDF 합) → 임계값은 URL을 무작위로 섞은 대조군의 99.9 백분위 → "
                    f"쌍을 이어 크기 {up.get('min_comp', 5)}·밀도 {up.get('min_density', 0.3)} 이상 묶음만 의심. 도메인 신규성(WHOIS)·단축 URL 해석은 데이터 없음.")
        st.markdown("- **희귀 기준 20%는 결과를 본 뒤 고른 가정값**입니다. 5%·10%·20%·전체 격자를 그대로 공개합니다(5%는 외국 기사 링크가 경계에 걸려 시드별로 0.93/0.83/0.00으로 불안정).")
        sw = pd.DataFrame(RED.get("rare_sweep", []))
        if len(sw):
            sw = sw.rename(columns={"rare_frac": "희귀 기준", "variant": "변형", "recall_url": "URL-망 재현율(평균)", "recall_min": "최소", "fp_url": "오탐", "null_flagged": "대조군 우연 묶임", "tau": "τ"})
            st.dataframe(sw, hide_index=True, width="stretch")
        st.caption("변경 이력(experiments/config.json · redteam_urlnet.changes): p99.9 임계값만 → 대조군 묶음 최대 29계정 → 밀도 0.3 추가 → 희귀 5% 추가(불안정) → 20%로 확정. "
                   "배경 링크 비율 25%·속보 공유 50%는 [가정]. 합성 결과이며 실데이터 검증은 아래 IRA 절.")

# ---------------------------------------------------------------- 실데이터 검증
real_path = os.path.join(HERE, "real", "real_results.json")
if os.path.exists(real_path):
    RR = json.load(open(real_path, encoding="utf-8"))
    st.divider()
    st.markdown("### 실데이터 검증 — 공개된 러시아 IRA 트윗")
    st.caption(f"FiveThirtyEight·클렘슨대 공개 데이터 · {RR['window']} · 트윗 {RR['tweets']:,}건 · 계정 {RR['accounts']}개 "
               "· 위 시스템과 같은 규칙(10분 안 같은 글·같은 링크, 2회 이상 반복)을 그대로 적용 · 계정은 가명")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("동시 게시 묶음", f"{RR['events']:,}건", help="10분 안에 서로 다른 계정 3개 이상이 같은 글이나 같은 링크를 올린 묶음")
    k2.metric("대조 실험(시각 무작위 이동)", f"{RR['null_events_mean']:.0f}건",
              help="계정마다 게시 시각을 ±3일 무작위로 밀었을 때 생기는 묶음 수. 우연이라면 비슷해야 함")
    k3.metric("반복 참여 계정(의심 기준)", f"{RR['accounts_repeated_share']:.0%}")
    k4.metric("같은 운영팀 비율", f"{RR['same_category_rate']:.1%}", delta=f"무작위 {RR['same_category_rate_random']:.0%}",
              delta_color="off", help="같은 묶음에 든 계정 쌍이 연구진 분류상 같은 팀인 비율")
    c_a, c_b = st.columns([3, 2])
    with c_a:
        rb = {k: v for k, v in RR["repeated_by_category"].items() if RR["accounts_by_category"].get(k, 0) >= 5}
        name = {"HashtagGamer": "해시태그 게임", "LeftTroll": "좌파 사칭", "RightTroll": "우파 사칭",
                "NonEnglish": "비영어(러시아어 등)", "NewsFeed": "뉴스 매체 사칭"}
        items = sorted(rb.items(), key=lambda kv: kv[1])
        f5 = go.Figure(go.Bar(x=[v for _, v in items],
                              y=[f"{name.get(k, k)} ({RR['accounts_by_category'][k]}개)" for k, _ in items],
                              orientation="h", marker_color=C_SUS,
                              text=[f"{v:.0%}" for _, v in items], textposition="outside", hoverinfo="skip"))
        f5.update_layout(height=260, title="운영팀별 '반복 동시 게시' 계정 비율 (=시스템이 잡는 비율)",
                         margin=dict(l=10, r=40, t=40, b=10), plot_bgcolor="white",
                         xaxis=dict(range=[0, 1.15], tickformat=".0%", gridcolor="#eee"))
        st.plotly_chart(f5, width="stretch")
    with c_b:
        st.markdown("**확인된 것**")
        st.markdown(f"- 실제 공작 계정도 동시 게시 흔적을 남긴다: 대조 실험 대비 **약 {RR['events']/max(RR['null_events_mean'],1):.0f}배**\n"
                    f"- 묶인 계정은 거의 같은 운영팀: **{RR['same_category_rate']:.1%}** (무작위 {RR['same_category_rate_random']:.0%})\n"
                    f"- 언어가 다른 계정이 같은 링크를 동시에 퍼 나른 묶음 **{RR['multi_language_url_events']}건**")
        st.markdown("**확인하지 못한 것 (한계)**")
        st.markdown("- 뉴스 매체 사칭 계정은 거의 못 잡음: 동시 게시 대신 각자 시간에 올림(아래 제2 신호층 결과 참고)\n"
                    "- 오탐: 이 데이터엔 일반 사용자가 없어 측정 불가\n"
                    "- R 경보·조기성: 리포스트 관계가 없어 측정 불가 → 플랫폼 데이터 협력 필요\n"
                    "- 한국어 공간: 공개된 한국 대상 공작 데이터셋 부재")
    if IRA_URL is not None:
        st.markdown("**제2 신호층(URL 공유 네트워크)을 같은 데이터에 적용하면** <small style='color:#6b6b66'>(같은 규칙·같은 임계값 규칙 · 대조군 = URL 셔플)</small>", unsafe_allow_html=True)
        u1, u2 = st.columns([3, 2])
        with u1:
            ir = RT.ira_rows(IRA_URL)
            f8 = go.Figure()
            f8.add_bar(y=[f"{r[0]} ({r[1]}개)" for r in ir], x=[r[2] for r in ir], orientation="h", name="burst 층", marker_color=RT.C_BURST,
                       text=[f"{r[2]:.0%}" for r in ir], textposition="outside")
            f8.add_bar(y=[f"{r[0]} ({r[1]}개)" for r in ir], x=[r[3] for r in ir], orientation="h", name="URL-망 층", marker_color=RT.C_URL,
                       text=[f"{r[3]:.0%}" for r in ir], textposition="outside")
            f8.update_layout(barmode="group", height=320, margin=dict(l=150, r=50, t=72, b=30), plot_bgcolor="white",
                             title=dict(text="운영팀별 의심 표시 비율 — burst 층 vs URL-망 층 (IRA 실데이터)", y=0.97, yanchor="top"),
                             xaxis=dict(range=[0, 1.2], tickformat=".0%", gridcolor="#eee"), yaxis=dict(automargin=True, tickfont=dict(size=12)),
                             legend=dict(orientation="h", y=1.14, x=0, font=dict(size=11)))
            st.plotly_chart(f8, width="stretch")
        with u2:
            nfp = IRA_URL["feed_profile"]["flagged_by_category"].get("NewsFeed", {})
            st.markdown(f"- URL-망이 묶은 계정 **{IRA_URL['urlnet']['flagged_accounts']}개**(비영어 1묶음, 밀도 {IRA_URL['urlnet']['components'][0]['density']:.2f}, "
                        f"같은 팀 {IRA_URL['urlnet']['same_category_rate']:.0%}) — 전부 burst 층이 이미 잡은 계정 → **실데이터 추가 이득 0**\n"
                        f"- 뉴스 매체 사칭 {IRA_URL['urlnet']['by_category']['NewsFeed']['n']}개: 두 층 모두 **0%** 유지\n"
                        f"- **발견:** 이 계정들의 링크는 bit.ly 등 단축 주소로만 남아 있고(2단계 해석 {IRA_URL['newsfeed_step2_resolved_share']:.0%}), "
                        f"계정마다 다른 도시의 지역 뉴스를 미러링 → '같은 링크'가 성립하지 않음. 레드팀의 '고유 단축 URL' 변형이 예측한 그대로\n"
                        f"- 보조 지표 '자동화 피드 프로필'은 뉴스 사칭 {nfp.get('flagged', 0)}/{nfp.get('n', 0)}개를 가려내지만 진짜 언론 봇과 구분 못 함 → 확인 목록용")
            st.caption(IRA_URL["feed_profile"]["caveat"])
    with st.expander("동시 게시 묶음 예시 (가명)"):
        for x in RR["examples"]:
            st.markdown(f"- {x['start'][:16]} · {x['span_sec']/60:.0f}분 사이 계정 **{x['n_accounts']}개** · "
                        f"{', '.join(x['langs'])} · 팀 {x['categories']}<br><small>{x['sample']}</small>",
                        unsafe_allow_html=True)

st.divider()
st.caption("이 화면은 판정이 아니라 분석가 보조 자료입니다. 최종 판단은 분석가가 합니다. "
           "합성 데이터 · 실존 개인/계정 없음 · 개인 식별·표적화 기능 없음.")

