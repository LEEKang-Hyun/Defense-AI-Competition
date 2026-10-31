"""
coord_decay.py — 제3 신호층: 시간 감쇠 다층(multiplex) 협업 가중치 조정 탐지 (2026-10-26 추가)

왜: 기존 coordination.py는 '10분 창 안에 8계정 이상'이라는 고정 창을 쓴다. 실험 2a에서 공작 계정이 게시 시각을 ±20분만
    흩뜨려도 재현율 0.90→0.18로 무너졌다. 이 모듈은 창을 두지 않는다. 두 계정이 같은 대상(같은 URL · 거의 같은 문장 ·
    같은 글의 리포스트)에 행동할 때마다 시간 간격 Δt에 지수 감쇠 exp(-Δt/τ)를 곱한 가중치를 쌓는다.
    (선례: Detecting Coordinated Activities Through Temporal, Multiplex, and Collaborative Analysis, arXiv 2512.19677 —
     Newman 협업 가중치 + 층별 시간 감쇠 + 다층 군집. 이 구현은 τ 선택을 모듈성 대신 '시간 셔플 대조군 대비 신호비'로 한다.)

층(layer)  url  : 같은 URL을 올린 계정 쌍          text : 글자 3-gram TF-IDF 코사인 ≥ TEXT_SIM 인 글을 올린 계정 쌍
           repost: 같은 뿌리 글을 리포스트한 계정 쌍(parent_id)
가중치     한 '대상'에 k개 계정이 참여하면 쌍마다 exp(-Δt/τ)/(k-1) (Newman 정규화: 인기 대상일수록 쌍 하나의 값이 작다)
귀무모형   계정별 게시 시각을 서사 안에서 무작위로 섞은 대조군 N_SHUF회 → 층별·대상 크기(k) 구간별 쌍 가중치의 p99.9 = 1.0 단위로
           정규화 (정규화 값 ≥ 1 = '우연으로는 거의 안 나오는 연결'). k 구간을 나누는 이유: 1/(k-1) 때문에 큰 대상(인기 URL)의
           쌍 가중치는 원래 작아서, 전체 p99.9 하나로 재면 큰 대상의 조정이 가려진다. 대조군은 텍스트·URL은 그대로 두고 시각만 섞는다.
τ 선택     층별로 τ ∈ TAU_GRID 중 정규화 후 '우연 이상' 초과분 Σmax(정규화값-1, 0)이 최대인 값
           (= 그 τ에서 대조군을 넘는 연결이 가장 많이 남는 값. 공작이 시각을 흩뜨리면 τ가 자동으로 길어진다)
판정       정규화 가중치 합 ≥ EDGE_MIN 인 간선만 남긴 그래프에서 Louvain 군집. 군집 크기 ≥ COMM_MIN 이고
           계정의 정규화 가중 차수 ≥ DEG_MIN 이며 '우연 이상' 공동 행동이 서로 다른 시간대(간격 > EPISODE_GAP분) 2곳 이상이면
           suspected_decay (기존 'burst 2회 이상' 반복 조건의 창 없는 판: 팬덤의 1회 합의 동시 게시는 review_decay에 머문다)
입력      data/posts.csv (truth_* 읽지 않음), data/accounts.csv(created_at), out/posts_nar.csv
출력      out/coord_decay_accounts.csv  계정×서사: 층별 차수, 정규화 차수, 군집, 등급, 근거
          out/coord_decay_edges.csv     계정 쌍: 층별 정규화 가중치, 합
          out/coord_decay_summary.json  층별 τ·임계값·대조군 통계
실행      python coord_decay.py [--data DIR --out DIR]   (필요 패키지: pandas numpy scikit-learn networkx)
주의      기존 out/accounts_score.csv·alerts·동결 숫자는 건드리지 않는다. 화면에서는 '제3 신호층'으로 따로 보인다.
"""
import os, sys, json, argparse
import numpy as np
import pandas as pd
import networkx as nx
from sklearn.feature_extraction.text import TfidfVectorizer

