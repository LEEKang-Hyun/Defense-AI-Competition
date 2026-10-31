"""
anim.py — 시간 흐름 재생 패널
화면 전체를 다시 그리지 않고, 브라우저 안에서 Plotly 애니메이션으로 h0 → h1 구간을 15분 단위로 재생한다.
위 왼쪽: 시간당 게시물(그 순간까지 알려진 분류로 색칠) · 위 오른쪽: 일반 사용자 간 R̂과 80% 구간
아래: 확산 경로 — 외국어 출처 → 의심 집단 → 일반 사용자. 일반 사용자는 (1시간, 단계) 집계 노드로만,
      개별 점은 외국어 출처와 '그 시점까지 행동 기준 의심이 확정된' 계정(가명)만.
제목: 시각 · 경보 단계 · R̂ · P(R>0.8) · 대응 권고 · 누적 게시물
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

STEP = 0.25  # 15분


def _interp(rs, col, t):
    """hour <= floor(t) 의 점 + t 시점 보간점(앞뒤 값이 모두 있을 때)"""
    h = int(np.floor(t))
    sub = rs[rs.hour <= h]
    xs, ys = list(sub.hour), list(sub[col])
    nxt = rs[rs.hour == h + 1]
    if t > h and len(nxt) and len(sub) and pd.notna(sub[col].iloc[-1]) and pd.notna(nxt[col].iloc[0]):
        a = t - h
        xs.append(t); ys.append((1 - a) * sub[col].iloc[-1] + a * nxt[col].iloc[0])
    return xs, ys


def build(gall, t0, rs, pol, joined, content_mode, h0, h1, max_h, colors, lv_style, fo_urls,
          r_alert=0.8, r_crit=1.0, frame_ms=40):
    """gall: 이 서사 전체 게시물(post_id, parent_id, ts, account_id, lang, url) · rs: R 시계열(이 서사)
    pol: hour→권고 문구 · joined: 계정→행동 기준 의심 확정 시각 · fo_urls: 외국어 출처 url→post_id"""
    C_ORD, C_SUS, C_SRC = colors
    G = gall.sort_values("ts").reset_index(drop=True).copy()
    G["tt"] = ((G.ts - t0) / pd.Timedelta(hours=1)).astype(float)
    G["hh"] = G.tt.astype(int)
    G["ko"] = G.lang == "ko"
    G["jt"] = G.account_id.map(lambda a: (joined[a] - t0) / pd.Timedelta(hours=1) if a in joined else np.inf)
    G.loc[~G.ko, "jt"] = np.inf
    # 내용 기준: 그 시점까지 이 서사를 말한(첫 한국어 게시) 계정은 모두 의심
    first_say = G[G.ko].groupby("account_id").tt.min()
    G["st"] = G.account_id.map(first_say).fillna(np.inf)
    # 확산 단계(깊이)와 위치
    idx = {p: i for i, p in enumerate(G.post_id)}
    depth = np.zeros(len(G), dtype=int)
    par = np.full(len(G), -1)
    for i, r in enumerate(G.itertuples()):
        pi = idx.get(r.parent_id, -1) if r.parent_id else -1
        par[i] = pi
        depth[i] = 0 if not r.ko else (depth[pi] + 1 if pi >= 0 else 1)
    G["d"] = depth
    rng = np.random.default_rng(0)
    G["ix"] = G.tt.round(2)
    G["iy"] = (G.d + rng.uniform(-0.25, 0.25, len(G))).round(2)
    G["ax"] = np.floor(G.tt) + 0.5
    G["ay"] = G.d.astype(float)
    url_par = np.array([idx.get(fo_urls.get(u), -1) if (k and not p and u) else -1
                        for u, k, p in zip(G.url, G.ko, G.parent_id)])
    gk = G[G.ko]
    hours = np.arange(0, max_h + 1)

    def bars(t):
        m = gk.tt < t
        sus = (gk.st <= t) if content_mode else (gk.jt <= t)
        o = gk[m & ~sus].groupby("hh").size().reindex(hours, fill_value=0)
        s = gk[m & sus].groupby("hh").size().reindex(hours, fill_value=0)
        return o.values, s.values

    def graph(t):
        vis = (G.tt < t).values
        beh = (G.jt <= t).values
        ind = vis & ((~G.ko.values) | beh)
        x = np.where(ind, G.ix, G.ax); y = np.where(ind, G.iy, G.ay)

        def lines(parent):
            xs, ys = [], []
            for c in np.where(vis & (parent >= 0))[0]:
                p = parent[c]
                if vis[p]:
                    xs += [x[p], x[c], None]; ys += [y[p], y[c], None]
            return xs, ys
        ex, ey = lines(par)
        ux, uy = lines(url_par)
        fo = vis & ~G.ko.values
        su = ind & G.ko.values
        agg = G[vis & G.ko.values & ~ind]
        if content_mode:
            orange = (agg.st <= t)
        else:
            orange = pd.Series(False, index=agg.index)

        def agg_xy(d):
            a = d.groupby(["ax", "ay"]).size().reset_index(name="n")
            return list(a.ax), list(a.ay), list(6 + 3 * np.sqrt(a.n))
        ox, oy, os_ = agg_xy(agg[~orange])
        cx, cy, cs = agg_xy(agg[orange])
        return [go.Scatter(x=ux, y=uy, mode="lines"), go.Scatter(x=ex, y=ey, mode="lines"),
                go.Scatter(x=list(G.ix[fo]), y=list(G.iy[fo]), mode="markers"),
                go.Scatter(x=list(G.ix[su]), y=list(G.iy[su]), mode="markers"),
                go.Scatter(x=ox, y=oy, mode="markers", marker=dict(size=os_)),
                go.Scatter(x=cx, y=cy, mode="markers", marker=dict(size=cs))]

    def title(t):
        h = max(1, int(np.floor(t)))
        row = rs[rs.hour == h]
        lv = row.level.iloc[0] if len(row) else "NONE"
        sym, col, name = lv_style[lv]
        r = row.r_pool.iloc[0] if len(row) else np.nan
        p = row.p_gt08.iloc[0] if len(row) else np.nan
        act = pol.get(h, "—")
        n = int((gk.tt < t).sum())
        rtxt = "R̂ —" if pd.isna(r) else f"R̂ {r:.2f} · P(R>0.8) {p:.0%}"
        return (f"<b>{h}시</b>  <span style='color:{col}'><b>{sym} {name}</b></span>   {rtxt}   "
                f"·  권고 <b>{act}</b>   ·  게시물 {n}건")

    # 세로축은 재생에 맞춰 그 순간까지의 데이터 크기를 따라 넓어진다 (초반이 바닥에 깔리지 않게)
    hc = gk.groupby("hh").size()

    def yr(t):
        seen = hc[hc.index <= int(np.floor(t))]
        v = max(25.0, float(seen.max()) * 1.15) if len(seen) else 25.0
        rr = rs[rs.hour <= max(1, int(np.ceil(t)))]
        r = max(1.6, float(np.nanmax(rr.r_hi)) + 0.1) if rr.r_hi.notna().any() else 1.6
        dd = G[G.tt < t].d
        d = max(4.6, float(dd.max()) + 0.6) if len(dd) else 4.6
        return dict(yaxis=dict(range=[0, v]), yaxis2=dict(range=[0, r]), yaxis3=dict(range=[-0.6, d]))

    def shapes(t):
        base = [dict(type="rect", xref="x2", yref="y2", x0=0, x1=max_h, y0=r_alert, y1=r_crit,
                     fillcolor="#ec835a", opacity=0.10, line_width=0, layer="below"),
                dict(type="line", xref="x2", yref="y2", x0=0, x1=max_h, y0=1, y1=1,
                     line=dict(color="#d03b3b", width=1))]
        return base + [dict(type="line", xref=x, yref=y, x0=t, x1=t, y0=0, y1=1,
                            line=dict(color="#6b6b66", dash="dot", width=1.5))
                       for x, y in (("x", "y domain"), ("x2", "y2 domain"), ("x3", "y3 domain"))]

    def traces(t):
        o, s = bars(t)
        bx, by = _interp(rs, "r_pool", t)
        lx, ly = _interp(rs, "r_lo", t)
        hx, hy = _interp(rs, "r_hi", t)
        ok = [i for i in range(min(len(lx), len(hx))) if pd.notna(ly[i]) and pd.notna(hy[i])]
        lx = [lx[i] for i in ok]; ly = [ly[i] for i in ok]; hx = [hx[i] for i in ok]; hy = [hy[i] for i in ok]
        return [go.Bar(x=hours, y=o), go.Bar(x=hours, y=s),
                go.Scatter(x=hx + lx[::-1], y=hy + ly[::-1], mode="lines"),
                go.Scatter(x=bx, y=by, mode="lines")] + graph(t)

    ts = list(np.round(np.arange(h0, h1 + 1e-9, STEP), 2))
    fig = make_subplots(rows=2, cols=2, specs=[[{}, {}], [{"colspan": 2}, None]],
                        row_heights=[0.42, 0.58], horizontal_spacing=0.08, vertical_spacing=0.13,
                        subplot_titles=("시간당 게시물", "일반 사용자 간 R̂ (파란 띠 = 80% 구간)",
                                        "확산 경로 — 외국어 출처(0단계)에서 일반 사용자까지 · 일반 사용자는 집계 노드 · 가로축: 시작 후 시간"))
    tr = traces(ts[0])
    sl = dict(legendgroup="a")
    fig.add_trace(go.Bar(x=hours, y=tr[0].y, name="일반 사용자", marker_color=C_ORD, hoverinfo="skip"), 1, 1)
    fig.add_trace(go.Bar(x=hours, y=tr[1].y, name="의심 집단", marker_color=C_SUS, hoverinfo="skip"), 1, 1)
    fig.add_trace(go.Scatter(x=tr[2].x, y=tr[2].y, mode="lines", fill="toself", fillcolor="rgba(42,120,214,0.15)",
                             line=dict(width=0), hoverinfo="skip", showlegend=False), 1, 2)
    fig.add_trace(go.Scatter(x=tr[3].x, y=tr[3].y, mode="lines", line=dict(color=C_ORD, width=2.5),
                             hoverinfo="skip", showlegend=False), 1, 2)
    fig.add_trace(go.Scatter(x=tr[4].x, y=tr[4].y, mode="lines", name="동일 URL 공유",
                             line=dict(color=C_SRC, width=1, dash="dot"), opacity=0.6, hoverinfo="skip"), 2, 1)
    fig.add_trace(go.Scatter(x=tr[5].x, y=tr[5].y, mode="lines", name="리포스트·답글",
                             line=dict(color="#b5b4ad", width=1), opacity=0.6, hoverinfo="skip"), 2, 1)
    fig.add_trace(go.Scatter(x=tr[6].x, y=tr[6].y, mode="markers", name="외국어 출처",
                             marker=dict(color=C_SRC, size=12, line=dict(color="white", width=1)), hoverinfo="skip"), 2, 1)
    fig.add_trace(go.Scatter(x=tr[7].x, y=tr[7].y, mode="markers", name="의심 계정(가명, 개별)",
                             marker=dict(color=C_SUS, size=8, line=dict(color="white", width=1)), hoverinfo="skip"), 2, 1)
    fig.add_trace(go.Scatter(x=tr[8].x, y=tr[8].y, mode="markers", name="일반 사용자(집계)",
                             marker=dict(color=C_ORD, size=tr[8].marker.size, opacity=0.75,
                                         line=dict(color="white", width=1)), hoverinfo="skip"), 2, 1)
    fig.add_trace(go.Scatter(x=tr[9].x, y=tr[9].y, mode="markers", name="내용 기준 의심(집계)",
                             marker=dict(color=C_SUS, size=tr[9].marker.size, opacity=0.6,
                                         line=dict(color="white", width=1)), hoverinfo="skip",
                             showlegend=bool(content_mode)), 2, 1)
    fig.frames = [go.Frame(name=str(t), data=traces(t), traces=list(range(10)),
                           layout=dict(shapes=shapes(t), title=dict(text=title(t)), **yr(t)))
                  for t in ts]
    play = dict(frame=dict(duration=frame_ms, redraw=True), transition=dict(duration=0), fromcurrent=False, mode="immediate")
    fig.update_layout(
        barmode="stack", bargap=0.15, height=820, plot_bgcolor="white", paper_bgcolor="white",
        title=dict(text=title(ts[0]), x=0.01, y=0.985, font=dict(size=16)),
        shapes=shapes(ts[0]), margin=dict(l=45, r=15, t=70, b=70),
        legend=dict(orientation="h", x=0, y=-0.06),
        xaxis=dict(range=[0, max_h]), xaxis2=dict(range=[0, max_h]),
        xaxis3=dict(range=[0, max_h]),
        yaxis=dict(range=yr(ts[0])["yaxis"]["range"], gridcolor="#eee"), yaxis2=dict(range=yr(ts[0])["yaxis2"]["range"], gridcolor="#eee"),
        yaxis3=dict(range=yr(ts[0])["yaxis3"]["range"], gridcolor="#eee", title="출처로부터 단계"),
        updatemenus=[dict(type="buttons", showactive=False, x=1.0, y=-0.06, xanchor="right", yanchor="top",
                          buttons=[dict(label="↻ 다시 재생", method="animate", args=[None, play])])])
    return fig.to_html(full_html=True, include_plotlyjs=True, auto_play=True,
                       animation_opts=play, config=dict(displayModeBar=False))
