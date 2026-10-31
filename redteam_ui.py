"""
redteam_ui.py — 회피 내성(레드팀) 화면 재료 (2026-10-17 추가)
app.py(Streamlit)와 export_html.py(오프라인 백업)가 같은 숫자·같은 배치를 쓰도록 한 곳에 둔다.
입력: out/redteam.json (experiments/redteam.py), real/urlnet_ira_results.json (real/urlnet_ira.py)
"""
import json, os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
C_ORD, C_SUS, C_SRC, C_GREY = "#2a78d6", "#eb6834", "#1baf7a", "#b5b4ad"
C_BURST, C_URL, C_UNION = "#eb6834", "#6c4ad6", "#1f1f1d"
CAT_KO = {"HashtagGamer": "해시태그 게임", "LeftTroll": "좌파 사칭", "RightTroll": "우파 사칭",
          "NonEnglish": "비영어(러시아어 등)", "NewsFeed": "뉴스 매체 사칭", "Fearmonger": "공포 조장", "Unknown": "미분류"}


def load():
    rp = os.path.join(HERE, "out", "redteam.json")
    ip = os.path.join(HERE, "real", "urlnet_ira_results.json")
    R = json.load(open(rp, encoding="utf-8")) if os.path.exists(rp) else None
    I = json.load(open(ip, encoding="utf-8")) if os.path.exists(ip) else None
    return R, I


