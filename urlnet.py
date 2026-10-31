"""
urlnet.py — 제2 신호층: 계정–URL 공유 네트워크 (2026-10-17 추가 · 회피 내성 보강)

왜 필요한가
  기존 M3(coordination.py)는 '짧은 시간에 몰린 게시(burst)'를 본다. 그래서 공작자가 게시 시각만
  ±20분 흩뜨려도 재현율이 0.9 → 0.18로 떨어지고(실험 2a), 각자 시간에 올리는 뉴스 사칭형 계정은
  IRA 실데이터에서 0% 탐지였다(한계 1). 이 층은 '언제'가 아니라 '무엇을 함께 미는가'를 본다.

무엇을 보나 (내용이 아니라 행동, 시각과 무관)
  · 두 계정이 72시간 안에 '같은 희귀 링크'를 2개 이상 함께 공유했는가
    희귀 링크 = 링크를 공유한 계정 전체의 20% 이하가 공유한 링크. 누구나 공유하는 대중적 링크는 세지 않는다
    (정상 사용자의 자연스러운 동시 공유를 거르는 핵심 조건. 대신 수백 계정이 동원된 대형 공작의 링크는 '인기'가 되어
    이 층을 빠져나간다 — 그때는 burst 층·R̂ 층이 본다)
  · 희귀도 가중 = log(링크 공유 계정 수 전체 / 그 링크를 공유한 계정 수)  (IDF)
  · 임계값은 사람이 정하지 않는다: 게시물의 URL을 무작위로 섞은 대조군(시각·계정별 게시 수·링크 인기 보존)에서
    쌍 점수 분포의 99.9 백분위를 임계값으로 쓴다 → 같은 규칙이 합성·실데이터에 그대로 적용된다
  · 임계값을 넘는 쌍을 이어 연결 요소(묶음)를 만들고, 크기 5 이상·밀도 0.3 이상(서로 촘촘히 이어진) 묶음의 계정을
    'URL-망 의심'으로 표시. 밀도 조건은 셔플 대조군에서 우연한 쌍이 성긴 연쇄로 이어져 큰 묶음이 되는 것을 거른다
  · 계정별 보조 지표: 희귀 도메인 집중도(공유 링크 중 공유 계정 5개 이하 도메인의 비율)

하지 않는 것 / 한계
  · 서사 묶기(임베딩) 결과를 쓰지 않는다 → 서사 묶기가 실패해도 작동 (장점) / 서사별 해석은 사후 결합
  · 도메인 신규성(WHOIS 등록일)은 데이터가 없어 보지 않는다 → 운용 시 연결 [데이터 없음]
  · 단축 URL을 해석하지 않으면 회피 가능(게시마다 다른 단축 주소) → 운용 시 리졸버 필요
  · 정상 사용자도 같은 속보 링크를 공유한다 → 오탐은 레드팀(redteam.py)에서 속보 대조군으로 측정

입력 : data/posts.csv (post_id, ts, account_id, url) · data/accounts.csv (created_at)
출력 : out/urlnet_accounts.csv, out/urlnet_edges.csv, out/urlnet_components.csv, out/urlnet_summary.json
실행 : python urlnet.py            (필요 패키지: pandas numpy)
"""
import json, os, re, sys
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA, OUT = os.path.join(HERE, "data"), os.path.join(HERE, "out")

WINDOW_H = 72          # 두 계정의 같은 링크 공유가 이 시간 안에 있어야 '함께 공유'
MIN_SHARED = 2         # 함께 공유한 서로 다른 링크 최소 수
MIN_COMP = 5           # 묶음 최소 크기
MIN_DENSITY = 0.30     # 묶음 밀도(실제 간선 / 가능한 쌍) 최소 — 대조군의 우연한 연쇄(성긴 묶음)를 거른다
NULL_SEEDS = 3         # URL 셔플 대조군 반복 수
NULL_PCT = 99.9        # 대조군 쌍 점수 백분위 → 임계값
RARE_DOMAIN_SHARERS = 5
RARE_FRAC = 0.20       # [가정] '희귀 링크' = 링크 공유 계정 전체의 20% 이하가 공유한 링크. 5%/10%/20%/전체 격자 비교 후 선택(redteam.json 참고)

_TRACK = re.compile(r"[?&](utm_[^&]*|fbclid=[^&]*|gclid=[^&]*|s=\d+|ref=[^&]*|src=[^&]*)")


def norm_url(u):
    if not isinstance(u, str) or len(u) < 8:
        return ""
    u = u.strip()
    u = re.sub(r"^https?://", "", u, flags=re.I)
    u = re.sub(r"^www\.", "", u, flags=re.I)
    u = _TRACK.sub("", u)
    u = u.rstrip("/?&#")
    return u.lower()


def domain(u):
    return u.split("/")[0].split(":")[0] if u else ""


def _pairs_for_url(rows, win_ns):
    """rows: [(acc, ts_ns)] 한 링크의 공유 기록. 72시간 안에 함께 공유한 서로 다른 계정 쌍 집합."""
    rows = sorted(rows, key=lambda x: x[1])
    out = set()
    n = len(rows)
    j = 0
    for i in range(n):
        a, t = rows[i]
        k = i + 1
        while k < n and rows[k][1] - t <= win_ns:
            b = rows[k][0]
            if b != a:
                out.add((a, b) if a < b else (b, a))
            k += 1
    return out