HERE = os.path.dirname(os.path.abspath(__file__))
TAU_GRID = [10, 30, 60, 180, 360, 1440]      # 분
TEXT_SIM = 0.6
N_SHUF = 20
NULL_Q = 0.99
EDGE_MIN = 1.0
DEG_MIN = 2.0
COMM_MIN = 5
EPISODE_GAP = 60      # 분: 공동 행동 시각을 이 간격으로 묶어 '서로 다른 시간대' 수를 센다
EPISODE_MIN = 2
EPISODE_FRAC = 0.25    # 한 시간대를 '군집의 공동 행동'으로 치려면 군집 계정의 이 비율(최소 3개) 이상이 참여해야 한다
LAYERS = ("url", "text", "repost")
K_BUCKETS = [(2, 2), (3, 5), (6, 15), (16, 10**9)]


def kb(k):
    for i, (lo, hi) in enumerate(K_BUCKETS):
        if lo <= k <= hi:
            return i
    return len(K_BUCKETS) - 1


def events(g):
    """서사 g(한국어 게시물)에서 층별 '대상 → [(계정, 시각)]' 목록을 만든다."""
    ev = {l: {} for l in LAYERS}
    for r in g.itertuples():
        if r.url:
            ev["url"].setdefault(r.url, []).append((r.account_id, r.ts))
        if r.parent_id:
            ev["repost"].setdefault(r.parent_id, []).append((r.account_id, r.ts))
    # text: 근사 중복 글 묶음(연결 성분) — 뿌리 글만(리포스트는 parent로 이미 잡힘)
    root = g[g.parent_id == ""]
    if len(root) >= 2:
        vec = TfidfVectorizer(analyzer="char", ngram_range=(3, 3), min_df=1)
        X = vec.fit_transform(root.text.values)
        S = (X @ X.T).tocoo()
        H = nx.Graph()
        for i, j, v in zip(S.row, S.col, S.data):
            if i < j and v >= TEXT_SIM:
                H.add_edge(i, j)
        ids, ts, ac = root.post_id.values, root.ts.values, root.account_id.values
        for k, comp in enumerate(nx.connected_components(H)):
            ev["text"][f"t{k}"] = [(ac[i], pd.Timestamp(ts[i])) for i in comp]
    return ev


def pair_weights(ev_layer, tau, times=None, kinfo=None):
    """한 층의 대상들에서 쌍 가중치 dict {(a,b): w}. 같은 계정이 한 대상에 여러 번이면 가장 가까운 시각 하나만 센다.
    times(dict)를 주면 쌍별 공동 행동 시각 목록 {(a,b): [(t_a, 기여값)]}을 채운다."""
    W = {}
    kof = {} if kinfo is None else kinfo
    for _, lst in ev_layer.items():
        best = {}
        for a, t in lst:
            best.setdefault(a, []).append(t)
        acc = sorted(best)
        k = len(acc)
        if k < 2:
            continue
        for x in range(k):
            for y in range(x + 1, k):
                a, b = acc[x], acc[y]
                ta_, tb_ = min(((ta, tb) for ta in best[a] for tb in best[b]), key=lambda p: abs((p[0] - p[1]).total_seconds()))
                dt = abs((ta_ - tb_).total_seconds()) / 60.0
                c = np.exp(-dt / tau) / (k - 1)
                W[(a, b)] = W.get((a, b), 0.0) + c
                if c >= kof.get((a, b), (0.0, 0))[0]:
                    kof[(a, b)] = (c, k)
                if times is not None:
                    times.setdefault((a, b), []).append((min(ta_, tb_), c, dt))
    return W


def shuffle_times(g, rng):
    g2 = g.copy()
    g2["ts"] = rng.permutation(g.ts.values)
    return g2