def layout(nodes, edges, seed=7, iters=None):
    """묶음별 배치: 연결 요소를 찾고, 요소마다 해바라기(황금각) 배열로 점을 촘촘하되 겹치지 않게 놓은 뒤
    요소들을 가로로 나란히 둔다(큰 묶음이 가운데). 힘-기반 배치는 촘촘한 묶음을 한 점으로 뭉개서 쓰지 않는다."""
    ids = [n["id"] for n in nodes]
    if not ids:
        return {}
    parent = {a: a for a in ids}
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for e in edges:
        if e["a"] in parent and e["b"] in parent:
            ra, rb = find(e["a"]), find(e["b"])
            if ra != rb:
                parent[ra] = rb
    groups = {}
    for a in ids:
        groups.setdefault(find(a), []).append(a)
    comps = sorted(groups.values(), key=len, reverse=True)
    rng = np.random.default_rng(seed)
    ga = np.pi * (3 - np.sqrt(5))          # 황금각
    placed, cx, blocks = {}, 0.0, []
    for c in comps:
        c = list(c); rng.shuffle(c)
        n = len(c); r_max = 0.13 * np.sqrt(n) + 0.05
        pts = []
        for i, a in enumerate(c):
            r = r_max * np.sqrt((i + 0.5) / n); th = i * ga
            pts.append((a, r * np.cos(th), r * np.sin(th)))
        blocks.append((r_max, pts))
    # 큰 묶음을 가운데, 나머지를 좌우로 번갈아
    order = []
    for i, b in enumerate(blocks):
        order.insert(len(order) // 2 if i % 2 else len(order) - len(order) // 2, b) if order else order.append(b)
    x = 0.0
    for r_max, pts in order:
        x += r_max
        for a, px, py in pts:
            placed[a] = (x + px, py)
        x += r_max + 0.25
    xs = np.array([v[0] for v in placed.values()]); ys = np.array([v[1] for v in placed.values()])
    cxm = (xs.max() + xs.min()) / 2; sc = max(xs.max() - xs.min(), ys.max() - ys.min(), 1e-6) / 2
    return {a: ((px - cxm) / sc, py / sc) for a, (px, py) in placed.items()}


def curve_rows(R):
    """[(variant, label, recall_burst, recall_url, recall_union, fp_burst, fp_url, null_flagged)]"""
    return [(c["variant"], c["label"], c["recall_burst"], c["recall_url"], c["recall_union"],
             c["fp_burst"], c["fp_url"], c.get("null_flagged", 0.0)) for c in R["curve"]]


def network_payload(R, variant):
    """선택 변형의 URL-망 예시 그래프: 노드 좌표·색·간선"""
    ex = R["examples"].get(variant)
    if not ex:
        return None
    pos = layout(ex["nodes"], ex["edges"])
    nodes = []
    for nd in ex["nodes"]:
        kind = "공작 계정" if nd["camp"] else ("속보 참여 일반 계정" if nd["b1"] else "일반 계정")
        col = C_SUS if nd["camp"] else (C_ORD if nd["b1"] else C_GREY)
        x, y = pos[nd["id"]]
        nodes.append(dict(id=nd["id"], x=x, y=y, kind=kind, color=col))
    edges = [dict(x0=pos[e["a"]][0], y0=pos[e["a"]][1], x1=pos[e["b"]][0], y1=pos[e["b"]][1],
                  score=e["score"], n=e["n_shared_urls"]) for e in ex["edges"] if e["a"] in pos and e["b"] in pos]
    return dict(nodes=nodes, edges=edges, flagged=ex["flagged"], camp_in_flagged=ex["camp_in_flagged"],
                components=ex["components"], links=ex.get("links", []))


def ira_rows(I):
    """[(분류, n, burst 비율, URL-망 비율, 합집합 비율)] — 계정 5개 이상 분류만"""
    out = []
    for k, v in I["burst"]["by_category"].items():
        if v["n"] < 5:
            continue
        u = I["urlnet"]["by_category"].get(k, {"share": 0.0}); un = I["union"]["by_category"].get(k, {"share": 0.0})
        out.append((CAT_KO.get(k, k), v["n"], v["share"], u["share"], un["share"]))
    return sorted(out, key=lambda r: r[2])


def findings_text(R, I):
    """확인된 것 / 확인하지 못한 것 — 숫자는 모두 파일에서"""
    cv = {c["variant"]: c for c in R["curve"]}
    f = []
    f.append(f"burst 층은 게시 시각 ±20분에 재현율 {cv['base']['recall_burst']:.2f} → {cv['jitter20']['recall_burst']:.2f}, ±60분이면 {cv['jitter60']['recall_burst']:.2f}. "
             f"URL-망 층은 시각과 무관해 {cv['base']['recall_url']:.2f}로 일정 → 합집합은 ±20분 {cv['jitter20']['recall_union']:.2f}, ±60분 {cv['jitter60']['recall_union']:.2f}")
    f.append(f"뉴스 사칭형(각자 시간에 게시, 묵은 계정, 재작성 문장): burst {cv['newsfeed']['recall_burst']:.2f} / URL-망 {cv['newsfeed']['recall_url']:.2f} — 단, 링크가 해석될 때만")
    f.append(f"링크 절반을 인기 링크로 희석하면 {cv['newsfeed_mix']['recall_url']:.2f}, 게시마다 다른 단축 URL이면 {cv['newsfeed_uniq']['recall_url']:.2f} — 72시간 창의 한계와 단축 URL 미해석의 한계")
    f.append(f"오탐: 속보 기사를 3번 재공유한 일반 계정 약 {cv['base']['fp_url']:.0f}개가 URL-망에, {cv['base']['fp_burst']:.0f}개가 burst에 걸림(두 층 공통, 실험 1과 같은 대조군). "
             f"대조군(URL 셔플)에서 우연히 묶이는 계정은 평균 {max(c.get('null_flagged', 0) for c in R['curve']):.0f}개 이하")
    if I:
        nf = I["urlnet"]["by_category"].get("NewsFeed", {}); ne = I["urlnet"]["by_category"].get("NonEnglish", {})
        f.append(f"IRA 실데이터: URL-망은 비영어 계정 {ne.get('flagged', 0)}개를 밀도 {I['urlnet']['components'][0]['density']:.2f}의 한 묶음으로 묶었고(같은 팀 {I['urlnet']['same_category_rate']:.0%}, 무작위 {I['urlnet']['same_category_rate_random']:.0%}, 대조군 {I['urlnet']['null_flagged_accounts']}) "
                 f"— 모두 burst 층이 이미 잡은 계정. 뉴스 사칭 {nf.get('n', 35)}개는 여전히 {nf.get('share', 0):.0%}")
        bl = I.get("newsfeed_link_domains_step1", {}).get("bit.ly", 0)
        f.append(f"왜 못 잡나(발견): 뉴스 사칭 계정 트윗 {I['newsfeed_tweets']:,}건의 링크가 bit.ly({bl:,}건) 등 단축 주소로만 남아 있고(2단계 해석 {I['newsfeed_step2_resolved_share']:.0%}) 계정마다 다른 도시의 지역 뉴스를 미러링 → '같은 링크'가 성립하지 않음. 레드팀 'newsfeed_uniq' 변형이 예측한 그대로")
        fp = I["feed_profile"]["flagged_by_category"].get("NewsFeed", {})
        f.append(f"보조 지표 '자동화 피드 프로필'(링크 ≥95%·리트윗 ≤5%·멘션 ≤5%·24시간 활동)은 뉴스 사칭 {fp.get('flagged', 0)}/{fp.get('n', 0)}개를 가려내지만, 진짜 언론사 자동 계정도 같은 프로필 → 사칭 증거가 아니라 확인 목록용")
    return f
