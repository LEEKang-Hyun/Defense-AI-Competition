"""
obsgraph.py — 확산 그래프 재생 (Obsidian 그래프 뷰 스타일)
계정 = 점, 리포스트·답글·외국어 출처 URL 공유 = 선, 반복 동시 게시로 묶인 의심 계정 = 주황 연결선.
브라우저 안에서 물리 시뮬레이션(밀어내기·당기기)으로 떠다니며, 시간에 따라 점·선이 생겨나는 애니메이션.
개인 보호: 일반 사용자는 이름표 없이 점으로만. 이름표(가명 ID)는 외국어 출처와 행동 기준 의심 확정 계정만.
실행: python3 obsgraph.py [서사번호=0]  →  out/graph_N0.html
"""
import json, os, sys
import numpy as np
import pandas as pd
import alerts as AL

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
LV_STYLE = {"NONE": ("·", "#8a8a85", "경보 없음"), "REVIEW": ("◇", "#9a9a95", "검토 권장"),
            "WATCH": ("●", "#fab219", "관찰"), "ALERT": ("▲", "#ec835a", "경보"),
            "CRITICAL": ("■", "#e04848", "위험")}


def payload(nid, P=None, S=None, M=None, SRC=None, R=None, POL=None):
    if P is None:
        P, S, B, M, SRC = AL.load()
    if R is None:
        R = pd.read_csv(os.path.join(OUT, "r_series.csv"), parse_dates=["ts"])
    if POL is None and os.path.exists(os.path.join(OUT, "policy.csv")):
        POL = pd.read_csv(os.path.join(OUT, "policy.csv"), keep_default_na=False)
    t0 = P.ts.min().floor("D")
    hr = lambda ts: round(float((ts - t0) / pd.Timedelta(hours=1)), 4)
    g = P[P.narrative_id == nid].sort_values("ts").reset_index(drop=True)
    joined = AL.suspect_asof(S, M, nid)
    fo_urls = {f["url"]: f["account_id"] for f in SRC.get(str(nid), {}).get("foreign", []) if f.get("url")}

    accs = list(dict.fromkeys(g.account_id))
    ai = {a: i for i, a in enumerate(accs)}
    post_acc = dict(zip(g.post_id, g.account_id))
    nodes = []
    for a in accs:
        ga = g[g.account_id == a]
        ko = ga[ga.lang == "ko"]
        fo = len(ko) == 0
        nodes.append(dict(fo=int(fo), tf=hr(ga.ts.min()),
                          tj=hr(joined[a]) if a in joined else None,
                          ts=hr(ko.ts.min()) if len(ko) else None,
                          id=a if (fo or a in joined) else ""))     # 일반 사용자는 ID를 싣지 않는다
    posts, edges = [], {}
    for r in g.itertuples():
        t = hr(r.ts)
        src, kind = None, ""
        if r.parent_id and r.parent_id in post_acc:
            src, kind = post_acc[r.parent_id], "r"
        elif r.url and r.url in fo_urls and r.lang == "ko":
            src, kind = fo_urls[r.url], "u"
        p = ai[src] if src is not None and src != r.account_id else -1
        posts.append([t, ai[r.account_id], p])
        if p >= 0:
            k = (min(p, ai[r.account_id]), max(p, ai[r.account_id]))
            if k not in edges:
                edges[k] = [k[0], k[1], t, kind, p]   # 마지막 = 출발점(퍼뜨린 쪽)
    # 반복 동시 게시로 묶인 의심 계정끼리: 두 계정 모두 의심 확정된 시점에 나타남
    ce = pd.read_csv(os.path.join(OUT, "coord_edges.csv"))
    ce = ce[(ce.narrative_id == nid) & ce.a.isin(joined) & ce.b.isin(joined) & ce.a.isin(ai) & ce.b.isin(ai)]
    coord = [[ai[x.a], ai[x.b], hr(max(joined[x.a], joined[x.b])), int(x.co_bursts)] for x in ce.itertuples()]

    rs = R[R.narrative_id == nid].sort_values("hour")
    pol = {} if POL is None else POL[POL.narrative_id == nid].set_index("hour")
    hours = {}
    for x in rs.itertuples():
        h = int(x.hour)
        row = dict(lv=x.level, r=None if pd.isna(x.r_pool) else round(float(x.r_pool), 2),
                   p=None if pd.isna(x.p_gt08) else round(float(x.p_gt08), 2),
                   p1=None if pd.isna(x.p_gt1) else round(float(x.p_gt1), 2))
        if len(pol) and h in pol.index:
            row["act"] = pol.loc[h, "action_label"]
            row["dont"] = pol.loc[h, "do_not"]
        hours[h] = row
    stops = []
    for lv in ("WATCH", "ALERT", "CRITICAL", "REVIEW"):
        hs = rs[rs.level == lv].hour
        if len(hs):
            stops.append([int(hs.min()), lv])
    stops.sort()
    src = SRC.get(str(nid), {})
    return dict(nid=int(nid), t0=str(t0), max_h=int(R.hour.max()), nodes=nodes, posts=posts,
                edges=list(edges.values()), coord=coord, hours=hours, stops=stops, lv=LV_STYLE,
                n_foreign=len(src.get("foreign", [])), lead=src.get("lead_hours"))


def build_html(nid=0, start=0.0, autoplay=True, height=None, **kw):
    d = payload(nid, **kw)
    d["start"], d["autoplay"] = float(start), bool(autoplay)
    with open(os.path.join(HERE, "obsgraph_template.html"), encoding="utf-8") as f:
        tpl = f.read()
    return tpl.replace("/*__DATA__*/null", json.dumps(d, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    nid = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    path = os.path.join(OUT, f"graph_N{nid}.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(build_html(nid))
    print(path)