def run_narrative(g, rng):
    """반환: edges(DataFrame), per-layer info"""
    ev = events(g)
    shuf = [events(shuffle_times(g, rng)) for _ in range(N_SHUF)]
    info, norm, co_times, pair_times = {}, {}, {}, {}
    for l in LAYERS:
        best = None
        for tau in TAU_GRID:
            kreal = {}
            real = pair_weights(ev[l], tau, kinfo=kreal)
            tot = sum(real.values())
            knull = [{} for _ in shuf]
            nulls = [pair_weights(s[l], tau, kinfo=kn) for s, kn in zip(shuf, knull)]
            null_tot = np.mean([sum(n.values()) for n in nulls]) if nulls else 0.0
            # k 구간별 귀무 p99.9 → 정규화 → '우연 이상' 초과분의 합 = 이 τ에서의 탐지 수확
            byb = {i: [] for i in range(len(K_BUCKETS))}
            for n, kn in zip(nulls, knull):
                for pr, v in n.items():
                    byb[kb(kn[pr][1])].append(v)
            allv = np.array([v for n in nulls for v in n.values()])
            qg = float(np.quantile(allv, NULL_Q)) if len(allv) else 1e-6
            qb = {i: max((float(np.quantile(np.array(v), NULL_Q)) if len(v) >= 50 else qg), 1e-6) for i, v in byb.items()}
            nrm = {pr: v / qb[kb(kreal[pr][1])] for pr, v in real.items()}
            excess = float(sum(max(v - 1.0, 0.0) for v in nrm.values()))
            if best is None or excess > best["excess"]:
                best = dict(tau=tau, excess=excess, real=real, tot=tot, null_tot=null_tot, nrm=nrm, qb=qb, qg=qg)
        norm[l] = best["nrm"]; qb = best["qb"]; q = best["qg"]
        best["snr"] = best["tot"] / best["null_tot"] if best["null_tot"] > 0 else float("inf")
        tl = {}
        pair_weights(ev[l], best["tau"], times=tl)
        pair_times[l] = tl
        info[l] = dict(tau_min=best["tau"], excess=round(best["excess"], 2), snr=(None if not np.isfinite(best["snr"]) else round(float(best["snr"]), 2)),
                       real_total=round(float(best["tot"]), 3), null_total_mean=round(float(best["null_tot"]), 3),
                       null_p999=round(q, 5), null_p999_by_k={str(K_BUCKETS[i]): round(v, 5) for i, v in qb.items()}, n_pairs=len(best["real"]))
    keys = set().union(*[set(norm[l]) for l in LAYERS])
    rows = [dict(a=a, b=b, **{l: round(norm[l].get((a, b), 0.0), 3) for l in LAYERS}) for (a, b) in keys]
    E = pd.DataFrame(rows, columns=["a", "b", *LAYERS])
    if len(E):
        E["w"] = E[list(LAYERS)].sum(axis=1).round(3)
        for r in E[E.w >= EDGE_MIN].itertuples():
            for l in LAYERS:
                for t, c, dt in pair_times[l].get((r.a, r.b), []):
                    if dt <= info[l]["tau_min"] * 0.7:      # 거의 동시(감쇠 ≥ 0.5)인 공동 행동만 '시간대'로 센다
                        co_times.setdefault((r.a, r.b), []).append(t)
    else:
        E["w"] = []
    return E, info, co_times   # co_times: 쌍 → 공동 행동 시각 (같은 군집 안의 쌍만 세는 건 main에서)


