"""
export_html.py — 오프라인 백업 시연 화면 만들기
파이프라인(M1~M6) 결과를 담아 인터넷·파이썬 없이 브라우저로 여는 demo.html 하나를 만든다.
화면 논리는 app.py와 같다: 슬라이더 시각에 분석관이 알 수 있었던 것만 보여준다.
실행 : python export_html.py   →  demo.html
"""
import json, os
import numpy as np
import pandas as pd
import plotly

import alerts as AL
import seal

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")


def build_data():
    """화면 데이터 D를 만든다 (demo.html과 한 화면 시연 demo_story.html이 같은 D를 쓴다)"""
    P, S, B, M, SRC = AL.load()
    R = pd.read_csv(os.path.join(OUT, "r_series.csv"), parse_dates=["ts"])
    cards = json.load(open(os.path.join(OUT, "alerts.json"), encoding="utf-8"))
    t0 = P.ts.min().floor("D")
    hr = lambda ts: float((pd.Timestamp(ts) - t0) / pd.Timedelta(hours=1))
    rng = np.random.default_rng(0)

    nars = {}
    for c in cards:
        nid = c["narrative_id"]
        g = P[P.narrative_id == nid].sort_values("ts").reset_index(drop=True)
        idx = {p: i for i, p in enumerate(g.post_id)}
        depth = {}
        for r in g.itertuples():
            depth[r.post_id] = 0 if r.lang != "ko" else (depth.get(r.parent_id, 0) + 1 if r.parent_id else 1)
        src = SRC.get(str(nid), {})
        src_urls = {f["url"] for f in src.get("foreign", []) if f.get("url")}
        accs = sorted(set(g.account_id))
        aidx = {a: i for i, a in enumerate(accs)}
        posts = [[round(hr(r.ts), 3), round(depth[r.post_id] + float(rng.uniform(-0.25, 0.25)), 3),
                  aidx[r.account_id], r.lang, idx.get(r.parent_id, -1),
                  1 if (r.lang == "ko" and not r.parent_id and r.url in src_urls) else 0,
                  r.text[:40], r.url if r.lang != "ko" else ""]
                 for r in g.itertuples()]
        joined = {aidx[a]: round(hr(t), 3) for a, t in AL.suspect_asof(S, M, nid).items() if a in aidx}
        s = S[S.narrative_id == nid]
        rs = R[R.narrative_id == nid]
        nars[str(nid)] = dict(
            accounts=accs, posts=posts, joined=joined,
            scores={str(aidx[r.account_id]): [r.score, r.young, r.url_share, int(r.n_bursts), r.tier,
                                             int(r.age_days), r.evidence]
                    for r in s.itertuples() if r.account_id in aidx},
            bursts=[dict(id=int(r.burst_id), s=hr(r.start), e=hr(r.end), start=f"{r.start:%m-%d %H:%M}", end=f"{r.end:%H:%M}",
                         n=int(r.n_accounts), sim=float(r.mean_text_sim), url=r.top_url)
                    for r in B[B.narrative_id == nid].itertuples()],
            # 분석관 판정 재집계용: 의심 계정 → [[burst_id, 종료 시각(h)] ...] (정상 판정 burst를 빼고 두 번째 남은 종료 시각 = 편입)
            ab={str(aidx[a]): [[int(b), round(hr(t), 3)] for b, t in zip(mm.burst_id, mm.burst_end)]
                for a, mm in M[(M.narrative_id == nid) & (M.account_id.isin(set(s[s.tier == "suspected"].account_id)))].groupby("account_id") if a in aidx},
            r=[dict(h=int(r.hour), r=None if pd.isna(r.r_pool) else round(float(r.r_pool), 3),
                    lo=None if pd.isna(r.r_lo) else round(float(r.r_lo), 3), hi=None if pd.isna(r.r_hi) else round(float(r.r_hi), 3),
                    p1=None if pd.isna(r.p_gt1) else round(float(r.p_gt1), 3), p08=None if pd.isna(r.p_gt08) else round(float(r.p_gt08), 3),
                    dom=bool(r.domestic),
                    n_susp=int(r.n_susp), n_sofar=int(r.n_posts_sofar), level=r.level) for r in rs.itertuples()],
            foreign=[dict(lang=f["lang"], x=hr(f["ts"]), ts=f["ts"][:16], url=f["url"])
                     for f in src.get("foreign", [])],
            samples=c["narrative_samples"], n_review=int((s.tier == "review").sum()))
    levels_by_hour = {}
    for n in R.narrative_id.unique():
        rs = R[R.narrative_id == n]
        levels_by_hour[str(int(n))] = rs.level.tolist()
    ok, msg = seal.verify()
    sp = os.path.join(OUT, "sensitivity.csv")
    sens = pd.read_csv(sp).to_dict("records") if os.path.exists(sp) else []
    xp = os.path.join(OUT, "sensitivity_extra.json")
    sens_x = json.load(open(xp, encoding="utf-8")) if os.path.exists(xp) else {}
    rp = os.path.join(HERE, "real", "real_results.json")
    real = json.load(open(rp, encoding="utf-8")) if os.path.exists(rp) else None
    max_h = int(R.hour.max())
    pp = os.path.join(OUT, "policy.csv")
    POL = pd.read_csv(pp, keep_default_na=False) if os.path.exists(pp) else None
    for k, v in nars.items():
        if POL is None:
            v["pol"] = []; continue
        pg = POL[POL.narrative_id == int(k)].sort_values("hour")
        v["pol"] = [dict(h=int(r.hour), a=int(r.action), al=r.action_label, sl=r.stage_label, attr=r.attribution,
                         now=r.why_now, lvl=r.why_level, dn=[x for x in str(r.do_not).split(" | ") if x],
                         esc=r.escalate_if, nt=[x for x in str(r.notes).split(" | ") if x],
                         cf=float(r.confidence), st=str(r.sticky) == "True") for r in pg.itertuples()]
    spp = os.path.join(OUT, "sensitivity_policy.csv")
    sens_pol = pd.read_csv(spp).to_dict("records") if os.path.exists(spp) else []
    vol = {}
    for n, kk in P[(P.lang == "ko") & (P.narrative_id >= 0)].groupby("narrative_id"):
        hc = kk.assign(h=((kk.ts - t0) / pd.Timedelta(hours=1)).astype(int)).groupby("h").size() \
            .reindex(range(max_h + 1), fill_value=0).values
        vh = AL.volume_alarm_hour(hc)
        lv_list = R[R.narrative_id == n].sort_values("hour").level.tolist()
        if vh is None and all(l == "NONE" for l in lv_list):
            continue
        smp = next((c["narrative_samples"][0] for c in cards if c["narrative_id"] == n), kk.text.iloc[0])
        vol[str(int(n))] = dict(vh=vh, sample=smp[:28], levels=lv_list)
    prp = os.path.join(OUT, "precursor.json")
    pre = json.load(open(prp, encoding="utf-8")) if os.path.exists(prp) else None   # 전조 카드 (축 A·B·정합성)
    rpp = os.path.join(OUT, "precursor_replay.json")
    replay = json.load(open(rpp, encoding="utf-8")) if os.path.exists(rpp) else None  # 역사 재생 (실제 공개 담화 백테스트)
    import redteam_ui as RT
    RED, IRA_URL = RT.load()
    red = None
    if RED is not None:
        red = dict(rows=RT.curve_rows(RED), nets={v: RT.network_payload(RED, v) for v in RED["variants"]},
                   findings=RT.findings_text(RED, IRA_URL), ira=(RT.ira_rows(IRA_URL) if IRA_URL else None),
                   ira_meta=(dict(flagged=IRA_URL["urlnet"]["flagged_accounts"], density=IRA_URL["urlnet"]["components"][0]["density"] if IRA_URL["urlnet"]["components"] else None,
                                  same=IRA_URL["urlnet"]["same_category_rate"], nf_n=IRA_URL["urlnet"]["by_category"]["NewsFeed"]["n"],
                                  step2=IRA_URL["newsfeed_step2_resolved_share"], feed=IRA_URL["feed_profile"]["flagged_by_category"].get("NewsFeed", {}),
                                  caveat=IRA_URL["feed_profile"]["caveat"]) if IRA_URL else None),
                   sweep=RED.get("rare_sweep", []), params=RED.get("urlnet_params", {}),
                   colors=dict(burst=RT.C_BURST, url=RT.C_URL, union=RT.C_UNION))
    urlnet_p = os.path.join(OUT, "urlnet_summary.json")
    urlnet = json.load(open(urlnet_p, encoding="utf-8")) if os.path.exists(urlnet_p) else None
    import analyst as ANL
    an = dict(chain_end=ANL.chain_end(), judgments={k: list(v) for k, v in ANL.JUDGMENTS.items()}, limits=ANL.LIMITS, conops=ANL.CONOPS,
              min_susp=ANL.MIN_SUSPECTS, role=ANL.ROLE)
    D = dict(max_h=max_h, t0=str(t0), nars=nars, actions=AL.ACTIONS, vol=vol, pre=pre, replay=replay, red=red, urlnet=urlnet, an=an,
             disarm=[dict(key=k, id=i, name=nm, why=w) for k, i, nm, w in AL.DISARM],
             levels=AL.LEVELS, r_alert=AL.R_ALERT, seal=dict(ok=ok, msg=msg), real=real, sens=sens, sens_x=sens_x, sens_pol=sens_pol)
    # 한 화면 시연용 메타 (전체 규모 · 지표)
    mp = os.path.join(OUT, "metrics.json")
    metrics = json.load(open(mp, encoding="utf-8")) if os.path.exists(mp) else {}
    n_ch = 0
    cp = os.path.join(OUT, "evidence_chain.jsonl")
    if os.path.exists(cp):
        n_ch = sum(1 for l in open(cp, encoding="utf-8") if l.strip())
    # 서사별 요약 (정상 서사 포함 전부): 최고 단계 · 게시물 수 · 볼륨 감시 경보 시각 · 예시 문장 · 외국어 출처 유무
    narr = {}
    for n in sorted(R.narrative_id.unique()):
        rs = R[R.narrative_id == n].sort_values("hour")
        kk = P[(P.narrative_id == n) & (P.lang == "ko")]
        hc = kk.assign(h=((kk.ts - t0) / pd.Timedelta(hours=1)).astype(int)).groupby("h").size() \
            .reindex(range(max_h + 1), fill_value=0).values if len(kk) else np.zeros(max_h + 1)
        lv_order = AL.LEVELS
        mx = max(rs.level.tolist(), key=lambda l: lv_order.index(l)) if len(rs) else "NONE"
        first_lv = {l: int(rs[rs.level == l].hour.min()) for l in lv_order if l != "NONE" and (rs.level == l).any()}
        smp = next((c["narrative_samples"][0] for c in cards if c["narrative_id"] == n), (kk.text.iloc[0] if len(kk) else ""))
        pol_first = ""
        if POL is not None:
            pq = POL[(POL.narrative_id == int(n)) & (POL.action > 0)].sort_values("hour")
            pol_first = str(pq.action_label.iloc[0]) if len(pq) else ""
        narr[str(int(n))] = dict(max_level=mx, first=first_lv, n_posts=int(len(kk)), vh=AL.volume_alarm_hour(hc),
                                 sample=str(smp)[:40], foreign=int(len(SRC.get(str(int(n)), {}).get("foreign", []))),
                                 domestic=bool(rs.domestic.any()) if "domestic" in rs else False, pol_first=pol_first)
    try:   # 한 화면 시연의 그래프 뷰(Obsidian 스타일) 재료 — 공작 서사의 계정·연결·게시 시각
        import obsgraph as OG
        camp_nid = int(pre["summary"]["campaign_narrative"]) if pre else int(next(iter(nars)))
        D["graph"] = OG.payload(camp_nid, P=P, S=S, M=M, SRC=SRC, R=R, POL=POL)
    except Exception as e:   # noqa: BLE001
        print("graph payload 생략:", e)
        D["graph"] = None
    D["sat"] = sat_payload()
    D["meta"] = dict(n_posts=int(len(P)), n_accounts=int(P.account_id.nunique()), n_hours=max_h, narr=narr,
                     n_narratives=int(P.truth_narrative.nunique()) if "truth_narrative" in P else None,
                     n_foreign=int((P.lang != "ko").sum()), n_bursts=int(len(B)), n_suspected=int((S.tier == "suspected").sum()),
                     n_chain=n_ch, metrics=metrics)
    return D


SAT_DIR = os.path.join(HERE, "data", "sat")   # 축 D 실제 위성 사례(캡처 파일 + manifest)


def _embed(path, max_w=1280, quality=82):
    """위성 캡처 PNG/JPG → 가로 max_w로 줄여 JPEG data URL. 파일이 없으면 None."""
    if not os.path.exists(path):
        return None
    try:
        from PIL import Image
        import base64, io
        im = Image.open(path).convert("RGB")
        if im.width > max_w:
            im = im.resize((max_w, int(im.height * max_w / im.width)))
        buf = io.BytesIO(); im.save(buf, "JPEG", quality=quality, optimize=True)
        return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    except Exception as e:  # noqa: BLE001
        print("위성 영상 임베드 실패:", path, e); return None


def sat_payload():
    """data/sat/manifest.json + 실제로 들어온 캡처 파일 → 화면 재료. 파일이 없는 자리는 안내문으로 남긴다."""
    mp = os.path.join(SAT_DIR, "manifest.json")
    if not os.path.exists(mp):
        return None
    M = json.load(open(mp, encoding="utf-8"))
    n_img = 0
    for site in M.get("sites", []):
        for k in ("before", "after"):
            f = site[k].get("file")
            site[k]["src"] = _embed(os.path.join(SAT_DIR, f)) if f else None
            n_img += 1 if site[k]["src"] else 0
        la, lo = site.get("lat"), site.get("lon")
        site["browser_url"] = (f"https://browser.dataspace.copernicus.eu/?zoom={site.get('zoom', 14)}&lat={la}&lng={lo}"
                               f"&datasetId=S2_L2A_CDAS&layerId=1_TRUE_COLOR") if la is not None and lo is not None else None
    M["n_images"] = n_img
    print(f"위성 사례: 지점 {len(M.get('sites', []))}개 · 영상 파일 {n_img}장 임베드")
    return M


def plotly_js():
    return open(os.path.join(os.path.dirname(plotly.__file__), "package_data", "plotly.min.js"), encoding="utf-8").read()