def pair_scores(P, win_h=WINDOW_H):
    """P: columns account_id, ts(datetime), url(normalized, non-empty).
    반환: dict{(a,b): (score, n_shared_urls)}, dict{url: n_sharers}, N(링크 공유 계정 수)"""
    win_ns = int(pd.Timedelta(hours=win_h).value)
    ts_ns = P.ts.values.astype("datetime64[ns]").astype("int64")
    by_url = {}
    for u, a, t in zip(P.url.values, P.account_id.values, ts_ns):
        by_url.setdefault(u, []).append((a, int(t)))
    N = P.account_id.nunique()
    sharers = {u: len({a for a, _ in rows}) for u, rows in by_url.items()}
    rare_max = max(3, int(RARE_FRAC * N))
    scores = {}
    for u, rows in by_url.items():
        n = sharers[u]
        if n < 2 or n > rare_max:
            continue
        w = float(np.log(N / n))
        for pr in _pairs_for_url(rows, win_ns):
            s, c = scores.get(pr, (0.0, 0))
            scores[pr] = (s + w, c + 1)
    return scores, sharers, N


def null_threshold(P, seeds=NULL_SEEDS, pct=NULL_PCT, win_h=WINDOW_H):
    """URL만 게시물 사이에서 무작위로 섞는다(시각·계정별 게시 수·링크 인기 분포 보존).
    임계값 = 대조군 쌍 점수의 99.9 백분위. 같은 규칙으로 대조군에서 묶이는 계정 수를 '우연 수준'으로 함께 보고한다
    (관측값은 이 우연 수준과 비교해 읽는다 — 실데이터 검증과 같은 방식)."""
    null_edges, vals = [], []
    for sd in range(seeds):
        rng = np.random.default_rng(1000 + sd)
        Q = P.copy()
        Q["url"] = rng.permutation(Q.url.values)
        sc, _, _ = pair_scores(Q, win_h)
        null_edges.append(sc)
        vals.append(np.array([s for s, c in sc.values()]) if sc else np.array([0.0]))
    allv = np.concatenate(vals)
    tau = float(np.percentile(allv, pct)) if len(allv) else 0.0
    nf = []
    for sc in null_edges:
        edges = [(a, b) for (a, b), (s, c) in sc.items() if c >= MIN_SHARED and s >= tau]
        _, info = flag_components(edges)
        nf.append(int(sum(i["size"] for i in info if i["flagged"])))
    return tau, dict(null_pair_scores_n=int(len(allv)), null_flagged_accounts=nf, null_flagged_mean=float(np.mean(nf)))


def flag_components(edges, min_comp=MIN_COMP, min_density=MIN_DENSITY):
    """edges: [(a,b)] → (comps 리스트, 묶음별 (size, n_edges, density, flagged))"""
    comps = components(edges)
    idx = {}
    for k, c in enumerate(comps):
        for a in c:
            idx[a] = k
    ne = [0] * len(comps)
    for a, b in edges:
        ne[idx[a]] += 1
    info = []
    for k, c in enumerate(comps):
        n = len(c); poss = n * (n - 1) / 2
        dens = ne[k] / poss if poss else 0.0
        info.append(dict(size=n, n_edges=ne[k], density=round(dens, 3), flagged=bool(n >= min_comp and dens >= min_density)))
    return comps, info


def components(edges):
    parent = {}
    def find(x):
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for a, b in edges:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
    groups = {}
    for x in list(parent):
        groups.setdefault(find(x), set()).add(x)
    return sorted(groups.values(), key=len, reverse=True)