def n_episodes(ts_list, gap_min=EPISODE_GAP):
    if not ts_list:
        return 0
    t = sorted(ts_list); n = 1
    for i in range(1, len(t)):
        if (t[i] - t[i - 1]).total_seconds() / 60.0 > gap_min:
            n += 1
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=os.path.join(HERE, "data"))
    ap.add_argument("--out", default=os.path.join(HERE, "out"))
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    rng = np.random.default_rng(a.seed)
    P = pd.read_csv(os.path.join(a.data, "posts.csv"), parse_dates=["ts"], keep_default_na=False,
                    usecols=["post_id", "ts", "account_id", "lang", "text", "url", "parent_id"])
    N = pd.read_csv(os.path.join(a.out, "posts_nar.csv"))
    P = P.merge(N[["post_id", "narrative_id"]], on="post_id")
    P = P[(P.lang == "ko") & (P.narrative_id >= 0)].sort_values("ts").reset_index(drop=True)
    acc_rows, edge_rows, summary = [], [], {}
    for nid, g in P.groupby("narrative_id"):
        E, info, pair_co = run_narrative(g.reset_index(drop=True), rng)
        summary[int(nid)] = info
        G = nx.Graph()
        for r in E[E.w >= EDGE_MIN].itertuples():
            G.add_edge(r.a, r.b, weight=r.w)
        comm = {}
        if G.number_of_edges():
            for k, c in enumerate(nx.community.louvain_communities(G, weight="weight", seed=a.seed)):
                for n in c:
                    comm[n] = (k, len(c))
        deg = dict(G.degree(weight="weight")) if G.number_of_edges() else {}
        # 서로 다른 시간대 수: 군집 단위로 센다. 같은 군집 안의 쌍이 거의 동시에 행동한 시각들을 EPISODE_GAP으로 묶고,
        # 군집 계정의 EPISODE_FRAC(최소 3개) 이상이 참여한 묶음만 '공동 행동 시간대'로 인정한다 (두 계정의 우연한 잡담 겹침 제외)
        ep_count = {}
        byc = {}
        for (x, y), ts_ in pair_co.items():
            if x in comm and y in comm and comm[x][0] == comm[y][0]:
                for t in ts_:
                    byc.setdefault(comm[x][0], []).append((t, x, y))
        for c, lst in byc.items():
            size = next(sz for (cc, sz) in comm.values() if cc == c)
            need = max(3, int(np.ceil(EPISODE_FRAC * size)))
            lst.sort(key=lambda z: z[0])
            clusters, cur = [], [lst[0]]
            for z in lst[1:]:
                if (z[0] - cur[-1][0]).total_seconds() / 60.0 > EPISODE_GAP:
                    clusters.append(cur); cur = [z]
                else:
                    cur.append(z)
            clusters.append(cur)
            for cl in clusters:
                accts = set(a for _, a, b in cl) | set(b for _, a, b in cl)
                if len(accts) >= need:
                    for a_ in accts:
                        ep_count[a_] = ep_count.get(a_, 0) + 1
        for acct in g.account_id.unique():
            d = float(deg.get(acct, 0.0))
            k, size = comm.get(acct, (-1, 0))
            lay = {l: round(float(E.loc[((E.a == acct) | (E.b == acct)) & (E[l] >= EDGE_MIN), l].sum()), 2) for l in LAYERS} if len(E) else {l: 0.0 for l in LAYERS}
            ep = ep_count.get(acct, 0)
            tier = "suspected_decay" if (size >= COMM_MIN and d >= DEG_MIN and ep >= EPISODE_MIN) else ("review_decay" if size >= COMM_MIN else "normal")
            ev = [f"{l} 층 우연 이상 연결 {lay[l]:.1f}" for l in LAYERS if lay[l] >= EDGE_MIN]
            if ep:
                ev.append(f"서로 다른 시간대 {ep}곳에서 공동 행동")
            if size >= COMM_MIN:
                ev.append(f"군집 {k} (크기 {size})")
            acc_rows.append(dict(account_id=acct, narrative_id=int(nid), deg_norm=round(d, 2), community=k, comm_size=size, n_episodes=ep,
                                 **{f"deg_{l}": lay[l] for l in LAYERS}, tier=tier, evidence=" / ".join(ev)))
        for r in E[E.w >= EDGE_MIN].itertuples():
            edge_rows.append(dict(narrative_id=int(nid), a=r.a, b=r.b, **{l: getattr(r, l) for l in LAYERS}, w=r.w))
        print(f"narrative {nid}: posts={len(g)} edges≥{EDGE_MIN}={G.number_of_edges()} "
              f"suspected={sum(1 for x in acc_rows if x['narrative_id']==nid and x['tier']=='suspected_decay')} "
              f"tau={ {l: info[l]['tau_min'] for l in LAYERS} }", flush=True)
    pd.DataFrame(acc_rows).to_csv(os.path.join(a.out, "coord_decay_accounts.csv"), index=False)
    pd.DataFrame(edge_rows, columns=["narrative_id", "a", "b", *LAYERS, "w"]).to_csv(os.path.join(a.out, "coord_decay_edges.csv"), index=False)
    json.dump(dict(params=dict(TAU_GRID=TAU_GRID, TEXT_SIM=TEXT_SIM, N_SHUF=N_SHUF, NULL_Q=NULL_Q, EDGE_MIN=EDGE_MIN,
                               DEG_MIN=DEG_MIN, COMM_MIN=COMM_MIN, EPISODE_GAP=EPISODE_GAP, EPISODE_MIN=EPISODE_MIN), narratives=summary),
              open(os.path.join(a.out, "coord_decay_summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