def main():
    D = build_data()
    html = TEMPLATE.replace("/*PLOTLY*/", plotly_js()).replace("/*DATA*/", json.dumps(D, ensure_ascii=False))
    with open(os.path.join(HERE, "demo.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print(f"demo.html 생성 ({len(html)/1e6:.1f} MB) · 서사 {len(D['nars'])}개")


TEMPLATE = r"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>FIMI 서사 조기경보</title>
<script>/*PLOTLY*/</script>
<style>
:root{--bg:#fafaf8;--panel:#fff;--ink:#1f1f1d;--muted:#6b6b66;--line:#e6e5df;--ord:#2a78d6;--sus:#eb6834;--src:#1baf7a}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:-apple-system,"Apple SD Gothic Neo","Noto Sans KR",sans-serif}
.wrap{display:grid;grid-template-columns:260px 1fr;min-height:100vh}
aside{background:#f1f0ec;padding:20px 18px;border-right:1px solid var(--line)}
aside h1{font-size:19px;margin:0 0 4px}aside .cap{font-size:12px;color:var(--muted);margin-bottom:18px}
main{padding:22px 28px;max-width:1200px}
input[type=range]{width:100%}.now{font-weight:700;margin:8px 0 18px}
.nar{padding:8px 10px;border-radius:8px;margin-bottom:6px;cursor:pointer;border:1px solid transparent}
.nar.sel{background:#fff;border-color:var(--line)}.nar small{color:var(--muted);display:block;margin-top:2px}
.kpis{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin:14px 0}
.chips{display:flex;gap:8px;flex-wrap:wrap}.chip{flex:1;min-width:120px;border:1.5px solid var(--line);border-radius:10px;padding:8px 10px;background:#fff}
.chip b{display:block;font-size:12px}.chip span{font-size:13px}.lad{display:flex;align-items:center;gap:8px;margin:3px 0;font-size:13px}
.lad .lv{width:26px;font-weight:700}.lad .st{font-size:12px;padding:1px 8px;border-radius:10px;font-weight:700}.lad .nt{width:42%;font-size:12px;color:var(--muted)}
.quote{font-size:15px;line-height:1.7;margin:6px 0;padding:10px 12px;border-left:3px solid #6c4ad6;background:#faf9ff}
.ftbl td{border:0;padding:3px 8px 3px 0;font-size:13px}.ftbl td:first-child{color:var(--muted);white-space:nowrap}
.cbar{height:8px;background:#f0efe9;border-radius:4px;margin-top:3px}.cbar div{height:8px;border-radius:4px}
.cmpw{position:relative;width:100%;max-width:760px;aspect-ratio:16/9;background:#000;border-radius:10px;overflow:hidden;border:1px solid var(--line)}
.cmpw img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;display:block}.cmpw .after{clip-path:inset(0 0 0 50%)}
.cmpw .div{position:absolute;top:0;bottom:0;width:2px;background:#fff;left:50%;box-shadow:0 0 6px rgba(0,0,0,.6)}
.cmpw .lab{position:absolute;top:8px;font-size:11px;padding:2px 7px;border-radius:6px;background:rgba(0,0,0,.55);color:#fff}.cmpw .lab.l{left:8px}.cmpw .lab.r{right:8px}
.cmpw input{position:absolute;inset:0;width:100%;height:100%;opacity:0;cursor:ew-resize;margin:0}
.cmpw .ph{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;text-align:center;padding:14px 18px;font-size:12px;line-height:1.55;color:var(--muted);background:#f6f5f0}.cmpw .ph code{display:block;font-size:11px;color:var(--ink);word-break:break-all;margin:4px 0}
.sattabs{display:flex;gap:6px;flex-wrap:wrap;margin:6px 0 8px}.sattabs button{padding:4px 9px;font-size:11.5px;border:1px solid var(--line);border-radius:8px;background:#fff;cursor:pointer}.sattabs button.on{background:#1f1f1d;color:#fff;border-color:#1f1f1d}
.kpi{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.kpi .l{font-size:12px;color:var(--muted)}.kpi .v{font-size:26px;font-weight:600;margin-top:4px}
.row{display:grid;grid-template-columns:1fr 1fr;gap:12px}.box{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:8px}
h2{font-size:17px;margin:24px 0 8px}.card{display:grid;grid-template-columns:3fr 2fr;gap:16px}
.card ul{margin:4px 0 10px;padding-left:18px}.card li{margin:3px 0;font-size:14px}.muted{color:var(--muted);font-size:13px}
.info{background:#eef4fc;border-radius:8px;padding:12px 14px;color:#1c5cab}
table{border-collapse:collapse;width:100%;font-size:12px}td,th{border-bottom:1px solid var(--line);padding:4px 6px;text-align:left}
details{margin-top:10px}.foot{margin-top:28px;border-top:1px solid var(--line);padding-top:10px}
.play{margin-top:8px;padding:6px 10px;border:1px solid var(--line);background:#fff;border-radius:6px;cursor:pointer}
body.cmd main>*:not(#head):not(#samples):not(#cmdbox):not(.foot){display:none}#cmdbox{display:none}body.cmd #cmdbox{display:block}
.jsel{font-size:12px;padding:2px 4px;border:1px solid var(--line);border-radius:6px;background:#fff;margin-left:6px}
.btn{padding:6px 10px;border:1px solid var(--line);background:#fff;border-radius:6px;cursor:pointer;font-size:12px}.btn.pri{background:#1f1f1d;color:#fff;border-color:#1f1f1d}
pre.brief{white-space:pre-wrap;font-size:12.5px;line-height:1.55;background:#fff;border:1px solid var(--line);border-radius:8px;padding:12px 14px;max-height:520px;overflow:auto}
@media(max-width:800px){.wrap{grid-template-columns:1fr}.kpis{grid-template-columns:1fr 1fr}.row,.card{grid-template-columns:1fr}main{padding:16px}}
</style></head><body>
<div class="wrap"><aside>
<h1>FIMI 서사 조기경보</h1><div class="cap">합성 데이터 시연 · 모든 계정·매체는 가상 · 계정은 가명 ID<br>오프라인 백업 화면</div>
<label class="muted">관측 시각 (시작 후 시간): <b id="hl"></b></label>
<input id="hs" type="range" min="1" step="1"><button class="play" id="play">▶ 자동 재생</button>
<div class="now" id="now"></div>
<div class="muted" style="margin-bottom:4px">판단 기준</div>
<label style="display:block;margin-bottom:2px"><input type="radio" name="mode" value="beh" checked> 행동 (우리 방식)</label>
<label style="display:block;margin-bottom:10px"><input type="radio" name="mode" value="cont"> 내용 (비교용)</label>
<div class="muted" style="margin-bottom:4px">화면</div>
<label style="display:inline-block;margin-right:8px"><input type="radio" name="role" value="an" checked> 분석관</label><label style="display:inline-block;margin-bottom:14px"><input type="radio" name="role" value="cmd"> 지휘관</label>
<div class="muted" style="margin-bottom:6px">서사별 현재 단계</div><div id="narlist"></div>
</aside><main>
<div id="head"></div><div class="muted" id="samples"></div><div id="cmdbox"></div>
<div class="kpis" id="kpis"></div><div id="cmp"></div>
<div class="row"><div class="box"><div id="c1"></div></div><div class="box"><div id="c2"></div></div></div>
<details style="margin-top:12px"><summary>단순 볼륨 감시와 비교 — 서사별 (지금 시각 기준)</summary><div id="voltbl"></div></details>
<h2>확산 경로 — 외국어 출처에서 일반 사용자까지</h2><div class="box"><div id="c3"></div></div>
<div class="muted" style="margin-top:6px">일반 사용자는 개별 계정이 아니라 시간·단계별 집계 노드로만 표시합니다. 개별 가명 ID는 행동 기준 의심 계정에만 보입니다.</div>
<h2>근거 카드</h2><div id="pol"></div><div id="card"></div><div id="briefwrap"></div>
<div id="prewrap"><h2>전조 카드 — 공식 신호 · 명분 서사 · 은밀 증폭의 정합성</h2>
<div class="muted">회색지대 도발은 행동 전에 정보 환경이 먼저 준비된다는 가설을 네 축으로 나눠 봅니다. 축 A·B는 가상 자료(합성), 축 C는 위 탐지 결과 그대로, 축 D(항만·선박·위성)는 연결 인터페이스만 둡니다. 말의 양을 세지 않고 발언의 구조(조건·시한·장소·수단·톤)를 뽑으며, 원문 인용이 없는 필드는 채우지 않습니다.</div>
<div class="box" style="margin-top:10px"><div id="pc"></div></div>
<div class="muted" style="margin-top:6px">◆ 공식 발언(크기 = 수준 L1~L3, 빈 마름모 = 완화 톤) · ● 명분 ▲ 피해 ■ 동원 서사 · 사각형 색 = 축 C 경보 단계 · 아래 띠: 보라 = 수사 단독, 빨강 = 수렴, 자주 = 불일치</div>
<div class="card" style="margin-top:12px"><div class="box" style="padding:14px 16px" id="pcard"></div><div><div class="box" style="padding:12px 14px" id="pstmt"></div><div class="box" style="padding:12px 14px;margin-top:12px" id="pcases"></div></div></div>
<details><summary>축 B — 외국어 서사 항목 (지금까지 관측, 규칙 기반 분류)</summary><div id="pitems"></div></details>
<details><summary>과거 사례 라이브러리 — 공개 보도 기준 7건 (선행 4 · 반례 2 · 오경보 1)</summary><div id="plib"></div><div class="muted" style="margin-top:6px">날짜·선행 일수는 보도 날짜 차이입니다. 사례 수가 적어 정확도를 주장하지 않고, 구조 일치 사례의 선행 범위만 참고합니다.</div></details>
<details id="satwrap"><summary>축 D 물리 전조 — 실제 공개 위성영상 사례 (Copernicus Sentinel-2 · 역사 사례 · 시스템 분석 아님)</summary><div id="satbody" style="margin-top:8px"></div></details>
<details id="rpwrap"><summary>역사 재생 — 실제 공개 담화에 같은 규칙을 돌리면? (10건 · 작동 확인, 정확도 주장 아님)</summary><div id="rpsum" style="font-size:14px;margin:8px 0"></div>
<div style="margin:6px 0"><label><input type="radio" name="rptag" value="v2" checked> v2 (실제 담화를 보고 고친 규칙)</label> &nbsp; <label><input type="radio" name="rptag" value="v1"> v1 (합성 문장만 보고 만든 규칙)</label></div>
<div class="box"><div id="rpfig"></div></div><div id="rptbl" style="margin-top:8px;overflow-x:auto"></div><div id="rpnotes" style="font-size:13px;margin-top:8px"></div></details>
<div class="muted" id="psum" style="margin-top:8px"></div></div>
<h2>증거 봉인</h2><div id="seal"></div>
<details style="margin-top:14px"><summary>민감도 분석 — 가정값을 바꿔도 결론이 유지되는가</summary><div id="sens"></div></details>
<div id="redwrap"><h2>회피 내성 — 공격자가 게시 시각을 흩뜨리면?</h2>
<div class="muted">위 탐지(burst 층)는 '짧은 시간에 몰린 게시'를 봅니다. 공작자가 시각만 흩뜨리면 어떻게 되는지, 그리고 시각과 무관하게 '무엇을 함께 미는가'를 보는 제2 신호층(URL 공유 네트워크)이 얼마나 받쳐 주는지를 공격자 정교함 7단계로 쟀습니다. 합성 데이터(정상 속보 대조군 포함) · 변형당 시드 3개 평균 · 서사 배정은 정답 라벨로 고정(burst 층에 유리한 조건).</div>
<div style="margin:10px 0 6px;font-size:13px;color:var(--muted)">공격자 정교함 (왼쪽 → 오른쪽으로 갈수록 회피에 능숙)</div><div id="redbtns" style="display:flex;gap:6px;flex-wrap:wrap"></div>
<div class="card" style="margin-top:10px"><div><div class="kpis" style="grid-template-columns:repeat(4,1fr)" id="redkpi"></div><div class="box"><div id="redcurve"></div></div></div>
<div><div class="box"><div id="rednet"></div></div><div class="muted" id="rednote" style="margin-top:6px"></div></div></div>
<div style="margin-top:10px"><b>읽는 법</b><ul id="redfind" style="font-size:14px"></ul></div>
<div class="card" id="redira" style="margin-top:6px"></div>
<details><summary>규칙·가정·격자 — 결과를 본 뒤 바꾼 것까지</summary><div id="redrule"></div></details></div>
<div id="realwrap"></div>
<div class="foot muted">이 화면은 판정이 아니라 분석가 보조 자료입니다. 최종 판단은 분석가가 합니다. 합성 데이터 · 실존 개인/계정 없음 · 개인 식별·표적화 기능 없음.</div>
</main></div>
<script>
const D=/*DATA*/;
const LV={NONE:["·","#8a8a85","경보 없음"],REVIEW:["◇","#8a8a85","검토 권장"],WATCH:["●","#e0a000","관찰"],ALERT:["▲","#ec835a","경보"],CRITICAL:["■","#d03b3b","위험"]};
const C={ord:"#2a78d6",sus:"#eb6834",src:"#1baf7a"};
const badge=l=>`<span style="color:${LV[l][1]};font-weight:700">${LV[l][0]} ${l}</span> <span class="muted">${LV[l][2]}</span>`;
const t0=new Date(D.t0.replace(" ","T"));
const fmt=h=>{const d=new Date(t0.getTime()+h*3600e3);const p=n=>String(n).padStart(2,"0");return `${p(d.getMonth()+1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`};
const nids=Object.keys(D.nars);let sel=nids[0];let H=13;let MODE="beh";let ROLE="an";
// ---- 분석관 판정 상태 (브라우저 메모리 · 새로고침하면 사라짐 · 내려받기로 보존)
const JUD={},JREC=[];let BRIEF_OPEN=false;
function sha256(str){const K=[0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2];
  let H0=[0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19];const b=new TextEncoder().encode(str);const l=b.length;const n=((l+9+63)>>6)<<6;const m=new Uint8Array(n);m.set(b);m[l]=0x80;const dv=new DataView(m.buffer);dv.setUint32(n-4,(l*8)>>>0);dv.setUint32(n-8,Math.floor(l*8/4294967296));
  const w=new Uint32Array(64);const rr=(x,k)=>(x>>>k)|(x<<(32-k));
  for(let i=0;i<n;i+=64){for(let t=0;t<16;t++)w[t]=dv.getUint32(i+t*4);for(let t=16;t<64;t++){const s0=rr(w[t-15],7)^rr(w[t-15],18)^(w[t-15]>>>3),s1=rr(w[t-2],17)^rr(w[t-2],19)^(w[t-2]>>>10);w[t]=(w[t-16]+s0+w[t-7]+s1)>>>0}
    let [a,bb,c,d,e,f,g,h]=H0;for(let t=0;t<64;t++){const S1=rr(e,6)^rr(e,11)^rr(e,25),ch=(e&f)^(~e&g),t1=(h+S1+ch+K[t]+w[t])>>>0,S0=rr(a,2)^rr(a,13)^rr(a,22),mj=(a&bb)^(a&c)^(bb&c),t2=(S0+mj)>>>0;h=g;g=f;f=e;e=(d+t1)>>>0;d=c;c=bb;bb=a;a=(t1+t2)>>>0}
    H0=[a,bb,c,d,e,f,g,h].map((x,k)=>(x+H0[k])>>>0)}
  return H0.map(x=>x.toString(16).padStart(8,"0")).join("")}
const canon=o=>JSON.stringify(Object.keys(o).sort().reduce((r,k)=>(r[k]=o[k],r),{}));   // python json.dumps(sort_keys) 와 같은 직렬화는 아니므로 체인은 화면 안에서만 검증
const excludedOf=n=>new Set(Object.entries(JUD).filter(([k,v])=>k.startsWith(n+":")&&v.j==="normal").map(([k])=>+k.split(":")[1]));
function joinedEff(N,n,a){const ex=excludedOf(n);if(!ex.size)return N.joined[a];const ab=N.ab[String(a)];if(!ab)return undefined;const ends=ab.filter(x=>!ex.has(x[0])).map(x=>x[1]).sort((p,q)=>p-q);return ends.length>=2?ends[1]:undefined}
function judge(bi,j){const key=sel+":"+bi;if(!j){delete JUD[key];render();return}const why=(document.getElementById("jwhy")||{}).value||"";
  const prev=JREC.length?JREC[JREC.length-1].record_sha256:D.an.chain_end;
  const body={kind:"analyst_judgment",narrative_id:+sel,hour:H,burst_id:bi,judgment:j,judgment_label:D.an.judgments[j][0],reason:why.slice(0,300),role:D.an.role,recorded_at:new Date().toISOString().slice(0,19)+"Z",prev};
  body.record_sha256=sha256(canon(body));JUD[key]={j,why,rec:body};JREC.push(body);render()}
function clearJud(){for(const k in JUD)delete JUD[k];JREC.length=0;render()}
function verifyRecs(){let prev=D.an.chain_end;for(const r of JREC){if(r.prev!==prev)return[false,"연결 끊김"];const b={...r};delete b.record_sha256;if(sha256(canon(b))!==r.record_sha256)return[false,"해시 불일치"];prev=r.record_sha256}return[true,`기록 ${JREC.length}건 · 체인 끝 ${prev.slice(0,12)}…`]}
function dl(name,text,type){const a=document.createElement("a");a.href=URL.createObjectURL(new Blob([text],{type:type||"text/plain"}));a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),2000)}
const hs=document.getElementById("hs");hs.max=D.max_h;hs.value=H;
const lvAt=(n,h)=>{const r=D.nars[n].r.find(x=>x.h===h);return r?r.level:"NONE"};
const base={paper_bgcolor:"#fff",plot_bgcolor:"#fff",margin:{l:40,r:10,t:40,b:40},font:{family:"-apple-system,Apple SD Gothic Neo,sans-serif",size:12}};
const cfg={displayModeBar:false,responsive:true};
function render(){
  const h=H,N=D.nars[sel],rr=N.r.find(x=>x.h===h)||{r:null,n_susp:0,n_sofar:0,level:"NONE"},lv=rr.level;
  document.getElementById("hl").textContent=h;document.getElementById("now").innerHTML="현재 시각 "+fmt(h);
  document.getElementById("narlist").innerHTML=nids.map(n=>`<div class="nar ${n===sel?"sel":""}" data-n="${n}">N${n} ${badge(lvAt(n,h))}<small>${D.nars[n].samples[0].slice(0,26)}…</small></div>`).join("");
  document.querySelectorAll(".nar").forEach(e=>e.onclick=()=>{sel=e.dataset.n;render()});
  const isSusBeh=a=>{const j=joinedEff(N,sel,a);return j!=null&&j<=h};
  const said=new Set(N.posts.filter(p=>p[3]==="ko"&&p[0]<h).map(p=>p[2]));
  document.body.classList.toggle("cmd",ROLE==="cmd");
  const isSus=MODE==="cont"?(a=>said.has(a)):isSusBeh;
  const nBeh=[...said].filter(isSusBeh).length;
  document.getElementById("head").innerHTML=`<h2 style="margin-top:0;font-size:22px">N${sel} · ${badge(lv)}</h2>`;
  document.getElementById("samples").textContent="서사 예시: "+N.samples.slice(0,2).join(" / ");
  const fo=N.foreign.filter(f=>f.x<h);
  const k=[["일반 사용자 간 R̂",rr.r==null?"—":rr.r.toFixed(2)+(rr.p1==null?"":` <span class="muted" style="font-size:13px">P(R>1) ${Math.round(rr.p1*100)}%</span>`)],["의심 계정 ("+(MODE==="cont"?"내용 기준":"행동 기준")+")",[...said].filter(isSus).length],["이 서사 게시물(지금까지)",rr.n_sofar],["외국어 출처 연결",fo.length?fo.length+"건":"없음"],
    ["전조 정합성",(()=>{if(!D.pre||+sel!==D.pre.summary.campaign_narrative)return"—";const r=preRow(h);return `<span style="color:${PST[r.state][1]}">${PST[r.state][0]} ${r.state_label}</span> <span class="muted" style="font-size:13px">수렴 ${r.conv}/3축</span>`})()]];
  document.getElementById("kpis").innerHTML=k.map(([l,v])=>`<div class="kpi"><div class="l">${l}</div><div class="v">${v}</div></div>`).join("");
  document.getElementById("cmp").innerHTML=said.size?`<div class="info" style="${MODE==="cont"?"background:#fdf6e3;color:#8a6200":""}"><b>내용 기준</b>이면 이 서사를 말한 계정 <b>${said.size.toLocaleString()}개</b> 전부가 의심 대상 → <b>행동 기준</b>이면 <b>${nBeh}개</b>. 같은 주장을 하는 일반 시민을 공작으로 몰지 않기 위해 우리는 행동을 봅니다.</div>`:"";
  const vrows=Object.entries(D.vol).map(([n,v])=>{const ours=v.levels[h-1]||"NONE";return `<tr><td>N${n}</td><td>${v.sample.replace(/</g,"&lt;")}…</td><td>${v.vh==null?"경보 없음":(v.vh<=h?v.vh+"시 경보":"아직")}</td><td>${LV[ours][0]} ${ours}</td></tr>`}).join("");
  document.getElementById("voltbl").innerHTML=`<table style="margin-top:8px"><tr><th>서사</th><th>예시</th><th>볼륨 감시</th><th>우리 단계</th></tr>${vrows}</table><div class="muted" style="margin-top:6px">단순 볼륨 감시 = 시간당 게시물 20건 이상이면서 직전 24시간 중앙값의 3배 이상. 볼륨 감시는 빨리 울리지만 자연 바이럴에도 울린다. 우리의 장점은 속도가 아니라 구분력이다.</div>`;
  // 차트1 볼륨
  const ord=Array(D.max_h+1).fill(0),sus=Array(D.max_h+1).fill(0);
  N.posts.forEach(p=>{if(p[3]!=="ko"||p[0]>=h)return;const b=Math.floor(p[0]);(isSus(p[2])?sus:ord)[b]++});
  const xs=[...Array(D.max_h+1).keys()];
  const shapes=N.bursts.filter(b=>b.e<h).map(b=>({type:"rect",xref:"x",yref:"paper",x0:b.s-.4,x1:b.e+.4,y0:0,y1:1,fillcolor:"#8a8a85",opacity:.12,line:{width:0}}));
  shapes.push({type:"line",xref:"x",yref:"paper",x0:h,x1:h,y0:0,y1:1,line:{dash:"dot",color:"#6b6b66"}});
  const vh=(D.vol[sel]||{}).vh;const anns=[];
  if(vh!=null&&vh<=h){shapes.push({type:"line",xref:"x",yref:"paper",x0:vh,x1:vh,y0:0,y1:1,line:{color:"#8a8a85",width:1.5}});
    anns.push({x:vh,xref:"x",y:1,yref:"paper",yanchor:"bottom",xanchor:"left",text:"단순 볼륨 경보",showarrow:false,font:{size:11,color:"#6b6b66"}})}
  Plotly.react("c1",[{type:"bar",x:xs,y:ord,name:"일반 사용자",marker:{color:C.ord},hovertemplate:"%{x}시 · 일반 사용자 %{y}건<extra></extra>"},
    {type:"bar",x:xs,y:sus,name:"의심 집단",marker:{color:C.sus},hovertemplate:"%{x}시 · 의심 집단 %{y}건<extra></extra>"}],
    {...base,height:290,barmode:"stack",bargap:.15,title:{text:"시간당 게시물 (회색 띠 = 동시 게시 burst)",font:{size:14}},shapes,annotations:anns,
     legend:{orientation:"h",y:-.28,x:0},xaxis:{range:[0,D.max_h],title:"시작 후 시간"},yaxis:{gridcolor:"#eee"}},cfg);
  // 차트2 R
  const rs=N.r.filter(x=>x.h<=h),mx=Math.max(1.6,...rs.map(x=>x.hi||0))+.1;
  const rb=rs.filter(x=>x.lo!=null);
  Plotly.react("c2",[{x:rb.map(x=>x.h).concat(rb.map(x=>x.h).reverse()),y:rb.map(x=>x.hi).concat(rb.map(x=>x.lo).reverse()),fill:"toself",fillcolor:"rgba(42,120,214,0.15)",line:{width:0},hoverinfo:"skip"},
    {x:rs.map(x=>x.h),y:rs.map(x=>x.r),mode:"lines+markers",line:{color:C.ord,width:2},marker:{size:6},
     customdata:rs.map(x=>[x.lo,x.hi,x.p1]),hovertemplate:"%{x}시 · R̂ %{y:.2f} (80% %{customdata[0]:.2f}~%{customdata[1]:.2f}) · P(R>1) %{customdata[2]:.0%}<extra></extra>"}],
    {...base,height:290,showlegend:false,title:{text:"일반 사용자 간 R̂ · 파란 띠 = 80% 구간",font:{size:14}},
     shapes:[{type:"rect",xref:"paper",x0:0,x1:1,y0:D.r_alert,y1:1,fillcolor:"#ec835a",opacity:.12,line:{width:0}},
             {type:"line",xref:"paper",x0:0,x1:1,y0:1,y1:1,line:{color:"#d03b3b",width:1}},
             {type:"line",x0:h,x1:h,yref:"paper",y0:0,y1:1,line:{dash:"dot",color:"#6b6b66"}}],
     annotations:[{xref:"paper",x:0,y:1,yanchor:"bottom",xanchor:"left",text:"R=1 자생 확산",showarrow:false,font:{size:11,color:"#d03b3b"}}],
     xaxis:{range:[0,D.max_h],title:"시작 후 시간"},yaxis:{range:[0,mx],gridcolor:"#eee"}},cfg);
  // 차트3 경로
  const vis=N.posts.map((p,i)=>[p,i]).filter(([p])=>p[0]<h);
  const ex=[],ey=[],ux=[],uy=[];const srcIdx=N.posts.map((p,i)=>[p,i]).filter(([p])=>p[3]!=="ko"&&p[0]<h);
  const XY=p=>(p[3]==="ko"&&!isSusBeh(p[2]))?[Math.floor(p[0])+.5,Math.round(p[1])]:[p[0],p[1]];
  vis.forEach(([p])=>{if(p[4]>=0&&N.posts[p[4]][0]<h){const a=XY(N.posts[p[4]]),b=XY(p);ex.push(a[0],b[0],null);ey.push(a[1],b[1],null)}});
  const grp=p=>p[3]!=="ko"?"외국어 출처":(isSus(p[2])?"의심 집단":"일반 사용자");
  // 부모 없이 원문 URL을 단 게시물 → 그 이전의 가장 최근 외국어 출처와 점선 연결
  vis.forEach(([p])=>{if(p[5]&&srcIdx.length){const q=srcIdx.reduce((a,[s])=>(s[0]<p[0]&&(!a||s[0]>a[0]))?s:a,null)||srcIdx[0][0];ux.push(q[0],p[0],null);uy.push(q[1],p[1],null)}});
  const tr=[{x:ux,y:uy,mode:"lines",line:{color:C.src,width:1,dash:"dot"},opacity:.5,hoverinfo:"skip",name:"출처 URL 공유"},
            {x:ex,y:ey,mode:"lines",line:{color:"#b5b4ad",width:1},opacity:.6,hoverinfo:"skip",name:"리포스트·답글 관계"}];
  [["일반 사용자",C.ord],["의심 집단",C.sus],["외국어 출처",C.src]].forEach(([nm,col])=>{const d=vis.filter(([p])=>grp(p)===nm).map(([p])=>p);
    const ind=d.filter(p=>p[3]!=="ko"||isSusBeh(p[2])), agg=d.filter(p=>p[3]==="ko"&&!isSusBeh(p[2]));
    if(ind.length) tr.push({x:ind.map(p=>p[0]),y:ind.map(p=>p[1]),mode:"markers",name:nm,marker:{color:col,size:nm==="외국어 출처"?11:8,line:{color:"#fff",width:1}},
      text:ind.map(p=>N.accounts[p[2]]+" · "+p[3]+"<br>"+p[6]),hovertemplate:"%{text}<extra>"+nm+"</extra>"});
    if(agg.length){const m={};agg.forEach(p=>{const k=(Math.floor(p[0])+.5)+"|"+Math.round(p[1]);m[k]=(m[k]||0)+1});
      const ks=Object.keys(m);tr.push({x:ks.map(k=>+k.split("|")[0]),y:ks.map(k=>+k.split("|")[1]),mode:"markers",name:nm+" (집계)",
        marker:{color:col,size:ks.map(k=>6+3*Math.sqrt(m[k])),opacity:.75,line:{color:"#fff",width:1}},customdata:ks.map(k=>m[k]),
        hovertemplate:"일반 사용자 %{customdata}건 (집계 · 개별 계정 표시 안 함)<extra></extra>"})}});
  Plotly.react("c3",tr,{...base,height:380,margin:{l:50,r:10,t:10,b:40},legend:{orientation:"h",y:-.18},
    xaxis:{range:[0,D.max_h],title:"시작 후 시간"},yaxis:{title:"출처로부터 단계(0=외국어 원문)",gridcolor:"#eee",dtick:1}},cfg);
  // 대응 단계 권고
  const AS={0:["○","#8a8a85"],1:["●","#2a78d6"],2:["◆","#e0a000"],3:["▲","#ec835a"],4:["■","#d03b3b"]};
  const pr=(N.pol||[]).find(x=>x.h===h), pel=document.getElementById("pol");
  if(pr&&(pr.a>0||lv!=="NONE")){const [ic,co]=AS[pr.a]||["·","#8a8a85"];
    pel.innerHTML=`<div class="box" style="padding:14px 16px;margin-bottom:12px"><div class="muted">대응 단계 권고 (분석관 보조 · 최종 결정은 사람)</div>
    <div style="font-size:21px;font-weight:700;color:${co};margin:2px 0 8px">${ic} ${pr.al}${pr.st?' <span class="muted" style="font-weight:400">· 이전 단계 유지(해제는 분석관)</span>':''}</div>
    <div class="card" style="gap:12px"><div style="font-size:14px"><b>확산 단계</b> ${pr.sl}<br><b>출처 귀속</b> ${pr.attr}<br><b>왜 지금</b> ${pr.now}<br><b>왜 이 수준</b> ${pr.lvl}</div>
    <div style="font-size:14px">${pr.dn.length?`<b>하지 말 것</b><ul>${pr.dn.map(x=>`<li>${x}</li>`).join("")}</ul>`:""}<b>다음 재평가</b> ${pr.esc}</div></div>
    ${pr.nt.length?`<div class="muted" style="margin-top:8px">${pr.nt.join(" · ")}</div>`:""}<div class="muted">신뢰도 ${pr.cf.toFixed(2)} · 판정이 아니라 분석관 보조</div></div>`;}
  else pel.innerHTML="";
  // 근거 카드
  const el=document.getElementById("card");
  if(lv==="NONE"){el.innerHTML='<div class="info">이 시각에는 경보가 없습니다. 반복 조정 집단이 확인되면 카드가 생성됩니다.</div>';}
  else{
    const cur=Object.entries(N.scores).filter(([a])=>isSusBeh(+a)).map(([,v])=>v);
    const mean=i=>cur.length?cur.reduce((s,v)=>s+v[i],0)/cur.length:0;
    const coord=mean(0),rv=rr.r==null?0:Math.min(rr.r,1),cv=.4*coord+.3*(fo.length?1:0)+.3*rv,conf=cv>=.7?"높음":cv>=.45?"중간":"낮음";
    const koX=N.posts.filter(p=>p[3]==="ko"&&p[0]<h).map(p=>p[0]),firstKo=koX.length?Math.min(...koX):null;
    const bb=N.bursts.filter(b=>b.e<h),mb=mean(3);
    const RA=reassess(N,sel,h,lv,fo.length>0);
    let trend="";const w=N.r.filter(x=>x.h<=h&&x.h>h-12&&x.r!=null);
    if(w.length>=4&&rr.r!=null){const n=w.length,sx=w.reduce((s,x)=>s+x.h,0),sy=w.reduce((s,x)=>s+x.r,0),sxx=w.reduce((s,x)=>s+x.h*x.h,0),sxy=w.reduce((s,x)=>s+x.h*x.r,0);
      const sl=(n*sxy-sx*sy)/(n*sxx-sx*sx);trend=` · 최근 12시간 추세 시간당 ${sl>=0?"+":""}${sl.toFixed(3)}`+(sl>0&&rr.r<1?` → 약 <b>${Math.round((1-rr.r)/sl)}시간 뒤 1 도달 (추정)</b>`:"")}
    const rows=Object.entries(N.scores).filter(([,v])=>v[4]!=="normal").sort((a,b)=>b[1][0]-a[1][0]);
    el.innerHTML=`<div class="card"><div>
      <div><b>단계</b> ${badge(lv)} · <b>신뢰도</b> ${conf} (${cv.toFixed(2)})</div>
      ${rr.dom?`<div class="info" style="background:#fdf6e3;color:#8a6200;margin-top:8px"><b>국내 사안 — 군 관할 아님.</b> 반복 조정 행위는 보이지만 외국어 출처가 연결되지 않았습니다. 경보 단계를 올리지 않으며, 필요 시 관계 기관 이관을 검토합니다.</div>`:(fo.length?`<div class="muted">관할: 외국발 서사 유입 — 탐지 대상</div>`:"")}
      ${fo.length?`<div style="margin-top:10px"><b>출처 (외국어 원문 → 한국어)</b><ul>${fo.map(f=>`<li><code>${f.lang}</code> ${f.ts} · ${f.url}${firstKo!=null&&firstKo>f.x?` · 한국어 첫 게시보다 <b>${(firstKo-f.x).toFixed(1)}시간 앞섬</b>`:""}</li>`).join("")}</ul></div>`:""}
      <div><b>동시 게시 burst ${bb.length}회</b> <span class="muted">· 오른쪽 선택 = 분석관 판정(체인 기록 · 근거 재집계)</span><ul>${bb.map(b=>{const jj=JUD[sel+":"+b.id];const jc={normal:"#2a78d6",confirmed:"#1baf7a",hold:"#e0a000"};return `<li>${b.start}–${b.end} · 계정 ${b.n}개 · 문장 유사도 ${b.sim.toFixed(2)}${b.url?" · URL "+b.url:""}${jj?` · <span style="color:${jc[jj.j]};font-weight:700">분석관 판정: ${D.an.judgments[jj.j][0]}</span>`:""}<select class="jsel" onchange="judge(${b.id},this.value)"><option value="">판정 —</option>${Object.entries(D.an.judgments).map(([k,v])=>`<option value="${k}" ${jj&&jj.j===k?"selected":""}>${v[0]}</option>`).join("")}</select></li>`}).join("")}</ul>
      <div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin:2px 0 8px"><input id="jwhy" placeholder="판정 근거 한 줄 (보고서에 그대로 들어감)" style="flex:1;min-width:220px;font-size:12px;padding:5px 8px;border:1px solid var(--line);border-radius:6px" value="${esc((JREC[JREC.length-1]||{}).reason||"")}">${JREC.length?`<button class="btn" onclick="dl('analyst_judgments.jsonl',JREC.map(r=>JSON.stringify(r)).join('\\n'),'application/json')">판정 기록 내려받기</button><button class="btn" onclick="clearJud()">초기화</button>`:""}</div>
      ${JREC.length?(()=>{const [ok,msg]=verifyRecs();return `<div class="muted">${ok?"✅":"❌"} 판정 체인 ${msg} · 증거 체인 끝 ${D.an.chain_end.slice(0,12)}…에 이어 붙임 · 역할은 가명</div>`})():""}</div>
      <div><b>의심 집단</b> 반복 조정 ${cur.length}개 계정 · 평균 burst 참여 ${mb.toFixed(1)}회${lv==="REVIEW"?` · 1회성 대규모 동시 게시 계정 ${N.n_review}개(검토 권장)`:""}${RA.removed.length?` · <span style="color:#2a78d6">판정 반영: ${RA.n_before} → ${RA.n_after}개</span>`:""}</div>
      ${RA.removed.length?`<div class="info" style="${RA.watch_met?"":"background:#fdf6e3;color:#8a6200"};margin:6px 0">${RA.note}</div>`:""}
      <div class="muted">신뢰도 = 0.4×집단 조정 점수 + 0.3×외국어 출처 연결 + 0.3×min(R̂,1). 가중치는 가정값입니다.</div>
      ${rr.r!=null?`<div style="margin-top:8px"><b>R̂ ${rr.r.toFixed(2)}</b> (80% 구간 ${rr.lo.toFixed(2)}~${rr.hi.toFixed(2)}) · <b>P(R>1) ${Math.round(rr.p1*100)}%</b> · P(R>0.8) ${Math.round(rr.p08*100)}%${trend}</div>`:""}
      ${(()=>{const on={burst:bb.length>=1,copypasta:bb.length&&Math.max(...bb.map(b=>b.sim))>=.5,url:mean(2)>=.5,young:mean(1)>=.5,foreign:fo.length>0&&bb.length>=1};
        const c=D.disarm.filter(d=>on[d.key]);return c.length?`<div style="margin-top:10px"><b>DISARM 후보 기법</b> <span class="muted">(신호와 기법의 연결은 해석이며 최종 태깅은 분석관)</span><ul>${c.map(d=>`<li><code>${d.id}</code> ${d.name} — ${d.why}</li>`).join("")}</ul></div>`:""})()}
      <div style="margin-top:10px"><b>탐지 단계별 기본 조치</b> <span class="muted">(대응 수위는 위 권고를 따름)</span><ul>${(D.actions[lv]||[]).map(x=>`<li>${x}</li>`).join("")}</ul></div>
      ${D.urlnet?`<div style="margin-top:10px"><b>제2 신호층 (URL 공유 네트워크)</b> <span class="muted">${D.urlnet.n_urls<10?`판정 보류 — 이 시나리오에는 링크가 ${D.urlnet.n_urls}개뿐이라 검정력이 없다(의심 묶음 ${D.urlnet.flagged_components}). 시각을 흩뜨린 공격에 대한 보강은 아래 '회피 내성' 참고`:`의심 묶음 ${D.urlnet.flagged_components} · 계정 ${D.urlnet.n_flagged_accounts} (72시간 안 희귀 링크 2개 이상 함께 공유 · 대조군 우연 수준 ${Math.round(D.urlnet.null_flagged_mean||0)}개)`}</span></div>`:""}
    </div><div><div class="box"><div id="c4"></div></div><div class="muted" style="margin-top:6px">신호는 내용이 아니라 행동만 봅니다. 신호 하나만으로는 의심 집단이 되지 않습니다.</div></div></div>
    <details><summary>계정 근거 표 (${rows.length}개, 가명 ID)</summary><table><tr><th>계정</th><th>등급</th><th>지금</th><th>점수</th><th>계정 나이(일)</th><th>burst</th><th>근거</th></tr>
    ${rows.map(([a,v])=>`<tr><td>${N.accounts[+a]}</td><td>${v[4]}</td><td>${isSusBeh(+a)?"의심":"아직 아님"}</td><td>${v[0].toFixed(2)}</td><td>${v[5]}</td><td>${v[3]}</td><td>${v[6]}</td></tr>`).join("")}</table></details>`;
    Plotly.react("c4",[{type:"bar",orientation:"h",x:[mean(1),Math.min(mb/2,1),mean(2)],y:["신생 계정","반복 burst","동일 URL"],
      marker:{color:C.sus},text:[mean(1).toFixed(2),mb.toFixed(1)+"회",mean(2).toFixed(2)],textposition:"outside",hoverinfo:"skip"}],
      {...base,height:210,margin:{l:80,r:40,t:34,b:10},title:{text:"의심 집단의 신호 (평균)",font:{size:13}},xaxis:{range:[0,1.3],visible:false}},cfg);
  }
  renderBrief(N,h,lv,fo,isSusBeh);
  renderPre(h);
  document.getElementById("seal").innerHTML=`<div>${D.seal.ok?"✅":"❌"} ${D.seal.msg}</div><div class="muted">관찰·경보·위험 단계에 처음 들어선 시점마다(관찰 = 일반 시민 사이 자생 확산 전) 출처·시간 순서·게시물 해시를 묶어 체인으로 이어 기록합니다. 원본 한 글자라도 바뀌면 검증이 실패합니다(변조 탐지). 자체 보관 체인이라 내부 일관성만 증명하며, 외부 타임스탬프 연동은 다음 단계입니다.</div>`;
}
hs.oninput=()=>{H=+hs.value;render()};
document.querySelectorAll('input[name=mode]').forEach(r=>r.onchange=()=>{MODE=r.value;render()});
document.querySelectorAll('input[name=role]').forEach(r=>r.onchange=()=>{ROLE=r.value;render();window.scrollTo(0,0)});
let timer=null;document.getElementById("play").onclick=e=>{if(timer){clearInterval(timer);timer=null;e.target.textContent="▶ 자동 재생";return}
  e.target.textContent="■ 멈춤";timer=setInterval(()=>{H=H>=D.max_h?1:H+1;hs.value=H;render()},600)};
document.addEventListener("keydown",e=>{if(e.key==="ArrowRight"&&H<D.max_h){H++;hs.value=H;render()}if(e.key==="ArrowLeft"&&H>1){H--;hs.value=H;render()}});

// ---------------------------------------------------------------- 전조 카드 (축 A 공식 신호 · B 명분/동원 · C 은밀 증폭 · D 물리 전조)
const PAX={A:"#6c4ad6",B:"#0f9d8a",C:"#eb6834",D:"#9a9a94"};
const PLVC={NONE:"#d9d8d2",REVIEW:"#b5b4ad",WATCH:"#fab219",ALERT:"#ec835a",CRITICAL:"#d03b3b"};
const PST={none:["·","#8a8a85","신호 없음"],watch:["◇","#8a8a85","관찰"],rhetoric_only:["◆","#6c4ad6","수사 단독"],partial:["◐","#e0a000","부분 수렴"],converged:["●","#d03b3b","수렴"],mismatch:["⚡","#8e24aa","불일치"]};
const PWHY={none:"어느 축에도 신호가 없습니다.",watch:"한 축에 약한 신호만 있습니다. 카드는 만들지 않습니다.",
 rhetoric_only:"공식 발언(축 A)만 강하고 서사(축 B)·은밀 증폭(축 C)은 조용합니다. 과거 라이브러리에는 사건 없는 급등 사례가 있어 공식 축 단독으로는 경보하지 않습니다.",
 partial:"한 축만 기준을 넘었습니다. 다른 축의 변화를 기다립니다.",converged:"두 축 이상이 같은 방향입니다. 공개 발언의 예고 시간창과 은밀 증폭이 겹치는 구간입니다.",
 mismatch:"공식 발언은 완화됐는데 은밀 증폭은 오르고 있습니다. 말과 행동이 어긋나는 구간 — 공식 발언만 믿고 경계를 낮추지 않습니다."};
const PF={conditional:["조건부","#6c4ad6"],deadline:["시한","#d03b3b"],place:["장소","#0f9d8a"],means:["수단","#eb6834"],blame:["책임 전가","#8a8a85"],threat:["위협","#b23a48"],announce:["예고 서술어","#7a5c00"],soft:["완화","#2a78d6"]};
const PTONE={threat:"위협",soft:"완화",neutral:"중립",announce:"예고"},PRANK={1:"대변인",2:"차관급",3:"군 총참모부",4:"최고위"},PSYM={pretext:"circle",victim:"triangle-up",mobilization:"square",other:"x"};
const PLAD={"확인":"#1baf7a","부분":"#e0a000","미확인":"#b5b4ad","판단 불가":"#8a8a85"};
const esc=t=>String(t).replace(/&/g,"&amp;").replace(/</g,"&lt;");
const preRow=h=>D.pre.series.find(s=>s.h===h)||D.pre.series[0];
const baseStmt=h=>{const sa=D.pre.statements.filter(s=>s.h<=h);return sa.length?sa.reduce((a,s)=>(s.level>a.level||(s.level===a.level&&s.h>a.h))?s:a):null};
function reassess(N,n,h,lv,foreign){
  const before=Object.entries(N.joined).filter(([a,t])=>t<=h).length;
  const ex=excludedOf(n);let after=before;
  if(ex.size){after=Object.keys(N.ab).filter(a=>{const j=joinedEff(N,n,+a);return j!=null&&j<=h}).length}
  const met=after>=D.an.min_susp&&foreign;let note="판정 없음 — 시스템 근거 그대로";
  if(ex.size){if(["WATCH","ALERT","CRITICAL"].includes(lv)&&!met)note=`관찰 조건(의심 계정 ${D.an.min_susp}개 이상 + 외국어 출처) 미충족 → <b>단계 해제 검토</b>. 자동 하향은 없다 — 해제는 분석관이 결정한다`;
    else if(["ALERT","CRITICAL"].includes(lv))note="관찰 조건은 유지. 경보·위험 단계는 일반 사용자 간 R̂가 정하므로 burst 판정으로는 바뀌지 않는다";else note="관찰 조건 유지"}
  return {n_before:before,n_after:after,watch_met:met,note,removed:ex.size?[1]:[]}}
const f2=(x,nd=2)=>(x==null||isNaN(x))?"—":(+x).toFixed(nd);
function buildCtx(N,h,lv,fo,isSusBeh){
  const pr=(N.pol||[]).find(x=>x.h===h)||null,rr=N.r.find(x=>x.h===h)||{},koX=N.posts.filter(p=>p[3]==="ko"&&p[0]<h).map(p=>p[0]),firstKo=koX.length?Math.min(...koX):null;
  const bb=N.bursts.filter(b=>b.e<h),cur=Object.entries(N.scores).filter(([a])=>isSusBeh(+a)).map(([,v])=>v),mean=i=>cur.length?cur.reduce((s,v)=>s+v[i],0)/cur.length:0;
  const rv=rr.r==null?0:Math.min(rr.r,1),cv=.4*mean(0)+.3*(fo.length?1:0)+.3*rv,conf=(cv>=.7?"높음":cv>=.45?"중간":"낮음")+` (${cv.toFixed(2)})`;
  const on={burst:bb.length>=1,copypasta:bb.length&&Math.max(...bb.map(b=>b.sim))>=.5,url:mean(2)>=.5,young:mean(1)>=.5,foreign:fo.length>0&&bb.length>=1};
  let pre=null;if(D.pre&&+sel===D.pre.summary.campaign_narrative){const row=preRow(h),bs=baseStmt(h);const sa=D.pre.statements.filter(s=>s.h<=h&&s.level>=3&&s.deadline_hours);let win=null;
    if(sa.length){const s=sa[sa.length-1],[lo,hi]=s.deadline_hours;win=`${(s.fields.means||[]).join(" · ")||"수단 미명시(상응 조치)"} 가능성 · 장소 ${[...new Set(s.fields.place||[])].join(" · ")||"장소 미명시"} · 시한 '${s.fields.deadline[0]}' → ${fmt(s.h+lo)} ~ ${fmt(s.h+hi)} (발언 ${s.stmt_id} 기준)`}
    pre={state_label:row.state_label,conv:row.conv,note:{mismatch:"공식 발언 완화 + 은밀 증폭 상승 — 완화 발언을 근거로 경계를 낮추지 않는다",converged:"공개 발언의 예고 시간창과 은밀 증폭이 겹치는 구간"}[row.state]||"",a_text:bs?`${bs.stmt_id} ${bs.ts} · 수준 L${bs.level} (${bs.level_why})`:null,window:win}}
  return {nid:sel,now:fmt(h),hour:h,level:lv,level_name:LV[lv][2],policy:pr?{action_label:pr.al,stage_label:pr.sl,attribution:pr.attr,why_now:pr.now,why_level:pr.lvl,escalate_if:pr.esc}:null,
    foreign:fo.map(f=>({lang:f.lang,ts:f.ts,url:f.url,lead_h:firstKo!=null?firstKo-f.x:null})),
    bursts:bb.map(b=>({id:b.id,start:b.start,end:b.end,n:b.n,sim:b.sim,url:b.url||"",judgment:(JUD[sel+":"+b.id]||{}).j||null})),
    reassess:reassess(N,sel,h,lv,fo.length>0),r:rr.r==null?null:{r:rr.r,lo:rr.lo,hi:rr.hi,p1:rr.p1,p08:rr.p08},
    disarm:lv==="NONE"?[]:D.disarm.filter(d=>on[d.key]),pre,do_not:pr?pr.dn:[],confidence:conf,judgments:JREC.filter(r=>r.narrative_id===+sel),chain_end:D.an.chain_end}}
function briefingMd(c){const L=[],pol=c.policy||{},fo=c.foreign,bb=c.bursts,ra=c.reassess,lead=fo.filter(f=>f.lead_h!=null&&f.lead_h>0).map(f=>f.lead_h);
  L.push(`# 브리핑 초안 — 서사 N${c.nid} · ${c.now} (시작 후 ${c.hour}시)`,"시스템 생성 초안(규칙 기반 템플릿 · LLM 미사용) · 분석관 검토 전 · 판정이 아니라 보조 자료 · 합성 데이터 시연","","## 1. 요약");
  L.push(`- 탐지 단계 **${c.level} (${c.level_name})** · 대응 권고 **${pol.action_label||"—"}** · 카드 신뢰도 ${c.confidence}`);
  L.push(`- 외국어 원문 ${fo.length}건${lead.length?`(한국어 첫 게시보다 최대 ${Math.max(...lead).toFixed(1)}시간 앞섬)`:""} · 반복 동시 게시 burst ${bb.length}회 · 의심 계정 ${ra.n_after}개${ra.removed.length?`(판정 전 ${ra.n_before}개)`:""}`);
  if(c.pre)L.push(`- 전조 정합성 **${c.pre.state_label}** (수렴 ${c.pre.conv}/3축)${c.pre.note?" · "+c.pre.note:""}`);
  L.push("","## 2. 근거 (시각 t까지 알 수 있던 것만)");
  if(fo.length){L.push("**외국어 출처 → 한국어 유입**");fo.forEach(f=>L.push(`- \`${f.lang}\` ${f.ts} · ${f.url}${f.lead_h>0?` · ${f.lead_h.toFixed(1)}시간 선행`:""}`))}else L.push("- 외국어 출처 연결 없음 → 국내 사안(군 관할 아님)으로 분류, 단계 상향 없음");
  L.push("**조정 행위(동시 게시 burst)**");bb.forEach(b=>L.push(`- ${b.start}–${b.end} · 계정 ${b.n}개 · 문장 유사도 ${f2(b.sim)}${b.url?" · "+b.url:""}${b.judgment?" · 분석관 판정: "+D.an.judgments[b.judgment][0]:""}`));
  if(c.r)L.push(`**일반 사용자 간 확산** R̂ ${f2(c.r.r)} (80% 구간 ${f2(c.r.lo)}~${f2(c.r.hi)}) · P(R>1) ${Math.round((c.r.p1||0)*100)}% · P(R>0.8) ${Math.round((c.r.p08||0)*100)}%`);
  if(c.disarm.length)L.push("**DISARM 후보 기법** (후보이며 확정은 분석관): "+c.disarm.map(d=>`\`${d.id}\` ${d.name}`).join(", "));
  if(c.pre&&c.pre.a_text)L.push(`**공식 신호(축 A)** ${c.pre.a_text}`);if(c.pre&&c.pre.window)L.push(`**가능한 행동·시간창** ${c.pre.window}`);
  L.push("","## 3. 권고와 하지 말 것");
  if(c.policy){L.push(`- **${pol.action_label}** — 확산 단계 ${pol.stage_label} · 출처 귀속 ${pol.attribution}`);if(pol.why_now)L.push(`- 왜 지금: ${pol.why_now}`);if(pol.why_level)L.push(`- 왜 이 수준: ${pol.why_level}`)}
  if(c.do_not.length)L.push("- 하지 말 것: "+c.do_not.join(" / "));if(pol.escalate_if)L.push(`- 다음 재평가: ${pol.escalate_if}`);
  L.push("","## 4. 분석관 판정 반영");
  if(c.judgments.length){c.judgments.forEach(j=>L.push(`- [${j.recorded_at}] ${j.hour}시 · burst ${j.burst_id} → ${j.judgment_label}${j.reason?` (${j.reason})`:""} · 기록 ${j.record_sha256.slice(0,12)}…`));L.push(`- 재집계: ${ra.note.replace(/<[^>]+>/g,"")}`)}else L.push("- 판정 없음 — 시스템 근거 그대로");
  L.push("","## 5. 신뢰도와 한계");D.an.limits.forEach(x=>L.push("- "+x));
  L.push("",`증거 체인 끝 \`${c.chain_end.slice(0,16)}…\` · 이 문서의 숫자는 모두 화면과 같은 파일(out/)에서 생성됨`);return L.join("\n")}
function renderBrief(N,h,lv,fo,isSusBeh){
  const c=buildCtx(N,h,lv,fo,isSusBeh),md=briefingMd(c),pol=c.policy||{},ra=c.reassess,lead=c.foreign.filter(f=>f.lead_h>0).map(f=>f.lead_h);
  const nums=[["의심 계정 (행동 기준)",`${ra.n_after}개`,ra.removed.length?`판정 전 ${ra.n_before}개`:"판정 없음"],["외국어 원문 선행",`${c.foreign.length}건`,lead.length?`한국어보다 최대 ${Math.max(...lead).toFixed(1)}시간 앞섬`:"연결 없음"],["자생 확산 확률 P(R>1)",c.r&&c.r.p1!=null?Math.round(c.r.p1*100)+"%":"—",c.r?"R̂ "+f2(c.r.r):"표본 부족"],["전조 정합성",c.pre?c.pre.state_label:"—",c.pre?`수렴 ${c.pre.conv}/3축`:"해당 없음"]];
  window.__BRIEF=md;
  const briefBox=`<details ${BRIEF_OPEN?"open":""} ontoggle="BRIEF_OPEN=this.open"><summary>브리핑 초안 — 규칙 기반 템플릿 · LLM 미사용 · 분석관 검토 전</summary><div style="display:flex;gap:6px;margin:8px 0"><button class="btn pri" onclick="dl('briefing_N${c.nid}_${String(h).padStart(2,'0')}h.md',window.__BRIEF,'text/markdown')">브리핑 초안 내려받기 (.md)</button><button class="btn" onclick="navigator.clipboard&&navigator.clipboard.writeText(window.__BRIEF)">복사</button></div><pre class="brief">${esc(md)}</pre></details>`;
  document.getElementById("cmdbox").innerHTML=`<div class="box" style="padding:14px 16px;margin-top:10px"><div class="muted">지휘관 요약 — 같은 데이터를 줄인 1화면 · 판정 아님 · 최종 결정은 사람</div>
    <div style="font-size:24px;font-weight:700;margin:2px 0 10px">N${c.nid} · ${c.level} ${c.level_name} · ${pol.action_label||"권고 없음"}</div>
    <div class="kpis" style="grid-template-columns:repeat(4,1fr);margin:0 0 12px">${nums.map(([k,v,d])=>`<div class="kpi"><div class="l">${k}</div><div class="v">${v}</div><div class="muted" style="font-size:12px">${d}</div></div>`).join("")}</div>
    <div class="card"><div style="font-size:14px">${c.do_not.length?`<b>하지 말 것</b><ul>${c.do_not.slice(0,3).map(x=>`<li>${esc(x)}</li>`).join("")}</ul>`:""}<b>다음 재평가</b> ${esc(pol.escalate_if||"—")}<br><b>카드 신뢰도</b> ${c.confidence} · <b>분석관 판정</b> ${c.judgments.length}건</div>
    <div style="font-size:14px"><b>운용 위치와 경계</b><ul>${Object.entries(D.an.conops).map(([k,v])=>`<li><b>${k}</b> ${esc(v)}</li>`).join("")}</ul></div></div></div>${briefBox}
    <div class="muted" style="margin-top:8px">상세 근거·차트는 왼쪽 '분석관' 화면으로 전환하면 보입니다.</div>`;
  const bc=document.getElementById("briefwrap");if(bc)bc.innerHTML=ROLE==="cmd"?"":briefBox;
}
let SATI=0,SATPOS=50;
function renderSat(){const S=D.sat,W=document.getElementById("satwrap");if(!S||!S.sites||!S.sites.length){if(W)W.style.display="none";return}const site=S.sites[SATI];
  const tabs=`<div class="sattabs">${S.sites.map((x,i)=>`<button class="${i===SATI?"on":""}" onclick="SATI=${i};SATPOS=50;renderSat()">${esc(x.title.split(" (")[0])}</button>`).join("")}</div>`;
  const has=site.before.src&&site.after.src;
  const img=has?`<div class="cmpw"><img src="${site.before.src}"><img class="after" id="satafter" src="${site.after.src}" style="clip-path:inset(0 0 0 ${SATPOS}%)"><div class="div" id="satdiv" style="left:${SATPOS}%"></div><span class="lab l">전 · ${esc(site.before.date)}</span><span class="lab r">후 · ${esc(site.after.date)}</span><input type="range" min="0" max="100" value="${SATPOS}" oninput="SATPOS=+this.value;document.getElementById('satafter').style.clipPath='inset(0 0 0 '+SATPOS+'%)';document.getElementById('satdiv').style.left=SATPOS+'%'"></div>`
    :`<div class="cmpw"><div class="ph"><div>아직 영상 파일이 없습니다 — 두 파일을 <b>data/sat/</b>(바탕화면 백신/4_근거자료/위성/)에 넣고 다시 내보내면 전·후 비교로 뜹니다.<code>${esc(site.before.file)} (전 · ${esc(site.before.date)})</code><code>${esc(site.after.file)} (후 · ${esc(site.after.date)})</code></div></div></div>`;
  const coord=site.lat!=null?`${(+site.lat).toFixed(3)}°N ${(+site.lon).toFixed(3)}°E`:"좌표 [확인 필요]";
  const pe=(S.physical_events||[]).map(e=>`<li>${e.date} · ${esc(e.what)}${e.source_url?` · <a href="${e.source_url}" target="_blank">출처</a>`:""}</li>`).join("");
  document.getElementById("satbody").innerHTML=`${tabs}${img}<div style="font-size:13px;margin-top:8px"><b>${esc(site.title)}</b> · ${esc(site.place)} · ${coord}${site.browser_url?` · <a href="${site.browser_url}" target="_blank">Copernicus Browser에서 열기</a>`:""}</div>
   <div class="muted" style="margin-top:4px"><b>무엇을 보나</b> ${esc(site.what)} · <b>의미</b> ${esc(site.role)}</div>${pe?`<div style="font-size:13px;margin-top:8px"><b>물리 신호 보도 날짜</b><ul>${pe}</ul></div>`:""}
   <div class="info" style="background:#fdf6e3;color:#8a6200;margin-top:8px;font-size:12.5px">${esc(S.disclaimer)} ${esc(S.license_note)}</div><div class="muted" style="margin-top:6px;font-size:11.5px">${esc(S.attribution)}</div>`}
let RPTAG="v2";const RLV={0:"#d9d8d2",1:"#b5b4ad",2:"#e0a000",3:"#d03b3b"},RVC={hit:"#1baf7a",miss:"#8a8a85",false_alarm:"#d03b3b",ok:"#1baf7a","n/a":"#b5b4ad"};
function renderReplay(){const R=D.replay,W=document.getElementById("rpwrap");if(!R){if(W)W.style.display="none";return}if(W.dataset.done===RPTAG)return;W.dataset.done=RPTAG;
  const s1=R.summary.v1,s2=R.summary.v2;
  document.getElementById("rpsum").innerHTML=`실제 공개 담화 재생 (추출 가능 ${s2.n_precedent+s2.n_false_alarm_cases}건) — <b>v2 규칙</b>: 행동으로 이어진 ${s2.n_precedent}건 중 L3 선행 <b>${s2.n_hit}건</b>(${s2.leads.map(x=>x+"일").join(" · ")}), 행동 없던 ${s2.n_false_alarm_cases}건 중 L3 <b>${s2.n_false_alarm_l3}건</b> → 공식 축 단독이면 오경보 ${s2.n_false_alarm_l3}/${s2.n_false_alarm_cases} — 축 C(은밀 증폭)와의 정합성이 필요한 이유. <b>v1 규칙</b>(합성 문장만 보고 만든 것): 선행 ${s1.n_hit}/${s1.n_precedent} · 오경보 ${s1.n_false_alarm_l3}/${s1.n_false_alarm_cases} — 합성 데이터 과적합 그대로.`;
  const tag=RPTAG,cases=R.cases.filter(c=>c.verdict[tag].result!=="n/a"),tr=[],shapes=[],ann=[];
  cases.forEach((c,i)=>{const y=cases.length-1-i;if(c.kind==="precedent"&&c.action_date)shapes.push({type:"line",x0:0,x1:0,y0:y-.42,y1:y+.42,line:{color:"#1f1f1d",width:3}});
    else{shapes.push({type:"rect",x0:0,x1:c.window_days,y0:y-.3,y1:y+.3,fillcolor:"#9a9a94",opacity:.12,line:{width:0}});ann.push({x:c.window_days/2,y:y+.33,text:`${c.window_days}일 창 — 연결된 행동 없음`,showarrow:false,font:{size:10,color:"#6b6b66"}});
      if(c.action_rel_days!=null){shapes.push({type:"line",x0:c.action_rel_days,x1:c.action_rel_days,y0:y-.3,y1:y+.3,line:{color:"#9a9a94",width:2,dash:"dot"}});ann.push({x:c.action_rel_days,y:y-.42,text:"통상 활동(연결 안 됨)",showarrow:false,font:{size:9,color:"#8a8a85"}})}}
    c.statements.filter(s=>!s.excluded).forEach(s=>{const lv=s[tag].level;tr.push({x:[s.rel_days],y:[y],mode:"markers+text",showlegend:false,marker:{symbol:"diamond",size:12+5*lv,color:RLV[lv],line:{color:"#fff",width:1}},text:[`L${lv}`],textposition:"top center",textfont:{size:10,color:lv>=2?RLV[lv]:"#6b6b66"},hovertemplate:`${s.date} · ${esc(s.speaker_role)}<br>${tag} L${lv} (${s[tag].level_why})<br>${esc(s.text_ko.slice(0,90))}…<extra></extra>`})})});
  const PE=(D.sat&&D.sat.physical_events)||[];
  cases.forEach((c,i)=>{const y=cases.length-1-i;const ev=PE.filter(e=>e.case_id===c.case_id&&e.date&&c.action_date&&c.kind==="precedent").map(e=>({...e,rd:Math.round((new Date(e.date)-new Date(c.action_date))/864e5)}));if(!ev.length)return;
    const inR=ev.filter(e=>e.rd>=-9&&e.rd<=15.5),left=ev.filter(e=>e.rd<-9),right=ev.filter(e=>e.rd>15.5),MK="#9a9a94";
    if(inR.length)tr.push({x:inR.map(e=>e.rd),y:inR.map(()=>y-.33),mode:"markers",showlegend:false,marker:{symbol:"triangle-down",size:11,color:MK,line:{color:"#fff",width:1}},text:inR.map(e=>`${e.date} · ${esc(e.what)}`),hovertemplate:"%{text}<extra>물리 신호</extra>"});
    if(left.length){const lo=Math.min(...left.map(e=>e.rd)),hi=Math.max(...left.map(e=>e.rd));tr.push({x:[-8.7],y:[y-.33],mode:"markers+text",showlegend:false,marker:{symbol:"triangle-down",size:11,color:MK,line:{color:"#fff",width:1}},text:[`◀ 물리 신호 ${left.length}건 (${lo}~${hi}일)`],textposition:"bottom right",textfont:{size:10,color:"#6b6b66"},hovertemplate:left.map(e=>`${e.date} (${e.rd}일) · ${esc(e.what.slice(0,60))}`).join("<br>")+"<extra>물리 신호</extra>"})}
    if(right.length){tr.push({x:[15],y:[y-.33],mode:"markers+text",showlegend:false,marker:{symbol:"triangle-down",size:11,color:MK,line:{color:"#fff",width:1}},text:[`▶ ${right.length}건`],textposition:"bottom left",textfont:{size:10,color:"#6b6b66"},hovertemplate:right.map(e=>`${e.date} (+${e.rd}일) · ${esc(e.what.slice(0,60))}`).join("<br>")+"<extra>물리 신호</extra>"})}});
  ann.push({xref:"paper",yref:"paper",x:1,y:1.02,xanchor:"right",yanchor:"bottom",text:"▽ 물리 신호(위성·현장 공개 보도)",showarrow:false,font:{size:10,color:"#6b6b66"}});
  Plotly.react("rpfig",tr,{...base,height:60+46*cases.length,margin:{l:10,r:10,t:36,b:36},shapes,annotations:ann,title:{text:`실제 공개 담화 재생 — 규칙 ${tag} · 마름모 = 발언(색 = 수준) · 검은 선 = 실제 행동일 · 회색 띠 = 행동 없음`,font:{size:13}},
    xaxis:{title:"상대 일수 (선행 사례: 행동일 = 0 · 행동 없는 사례: 첫 발언 = 0)",range:[-9,15.5],zeroline:false,gridcolor:"#f0efe9",dtick:2},yaxis:{automargin:true,tickvals:cases.map((_,i)=>i),ticktext:[...cases].reverse().map(c=>`${c.case_id.slice(0,2)} ${c.name.split("(")[0].slice(0,22)}…`),tickfont:{size:11},range:[-.6,cases.length-.4]}},cfg);
  const rows=[];R.cases.forEach(c=>{const v2=c.verdict.v2;c.statements.forEach((s,k)=>{const lv=s.excluded?"요약문 — 추출 제외":`v1 L${s.v1.level} → <b style="color:${RLV[s.v2.level]}">v2 L${s.v2.level}</b>`;const fl=s.excluded?"":Object.keys(s.v2.fields).filter(k=>PF[k]).map(k=>`<span style="color:${PF[k][1]}">${PF[k][0]}</span>`).join(" · ");
    rows.push(`<tr>${k===0?`<td rowspan="${c.statements.length}" style="vertical-align:top"><b>${c.case_id.slice(0,2)}</b> ${esc(c.name)}<br><span class="muted">${c.kind_ko}${c.in_sample_v2?" · 규칙 설계에 사용":""}</span><br><span style="color:${RVC[v2.result]};font-weight:700">${esc(v2.label)}</span></td>`:""}<td style="white-space:nowrap">${s.date}</td><td>${esc(s.speaker_role)}</td><td style="max-width:420px">${esc(s.text_ko.slice(0,140))}${s.text_ko.length>140?"…":""}</td><td style="white-space:nowrap">${lv}</td><td>${fl}</td>${k===0?`<td rowspan="${c.statements.length}" style="vertical-align:top;white-space:nowrap">${c.action_date||"—"}</td>`:""}</tr>`)})});
  document.getElementById("rptbl").innerHTML=`<table><tr><th>사례</th><th>발언일</th><th>발화 기관</th><th>인용(보도된 그대로, 발췌)</th><th>규칙 수준</th><th>v2 추출 필드</th><th>행동일</th></tr>${rows.join("")}</table>`;
  document.getElementById("rpnotes").innerHTML=`<b>정직하게 적어 둘 것</b><ul>${R.notes.map(x=>`<li>${esc(x)}</li>`).join("")}</ul><div class="muted">출처: ${esc(R.source_file)} · 사례별 출처 URL과 확인 상태는 출처_실사례_라이브러리.md</div>`}
document.querySelectorAll('input[name=rptag]').forEach(r=>r.onchange=()=>{RPTAG=r.value;renderReplay()});
function renderPre(h){
  renderReplay();if(!renderPre.satDone){renderPre.satDone=true;renderSat()}
  const W=document.getElementById("prewrap");if(!D.pre){W.style.display="none";return}
  const P=D.pre,row=preRow(h),sa=P.statements.filter(s=>s.h<=h),bi=P.items.filter(x=>x.h<=h),cs=P.series.filter(s=>s.h<=h),camp=P.summary.campaign_narrative;
  // 타임라인 (위) + 정합성 (아래)
  const tr=[{x:[0,P.max_h],y:[0,0],mode:"lines",line:{color:PAX.D,width:1,dash:"dot"},hoverinfo:"skip",showlegend:false},
    {x:cs.map(s=>s.h),y:cs.map(()=>1),mode:"markers",marker:{symbol:"square",size:10,color:cs.map(s=>PLVC[s.c_label])},customdata:cs.map(s=>s.c_label),hovertemplate:"%{x}시 · 축 C 단계 %{customdata}<extra></extra>",showlegend:false}];
  if(bi.length) tr.push({x:bi.map(x=>x.h),y:bi.map(()=>2),mode:"markers",marker:{symbol:bi.map(x=>PSYM[x.kind]),size:13,color:PAX.B,line:{color:"#fff",width:1}},
    text:bi.map(x=>`${x.ts} · ${x.lang} · ${esc(x.outlet)}<br>${x.kind_label}<br>${esc(x.text_ko.slice(0,60))}`),hovertemplate:"%{text}<extra>B</extra>",showlegend:false});
  const shapes=[];
  if(sa.length){tr.push({x:sa.map(s=>s.h),y:sa.map(()=>3),mode:"markers+text",marker:{symbol:sa.map(s=>s.tone==="soft"?"diamond-open":"diamond"),size:sa.map(s=>10+5*s.level),color:PAX.A,line:{color:PAX.A,width:2}},
    text:sa.map(s=>`${s.stmt_id} L${s.level}`),textposition:"top center",textfont:{size:11,color:PAX.A},customdata:sa.map(s=>`${s.ts} · ${esc(s.channel)}<br>${s.level_why} · 톤 ${PTONE[s.tone]}<br>${esc(s.text.slice(0,70))}…`),hovertemplate:"%{customdata}<extra>A</extra>",showlegend:false});
    sa.forEach(s=>{if(s.level>=3&&s.deadline_hours){const [lo,hi]=s.deadline_hours;shapes.push({type:"rect",xref:"x",yref:"y",x0:s.h+lo,x1:Math.min(s.h+hi,P.max_h),y0:3-.28,y1:3+.28,fillcolor:PAX.A,opacity:.10,line:{color:PAX.A,width:1,dash:"dot"}})}})}
  tr.push({x:cs.map(s=>s.h),y:cs.map(s=>s.conv),mode:"lines",line:{shape:"hv",color:"#1f1f1d",width:2},fill:"tozeroy",fillcolor:"rgba(31,31,29,0.06)",hovertemplate:"%{x}시 · 수렴 축 %{y}/3<extra></extra>",showlegend:false,yaxis:"y2"});
  let rs=null,rst=null;[...cs,null].forEach(s=>{const st=s?s.state:null;if(st!==rst){if(["rhetoric_only","converged","mismatch"].includes(rst))shapes.push({type:"rect",xref:"x",yref:"y2",x0:rs-.5,x1:(s?s.h:h+1)-.5,y0:0,y1:3.3,fillcolor:PST[rst][1],opacity:.12,line:{width:0}});rs=s?s.h:null;rst=st}});
  shapes.push({type:"line",xref:"x",yref:"paper",x0:h,x1:h,y0:0,y1:1,line:{dash:"dot",color:"#6b6b66"}});
  Plotly.react("pc",tr,{...base,height:430,margin:{l:90,r:10,t:36,b:40},shapes,
    title:{text:"네 축의 전조 신호와 정합성 — 관측 시각까지 보이는 것만 · 보라 점선 띠 = 공식 발언의 예고 시간창",font:{size:14}},
    annotations:[{x:P.max_h/2,y:0,xref:"x",yref:"y",yshift:11,text:"데이터 없음 — 항만·선박·위성 전조는 연결 예정(T2-3·T2-4)",showarrow:false,font:{size:11,color:PAX.D}},
                 {xref:"paper",yref:"paper",x:0,y:.30,xanchor:"left",yanchor:"bottom",text:"수렴 축 수 · 띠 = 상태",showarrow:false,font:{size:11,color:"#6b6b66"}}],
    xaxis:{range:[0,P.max_h],title:"시작 후 시간",anchor:"y2"},
    yaxis:{domain:[.36,1],tickvals:[0,1,2,3],ticktext:["D 물리 전조","C 은밀 증폭","B 명분·동원","A 공식 신호"],range:[-.6,3.75],gridcolor:"#f0efe9",zeroline:false},
    yaxis2:{domain:[0,.28],range:[0,3.3],tickvals:[0,1,2,3],ticktext:["0","1","2","3축"],gridcolor:"#eee"}},cfg);
  // 카드 (왼쪽)
  const base_=baseStmt(h);
  const chip=(nm,txt,col,on)=>`<div class="chip" style="border-color:${on?col:"var(--line)"};background:${on?col+"14":"#fff"}"><b style="color:${col}">${nm}</b><span>${esc(txt)}</span></div>`;
  let aTxt=`L${row.a_level}`+(base_&&row.a_level>=2?` · ${base_.stmt_id} ${base_.level_why.split(" · ").pop()}`:"");if(row.a_tone==="soft"&&sa.length)aTxt+=` · 최신 ${sa[sa.length-1].stmt_id} 톤 완화`;
  const bTxt={0:"없음",1:`항목 ${row.b_items}건`,2:`다국어 명분 서사 확인 (${row.b_items}건)`}[row.b_level];
  const chips=`<div class="chips">${chip("A 공식 신호",aTxt,PAX.A,row.a_level>=2)}${chip("B 명분·동원",bTxt,PAX.B,row.b_level>=2)}${chip("C 은밀 증폭",row.c_label,PAX.C,row.c_level>=2)}${chip("D 물리 전조","데이터 없음",PAX.D,false)}</div>`;
  // 시간창
  let win="공식 발언에 시한이 없어 시간창을 만들지 않습니다.";
  const s3=sa.filter(s=>s.level>=3&&s.deadline_hours);
  if(s3.length){const s=s3[s3.length-1],[lo,hi]=s.deadline_hours,means=(s.fields.means||[]).join(" · ")||"수단 미명시(상응 조치)",place=[...new Set(s.fields.place||[])].join(" · ")||"장소 미명시";
    win=`<b>${esc(means)}</b> 가능성 · 장소 <b>${esc(place)}</b> · 시한 '${esc(s.fields.deadline[0])}' → <b>${fmt(s.h+lo)} ~ ${fmt(s.h+hi)}</b> (발언 ${s.stmt_id} 기준, 가상 시나리오 시각)`;
    const prec=s.similar.filter(c=>c.kind==="precedent"&&c.match>=2&&(c.axes||["A"]).includes("A"));
    if(prec.length)win+=`<br><span class="muted">유사 사례 선행: ${prec.map(c=>`${c.name.split(" (")[0]} ${c.lead_days}일`).join(" · ")} → 라이브러리 기준 ${Math.min(...prec.map(c=>c.lead_days))}~${Math.max(...prec.map(c=>c.lead_days))}일</span>`}
  const lad=row.ladder.map(l=>`<div class="lad"><span class="lv" style="color:${PLAD[l.status]}">${l.level}</span><span style="flex:1">${l.name}</span><span class="st" style="background:${PLAD[l.status]}22;color:${PLAD[l.status]}">${l.status}</span><span class="nt">${esc(l.note)}</span></div>`).join("");
  const pr=(D.nars[String(camp)].pol||[]).find(x=>x.h===h);
  let dn=["공식 발언(축 A)만으로 경보 단계를 올리지 않기","특정 일반 사용자 지목 금지"];if(pr)pr.dn.forEach(x=>{if(!dn.some(y=>y.includes(x)||x.includes(y)))dn.push(x)});if(row.state==="mismatch")dn.unshift("완화 발언을 근거로 경계·관찰을 낮추기");
  const conf={none:"—",watch:"낮음",rhetoric_only:"낮음 (공개 1축)",partial:"낮음~중간",converged:row.c_level>=2?"중간 (공개 2축 + 은밀 축 확인)":"중간 (공개 2축)",mismatch:"중간 — 해석 주의"}[row.state];
  document.getElementById("pcard").innerHTML=`<div class="muted">전조 카드 (분석관 보조 · 판정 아님 · 최종 결정은 사람)</div>
   <div style="font-size:22px;margin:2px 0 10px"><span style="color:${PST[row.state][1]};font-weight:700">${PST[row.state][0]} ${row.state_label}</span> <span class="muted" style="font-size:14px">수렴 ${row.conv}/3축 · ${h}시</span></div>${chips}
   <div style="margin:10px 0 4px;font-size:14px">${PWHY[row.state]}</div>
   <div style="margin-top:10px"><b>가능한 행동·시간창</b><div style="font-size:14px;margin-top:2px">${win}</div></div>
   <div style="margin-top:10px"><b>증거 사다리</b> <span class="muted">— 공개 데이터로 할 수 있는 주장의 단계</span>${lad}</div>
   <div class="card" style="gap:12px;margin-top:10px;font-size:14px"><div><b>권고</b> ${esc(pr?pr.al:(row.policy||"—"))}<br><span class="muted">대응 수위는 확산 단계(기존 권고)가 정하고, 전조 카드는 '언제·무엇을 경계할지'를 더한다</span></div>
   <div><b>하지 말 것</b><ul>${dn.map(x=>`<li>${esc(x)}</li>`).join("")}</ul></div></div>
   <div style="margin-top:6px;font-size:14px"><b>다음 재평가</b> 축 A 새 발언(톤·시한 변화) · 축 C burst 재발 또는 단계 상승 · 예고 시한 경과 시 상태 재계산 · <b>신뢰도</b> ${conf}</div>
   <div class="muted" style="margin-top:6px">축 A·B 자료는 가상(합성) · 추출·분류는 규칙 기반(시연, 운용 시 LLM 교체) · L5는 공개 데이터로 판단 불가.</div>`;
  // 발언 구조화 (오른쪽 위)
  const S=document.getElementById("pstmt");
  if(!base_){S.innerHTML='<div class="info">이 시각에는 아직 공식 발언이 없습니다. 발언이 들어오면 구조화 결과와 유사 사례가 여기 표시됩니다.</div>';document.getElementById("pcases").innerHTML="";}
  else{const t=base_.text;let out="",last=0;const sp=[...base_.spans].sort((a,b)=>a[0]-b[0]||(b[1]-b[0])-(a[1]-a[0]));
    sp.forEach(([a,b,k])=>{if(a<last)return;out+=esc(t.slice(last,a));const [nm,col]=PF[k];out+=`<span title="${nm}" style="border-bottom:2px solid ${col};background:${col}14;padding:0 1px">${esc(t.slice(a,b))}</span>`;last=b});out+=esc(t.slice(last));
    const legend=Object.values(PF).map(([n,c])=>`<span style="font-size:11px;color:${c};border-bottom:2px solid ${c}">${n}</span>`).join(" ");
    const F=base_.fields,j=(k,d)=>[...new Set(F[k]||[])].join(" / ")||d;
    const rows=[["발화자 격",`${base_.speaker} (${PRANK[base_.speaker_rank]||"—"}) · ${base_.channel} · ${base_.route}`],["조건",j("conditional","없음")],["시한",j("deadline","없음")],["장소",j("place","없음")],["수단",j("means","미명시")],["책임 전가 대상",j("blame","없음")],["톤",PTONE[base_.tone]+(base_.tone==="soft"&&F.threat?" — 위협 표현과 혼재":"")]];
    let latest="";const L=sa[sa.length-1];if(L!==base_){const cond=(L.fields.conditional||[]).join(" / ");latest=`<div style="margin-top:8px;padding:8px 12px;border-left:3px solid ${L.tone==="soft"?PF.soft[1]:PAX.A};background:#f6f9fe;font-size:13px"><b>최신 발언 ${L.stmt_id}</b> · ${L.ts} · ${esc(L.channel)} · 톤 <b>${PTONE[L.tone]}</b>${cond?" · 조건: "+esc(cond):""}<br>“${esc(L.text)}”<br><span class="muted">기준 발언(${base_.stmt_id})의 예고는 철회되지 않았다. 완화 발언은 톤 변화로만 기록한다.</span></div>`}
    S.innerHTML=`<div class="muted" style="font-size:12px">기준 공식 발언 ${base_.stmt_id} · ${base_.ts} · 수준 L${base_.level} (${base_.level_why}) · 원문은 가상 번역문</div><div class="quote">“${out}”</div><div style="margin-bottom:6px">${legend}</div>
     <table class="ftbl">${rows.map(([k,v])=>`<tr><td>${k}</td><td>${esc(v)}</td></tr>`).join("")}</table><div class="muted" style="margin-top:4px">인용 구절이 없는 필드는 채우지 않는다(환각 차단). 규칙 기반 추출(시연).</div>${latest}`;
    // 유사 사례 (오른쪽 아래)
    const byid={};P.cases.forEach(c=>byid[c.id]=c);let sims=[...base_.similar];
    if(row.state==="mismatch"&&!sims.some(m=>m.id==="X1"))sims.unshift({id:"X1",kind:"counter",name:byid.X1.name,match:0,lead_days:byid.X1.lead_days,matched:[]});
    const mx=8,kc={precedent:PAX.A,counter:"#8e24aa",false_alarm:"#8a8a85"};
    document.getElementById("pcases").innerHTML=`<div class="muted" style="font-size:12px">유사 과거 사례 — 신호에서 행동까지 선행 일수 (공개 보도 기준 · 라이브러리 7건 · 규칙 기반 유사도)</div>`+
     sims.map(m=>{const c=byid[m.id],ld=c.lead_days,col=kc[c.kind],w=ld==null?0:Math.min(ld,mx)/mx*100,lab=ld==null?"사건 없음":(ld<=mx?ld+"일":ld+"일 (축 B 장기 축적)");
       const mt=m.match?`구조 일치 ${m.match}/4${m.matched.length?" · "+m.matched.map(k=>PF[k][0]).join(", "):""}`:"불일치 상태의 참고 반례";
       return `<div style="margin:6px 0"><div style="display:flex;justify-content:space-between;font-size:13px"><span><b>${esc(c.name)}</b> <span class="muted">${mt}</span></span><span style="color:${col};font-weight:700;white-space:nowrap;margin-left:8px">${lab}</span></div><div class="cbar"><div style="width:${w.toFixed(0)}%;background:${col}"></div></div><div class="muted" style="font-size:12px;margin-top:2px">${esc(c.signal.slice(0,70))}… → ${esc(c.action.slice(0,40))}${c.note?" · "+esc(c.note):""}</div></div>`}).join("")+
     `<div class="muted" style="font-size:12px">보라 = 선행 사례 · 자주색 = 반례(기만·동시) · 회색 = 사건 없는 급등. 정확도 주장이 아니라 참고용.</div>`;}
  document.getElementById("pitems").innerHTML=bi.length?`<table style="margin-top:8px"><tr><th>시각</th><th>언어</th><th>매체(가상)</th><th>분류(규칙)</th><th>번역</th></tr>${bi.map(x=>`<tr><td>${x.ts}</td><td><code>${x.lang}</code></td><td>${esc(x.outlet)}</td><td style="color:${PAX.B};font-weight:700">${x.kind_label}</td><td>${esc(x.text_ko)}</td></tr>`).join("")}</table>`:'<div class="muted" style="margin-top:8px">아직 관측된 외국어 서사 항목이 없습니다.</div>';
  document.getElementById("plib").innerHTML=`<table style="margin-top:8px"><tr><th>ID</th><th>사례</th><th>신호일</th><th>행동일</th><th>선행(일)</th><th>신호</th><th>행동</th><th>출처</th></tr>${P.cases.map(c=>`<tr><td>${c.id}</td><td>${esc(c.name)}</td><td>${c.signal_date}</td><td>${c.action_date||"—"}</td><td>${c.lead_days==null?"—":c.lead_days}</td><td>${esc(c.signal)}</td><td>${esc(c.action)}</td><td style="font-size:11px">${c.sources.map(esc).join("<br>")}</td></tr>`).join("")}</table>`;
  const sm=P.summary;document.getElementById("psum").textContent=`이 시나리오에서: 공식 예고형 발언 ${sm.a_first_level3_id}(${Math.round(sm.a_first_level3_h)}시) → 은밀 증폭 관찰 ${sm.c_first_watch_h}시 (발언 ${Math.round(sm.a_to_watch_h)}시간 뒤) → 수렴 ${sm.first_converged_h}시 → 공식 톤 완화와 은밀 증폭 상승이 어긋나는 불일치 ${sm.first_mismatch_h}시. 모두 합성 데이터의 계산값입니다.`;
}

function renderSens(){
  if(!D.sens||!D.sens.length) return;
  const cols=Object.keys(D.sens[0]);
  const ts=(D.sens_x||{}).time_shuffle||{}, nf=(D.sens_x||{}).no_foreign_source||[];
  document.getElementById("sens").innerHTML=`<table style="margin-top:8px"><tr>${cols.map(c=>`<th>${c}</th>`).join("")}</tr>${D.sens.map(r=>`<tr>${cols.map(c=>`<td>${r[c]==null?"—":r[c]}</td>`).join("")}</tr>`).join("")}</table>
  <ul style="font-size:14px"><li><b>시간 셔플 대조:</b> 계정마다 게시 시각을 ±24시간 무작위로 밀면 burst ${ts.observed_bursts}건 → ${(ts.shuffled||[]).map(x=>x.bursts).join(", ")}, 의심 계정 ${ts.observed_suspected}개 → ${(ts.shuffled||[]).map(x=>x.suspected).join(", ")}</li>
  ${nf.map(x=>`<li><b>외국어 출처를 지우면</b> N${x.narrative_id}: 최고 ${x.max_level} · ${x.jurisdiction}</li>`).join("")}</ul>
  ${(D.sens_pol||[]).length?`<div style="margin:8px 0 4px"><b>대응 단계 권고의 가정값 격자</b> (일반 반응 기준 × 확산 확률 기준)</div><table><tr>${Object.keys(D.sens_pol[0]).map(c=>`<th>${c}</th>`).join("")}</tr>${D.sens_pol.map(r=>`<tr>${Object.keys(r).map(c=>`<td>${r[c]==null?"—":r[c]}</td>`).join("")}</tr>`).join("")}</table>`:""}
  <div class="muted">공작 계정 탐지는 설정에 견고하다(합성 데이터의 신호가 강한 탓도 있음). 경보(ALERT) 시점은 R 합산 시간·확률 기준에 민감하므로 운영 정책(오경보 허용 수준)으로 정해야 하는 값이다. 관찰(WATCH)과 위험(CRITICAL)은 안정적이다.</div>`;
}
renderSens();
// ---------------------------------------------------------------- 회피 내성 (레드팀) — 제2 신호층
let RV=0;
const RSHORT={base:"기본<br>(동시 게시)",jitter20:"시각<br>±20분",jitter60:"시각<br>±60분",jitter180:"시각<br>±180분",newsfeed:"뉴스<br>사칭형",newsfeed_mix:"+ 인기 링크<br>희석 50%",newsfeed_uniq:"+ 고유<br>단축 URL"};
function renderRed(){
  const W=document.getElementById("redwrap");const R=D.red;if(!R){W.style.display="none";return}
  const rows=R.rows,r=rows[RV],col=R.colors;
  document.getElementById("redbtns").innerHTML=rows.map((x,i)=>`<button onclick="RV=${i};renderRed()" style="padding:6px 10px;border-radius:8px;border:1.5px solid ${i===RV?"#1f1f1d":"var(--line)"};background:${i===RV?"#1f1f1d":"#fff"};color:${i===RV?"#fff":"#1f1f1d"};font-size:12px;cursor:pointer">${x[1]}</button>`).join("");
  document.getElementById("redkpi").innerHTML=[["burst 층 재현율",r[2].toFixed(2),"공작 계정 중 반복 동시 게시로 의심 표시"],["URL-망 층 재현율",r[3].toFixed(2),"72시간 안 희귀 링크 2개 이상 함께 공유 묶음"],["합집합",r[4].toFixed(2),""],["오탐 (burst / URL-망)",`${Math.round(r[5])} / ${Math.round(r[6])}`,"거의 전부 속보를 3번 재공유한 일반 계정"]]
    .map(([k,v,n])=>`<div class="kpi"><div class="k">${k}</div><div class="v" style="font-size:24px">${v}</div><div class="muted" style="font-size:11px">${n}</div></div>`).join("");
  const xs=rows.map((_,i)=>i);
  Plotly.react("redcurve",[
    {x:xs,y:rows.map(x=>x[2]),mode:"lines+markers",name:"burst 층(동시 게시)",line:{color:col.burst,width:3},marker:{size:9}},
    {x:xs,y:rows.map(x=>x[3]),mode:"lines+markers",name:"URL-망 층(함께 미는 링크)",line:{color:col.url,width:3},marker:{size:9}},
    {x:xs,y:rows.map(x=>x[4]),mode:"lines",name:"합집합",line:{color:col.union,width:1.5,dash:"dot"}}],
    {...base,height:350,margin:{l:40,r:10,t:72,b:60},title:{text:"신호 생존 곡선 — 공격자 정교함에 따른 공작 계정 재현율",font:{size:14},y:.97,yanchor:"top"},
     shapes:[{type:"rect",xref:"x",yref:"paper",x0:RV-.5,x1:RV+.5,y0:0,y1:1,fillcolor:"#1f1f1d",opacity:.06,line:{width:0}}],
     xaxis:{tickvals:xs,ticktext:rows.map(x=>RSHORT[x[0]]||x[1]),tickfont:{size:11},range:[-.5,rows.length-.5]},
     yaxis:{range:[-.05,1.08],title:"재현율",gridcolor:"#eee"},legend:{orientation:"h",y:1.13,x:0,font:{size:11}}},cfg);
  const net=R.nets[r[0]];
  if(net&&net.nodes.length){
    const ex=[],ey=[];net.edges.forEach(e=>{ex.push(e.x0,e.x1,null);ey.push(e.y0,e.y1,null)});
    const tr=[{x:ex,y:ey,mode:"lines",line:{color:"#c9c8c0",width:.8},opacity:.7,hoverinfo:"skip",showlegend:false}];
    [["공작 계정",C.sus],["속보 참여 일반 계정",C.ord],["일반 계정","#b5b4ad"]].forEach(([k,c])=>{const nn=net.nodes.filter(n=>n.kind===k);if(nn.length)tr.push({x:nn.map(n=>n.x),y:nn.map(n=>n.y),mode:"markers",name:k,marker:{size:13,color:c,line:{color:"#fff",width:1.5}},text:nn.map(n=>n.id),hovertemplate:"%{text}<extra>"+k+"</extra>"})});
    Plotly.react("rednet",tr,{...base,height:330,margin:{l:10,r:10,t:40,b:10},title:{text:`URL 공유 네트워크 — ${r[1]} (시드 1)`,font:{size:14}},xaxis:{visible:false},yaxis:{visible:false,scaleanchor:"x"},legend:{orientation:"h",y:-.02,x:0,font:{size:11}}},cfg);
    const comps=net.components.filter(c=>c.flagged);
    document.getElementById("rednote").textContent=`선 = 72시간 안에 희귀 링크 2개 이상을 함께 공유(대조군 99.9 백분위 초과) · 의심 묶음 ${comps.length}개 (${comps.map(c=>`크기 ${c.size}·밀도 ${c.density.toFixed(2)}`).join(", ")||"없음"}) · 묶인 계정 ${net.flagged}개 중 공작 ${net.camp_in_flagged}개. 파란 묶음은 같은 속보 기사를 3번 재공유한 일반 계정 — 이 층의 오탐이며 경보 단계에서는 걸러진다(실험 1).`;
  }else{Plotly.purge("rednet");document.getElementById("rednet").innerHTML='<div class="info" style="margin:40px 10px">이 변형에서는 임계값을 넘는 링크 공유 쌍이 없습니다 — 네트워크가 비어 있습니다(= 탐지 실패).</div>';document.getElementById("rednote").textContent="";}
  document.getElementById("redfind").innerHTML=R.findings.map(t=>`<li>${esc(t)}</li>`).join("");
  if(R.ira){const ir=R.ira,m=R.ira_meta;
    document.getElementById("redira").innerHTML=`<div><div style="font-size:14px"><b>제2 신호층을 IRA 실데이터에 적용하면</b> <span class="muted">(같은 규칙·같은 임계값 규칙 · 대조군 = URL 셔플)</span></div><div class="box" style="margin-top:6px"><div id="redirabar"></div></div></div>
     <div style="font-size:14px"><ul><li>URL-망이 묶은 계정 <b>${m.flagged}개</b>(비영어 1묶음, 밀도 ${(m.density||0).toFixed(2)}, 같은 팀 ${Math.round(m.same*100)}%) — 전부 burst 층이 이미 잡은 계정 → <b>실데이터 추가 이득 0</b></li>
     <li>뉴스 매체 사칭 ${m.nf_n}개: 두 층 모두 <b>0%</b> 유지</li>
     <li><b>발견:</b> 이 계정들의 링크는 bit.ly 등 단축 주소로만 남아 있고(2단계 해석 ${Math.round(m.step2*100)}%), 계정마다 다른 도시의 지역 뉴스를 미러링 → '같은 링크'가 성립하지 않음. 레드팀의 '고유 단축 URL' 변형이 예측한 그대로</li>
     <li>보조 지표 '자동화 피드 프로필'은 뉴스 사칭 ${m.feed.flagged||0}/${m.feed.n||0}개를 가려내지만 진짜 언론 봇과 구분 못 함 → 확인 목록용</li></ul><div class="muted">${esc(m.caveat)}</div></div>`;
    Plotly.react("redirabar",[{type:"bar",orientation:"h",y:ir.map(x=>`${x[0]} (${x[1]}개)`),x:ir.map(x=>x[2]),name:"burst 층",marker:{color:col.burst},text:ir.map(x=>Math.round(x[2]*100)+"%"),textposition:"outside"},
      {type:"bar",orientation:"h",y:ir.map(x=>`${x[0]} (${x[1]}개)`),x:ir.map(x=>x[3]),name:"URL-망 층",marker:{color:col.url},text:ir.map(x=>Math.round(x[3]*100)+"%"),textposition:"outside"}],
      {...base,barmode:"group",height:320,margin:{l:150,r:50,t:72,b:30},title:{text:"운영팀별 의심 표시 비율 — burst 층 vs URL-망 층 (IRA 실데이터)",font:{size:14},y:.97,yanchor:"top"},xaxis:{range:[0,1.2],tickformat:".0%",gridcolor:"#eee"},yaxis:{automargin:true,tickfont:{size:12}},legend:{orientation:"h",y:1.14,x:0,font:{size:11}}},cfg);}
  const p=R.params||{};
  document.getElementById("redrule").innerHTML=`<ul style="font-size:13px"><li><b>URL-망 규칙:</b> 두 계정이 ${p.window_h||72}시간 안에 같은 희귀 링크(링크 공유 계정의 ${Math.round((p.rare_frac||.2)*100)}% 이하가 공유)를 ${p.min_shared||2}개 이상 함께 공유하면 쌍 점수(IDF 합) → 임계값은 URL을 무작위로 섞은 대조군의 99.9 백분위 → 쌍을 이어 크기 ${p.min_comp||5}·밀도 ${p.min_density||.3} 이상 묶음만 의심. 도메인 신규성(WHOIS)·단축 URL 해석은 데이터 없음.</li>
   <li><b>희귀 기준 20%는 결과를 본 뒤 고른 가정값</b>입니다. 5%·10%·20%·전체 격자를 그대로 공개합니다(5%는 외국 기사 링크가 경계에 걸려 시드별로 0.93/0.83/0.00으로 불안정).</li></ul>
   <table><tr><th>희귀 기준</th><th>변형</th><th>URL-망 재현율(평균)</th><th>최소</th><th>오탐</th><th>대조군 우연 묶임</th><th>τ</th></tr>${(R.sweep||[]).map(x=>`<tr><td>${x.rare_frac}</td><td>${x.variant}</td><td>${(+x.recall_url).toFixed(2)}</td><td>${(+x.recall_min).toFixed(2)}</td><td>${(+x.fp_url).toFixed(1)}</td><td>${(+x.null_flagged).toFixed(1)}</td><td>${(+x.tau).toFixed(2)}</td></tr>`).join("")}</table>
   <div class="muted" style="margin-top:6px">변경 이력(experiments/config.json · redteam_urlnet.changes): p99.9 임계값만 → 대조군 묶음 최대 29계정 → 밀도 0.3 추가 → 희귀 5% 추가(불안정) → 20%로 확정. 배경 링크 비율 25%·속보 공유 50%는 [가정]. 합성 결과이며 실데이터 검증은 아래 IRA 절.</div>`;
}

function renderReal(){
  const R=D.real; if(!R) return;
  const name={HashtagGamer:"해시태그 게임",LeftTroll:"좌파 사칭",RightTroll:"우파 사칭",NonEnglish:"비영어(러시아어 등)",NewsFeed:"뉴스 매체 사칭"};
  const pct=v=>Math.round(v*100)+"%";
  const items=Object.entries(R.repeated_by_category).filter(([k])=>(R.accounts_by_category[k]||0)>=5).sort((a,b)=>a[1]-b[1]);
  document.getElementById("realwrap").innerHTML=`<h2 style="margin-top:32px;border-top:1px solid var(--line);padding-top:20px">실데이터 검증 — 공개된 러시아 IRA 트윗</h2>
  <div class="muted">FiveThirtyEight·클렘슨대 공개 데이터 · ${R.window} · 트윗 ${R.tweets.toLocaleString()}건 · 계정 ${R.accounts}개 · 위 시스템과 같은 규칙(10분 안 같은 글·같은 링크, 2회 이상 반복)을 그대로 적용 · 계정은 가명</div>
  <div class="kpis">${[["동시 게시 묶음",R.events.toLocaleString()+"건"],["대조 실험(시각 무작위 이동)",Math.round(R.null_events_mean)+"건"],["반복 참여 계정(의심 기준)",pct(R.accounts_repeated_share)],["같은 운영팀 비율",(R.same_category_rate*100).toFixed(1)+"%"+` <span class="muted" style="font-size:13px">무작위 ${pct(R.same_category_rate_random)}</span>`]].map(([l,v])=>`<div class="kpi"><div class="l">${l}</div><div class="v">${v}</div></div>`).join("")}</div>
  <div class="card"><div class="box"><div id="c5"></div></div><div>
  <b>확인된 것</b><ul><li>실제 공작 계정도 동시 게시 흔적을 남긴다: 대조 실험 대비 <b>약 ${Math.round(R.events/Math.max(R.null_events_mean,1))}배</b></li>
  <li>묶인 계정은 거의 같은 운영팀: <b>${(R.same_category_rate*100).toFixed(1)}%</b> (무작위 ${pct(R.same_category_rate_random)})</li>
  <li>언어가 다른 계정이 같은 링크를 동시에 퍼 나른 묶음 <b>${R.multi_language_url_events}건</b></li></ul>
  <b>확인하지 못한 것 (한계)</b><ul><li>뉴스 매체 사칭 계정은 거의 못 잡음: 동시 게시 대신 각자 시간에 올림</li><li>오탐: 이 데이터엔 일반 사용자가 없어 측정 불가</li><li>R 경보·조기성: 리포스트 관계가 없어 측정 불가 → 플랫폼 데이터 협력 필요</li><li>한국어 공간: 공개된 한국 대상 공작 데이터셋 부재</li></ul></div></div>
  <details><summary>동시 게시 묶음 예시 (가명)</summary><ul>${R.examples.map(x=>`<li>${x.start.slice(0,16)} · ${Math.round(x.span_sec/60)}분 사이 계정 <b>${x.n_accounts}개</b> · ${x.langs.join(", ")}<br><small class="muted">${x.sample.replace(/</g,"&lt;")}</small></li>`).join("")}</ul></details>`;
  Plotly.react("c5",[{type:"bar",orientation:"h",x:items.map(([,v])=>v),y:items.map(([k])=>`${name[k]||k} (${R.accounts_by_category[k]}개)`),
    marker:{color:C.sus},text:items.map(([,v])=>pct(v)),textposition:"outside",hoverinfo:"skip"}],
    {...base,height:260,margin:{l:170,r:40,t:40,b:30},title:{text:"운영팀별 '반복 동시 게시' 계정 비율 (=시스템이 잡는 비율)",font:{size:13}},
     xaxis:{range:[0,1.15],tickformat:".0%",gridcolor:"#eee"}},cfg);
}
renderRed();renderReal();
window.addEventListener("resize",()=>{clearTimeout(window._rt);window._rt=setTimeout(()=>{render();renderRed();renderReal()},150)});
render();
</script></body></html>"""

if __name__ == "__main__":
    main()