def run(posts, accounts=None, win_h=WINDOW_H, min_shared=MIN_SHARED, min_comp=MIN_COMP,
        null_seeds=NULL_SEEDS, tau=None):
    """posts: DataFrame(post_id, ts, account_id, url[, lang]). accounts: DataFrame(account_id, created_at) 선택.
    반환 dict(accounts=DataFrame, edges=DataFrame, components=DataFrame, summary=dict)"""
    P = posts.copy()
    P["ts"] = pd.to_datetime(P.ts)
    P["url"] = P.url.map(norm_url)
    P = P[P.url != ""].copy()
    P["dom"] = P.url.map(domain)
    n_posts_url = len(P)
    if n_posts_url == 0:
        return dict(accounts=pd.DataFrame(), edges=pd.DataFrame(), components=pd.DataFrame(),
                    summary=dict(n_posts_with_url=0))
    scores, sharers, N = pair_scores(P, win_h)
    null_info = {}
    if tau is None:
        tau, null_info = null_threshold(P, null_seeds, NULL_PCT, win_h)
    edges = [(a, b, s, c) for (a, b), (s, c) in scores.items() if c >= min_shared and s >= tau]
    E = pd.DataFrame(edges, columns=["a", "b", "score", "n_shared_urls"]).sort_values("score", ascending=False)
    comps, info = flag_components([(a, b) for a, b, _, _ in edges], min_comp)
    comp_of = {}
    comp_rows = []
    for k, c in enumerate(comps):
        for a in c:
            comp_of[a] = k
        comp_rows.append(dict(component=k, **info[k]))
    C = pd.DataFrame(comp_rows)
    # 계정별 지표
    dom_sharers = P.groupby("dom").account_id.nunique()
    rare_dom = set(dom_sharers[dom_sharers <= RARE_DOMAIN_SHARERS].index)
    deg = {}
    shared_urls = {}
    for a, b, s, c in edges:
        deg[a] = deg.get(a, 0) + 1; deg[b] = deg.get(b, 0) + 1
        shared_urls[a] = max(shared_urls.get(a, 0), c); shared_urls[b] = max(shared_urls.get(b, 0), c)
    rows = []
    for a, g in P.groupby("account_id"):
        k = comp_of.get(a, -1)
        size = len(comps[k]) if k >= 0 else 0
        rare_ratio = float((g.dom.isin(rare_dom)).mean())
        flagged = bool(info[k]["flagged"]) if k >= 0 else False
        ev = []
        if flagged:
            ev.append(f"희귀 링크 {shared_urls.get(a, 0)}개 이상을 계정 {deg.get(a, 0)}개와 {win_h}시간 안에 함께 공유")
            ev.append(f"URL 공유 묶음 크기 {size} · 밀도 {info[k]['density']:.2f}")
        if rare_ratio >= 0.8 and len(g) >= 2:
            ev.append(f"공유 링크의 {rare_ratio:.0%}가 희귀 도메인")
        rows.append(dict(account_id=a, n_url_posts=len(g), n_distinct_urls=g.url.nunique(),
                         component=k, component_size=size, degree=deg.get(a, 0),
                         max_shared_urls=shared_urls.get(a, 0), rare_domain_ratio=round(rare_ratio, 3),
                         urlnet_flag=flagged, evidence=" · ".join(ev)))
    A = pd.DataFrame(rows).sort_values(["urlnet_flag", "degree"], ascending=[False, False])
    if accounts is not None and "created_at" in accounts:
        A = A.merge(accounts[["account_id", "created_at"]], on="account_id", how="left")
    rare_max = max(3, int(RARE_FRAC * N))
    summary = dict(n_posts_with_url=int(n_posts_url), n_accounts_with_url=int(N), n_urls=int(len(sharers)),
                   rare_max_sharers=rare_max, n_rare_urls=int(sum(1 for u, n in sharers.items() if 2 <= n <= rare_max)),
                   window_h=win_h, min_shared_urls=min_shared, min_component=min_comp,
                   tau=round(tau, 4), tau_rule=f"URL 셔플 대조군 쌍 점수 {NULL_PCT} 백분위 (희귀 링크만 집계)",
                   n_edges=int(len(E)), n_components=int(len(comps)),
                   n_flagged_accounts=int(A.urlnet_flag.sum()),
                   min_density=MIN_DENSITY,
                   flagged_components=int(C["flagged"].sum()) if len(C) else 0, **null_info)
    return dict(accounts=A, edges=E, components=C, summary=summary, posts=P)


def main():
    os.makedirs(OUT, exist_ok=True)
    P = pd.read_csv(os.path.join(DATA, "posts.csv"), keep_default_na=False,
                    usecols=["post_id", "ts", "account_id", "lang", "url"])
    A = pd.read_csv(os.path.join(DATA, "accounts.csv"), usecols=["account_id", "created_at"])
    res = run(P, A)
    res["accounts"].to_csv(os.path.join(OUT, "urlnet_accounts.csv"), index=False)
    res["edges"].to_csv(os.path.join(OUT, "urlnet_edges.csv"), index=False)
    res["components"].to_csv(os.path.join(OUT, "urlnet_components.csv"), index=False)
    # 화면용: 묶음별 링크 목록(가명 계정만)
    P2 = res["posts"]
    fl = set(res["accounts"][res["accounts"].urlnet_flag].account_id)
    links = (P2[P2.account_id.isin(fl)].groupby("url").agg(n_accounts=("account_id", "nunique"),
             first_ts=("ts", "min")).reset_index().sort_values("n_accounts", ascending=False))
    res["summary"]["flagged_links"] = [dict(url=r.url, n_accounts=int(r.n_accounts), first_ts=str(r.first_ts))
                                       for r in links.head(12).itertuples()]
    json.dump(res["summary"], open(os.path.join(OUT, "urlnet_summary.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1, default=str)
    s = res["summary"]
    print(f"URL 게시 {s['n_posts_with_url']}건 · 링크 공유 계정 {s['n_accounts_with_url']} · 링크 {s['n_urls']}개")
    print(f"임계값 τ={s['tau']} ({s['tau_rule']}) · 대조군 묶임 계정 {s.get('null_flagged_accounts')}")
    print(f"간선 {s['n_edges']} · 묶음 {s['n_components']} · 의심 묶음 {s['flagged_components']} · 의심 계정 {s['n_flagged_accounts']}")


if __name__ == "__main__":
    main()
