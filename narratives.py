"""
narratives.py — M2 다국어 서사 클러스터링 + 출처 연결

입력 : data/posts.csv                      (truth_* 컬럼은 읽지 않는다. --dev 일 때만 순도 출력)
출력 : out/posts_nar.csv   post_id, narrative_id(-1=서사 아님), sim_to_centroid
       out/sources.json    서사별 출처 후보(외국어 게시물), 한국어 최초 게시, 시간차, 공유 URL
       out/emb.npy         임베딩 캐시 (모델 로딩 시간 절약)

실행 :
  python narratives.py                    # 다국어 MiniLM (권장, 처음 1회 모델 다운로드)
  python narratives.py --thr 0.45         # 클러스터 거리 임계값 조정 (코사인 거리, 작을수록 엄격)
  python narratives.py --dev              # 개발용: truth 라벨 대비 순도 출력 (평가·튜닝 전용)
  python narratives.py --embed hash       # 모델 없이 도는 대체 임베딩 (교차언어 연결은 안 됨, 코드 점검용)

설계 메모
  - 서사는 두 경로로 정한다. ① 의미: 부모가 없는 한국어 게시물(뿌리)을 다국어 임베딩으로 군집화
    ② 대화 구조: 리포스트·답글·인용(parent_id)으로 이어진 게시물은 부모의 서사를 상속.
    이유: 짧은 구어체 한국어에서는 임베딩이 주제보다 문체를 크게 반영해 서로 다른 주제가 섞였다
    (맥 실측: 방위비 반응 글끼리 0.62, 방위비-급식 0.61). 한계: 링크 없이 같은 주장을 쓴 글은 ①에만 의존.
  - 한국어 게시물만 먼저 군집화하고, 외국어 게시물은 가장 가까운 서사 중심에 붙인다.
    (외국어 게시물이 4건뿐이라 따로 군집화하면 최소 크기 조건에서 사라진다)
  - 서사 = 크기 >= MIN_SIZE 인 군집. 잡담 템플릿도 군집이 되지만 M3/M4에서
    '외국어 출처 + 조정 신호'가 없으면 경보 후보가 되지 못한다.
"""
import argparse, json, os, sys
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA, OUT = os.path.join(HERE, "data"), os.path.join(HERE, "out")
MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
MIN_SIZE = int(os.environ.get("FIMI_MIN_SIZE", "8"))  # 서사로 인정할 최소 한국어 게시물 수 (합성 시연 기본 8, 실시간 표본은 live/analyze.py가 3으로 낮춤)
ATTACH_SIM = 0.50     # 외국어 게시물을 서사에 붙이는 최소 코사인 유사도


def embed(texts, kind):
    if kind == "hash":  # 코드 점검용: 문자 2~3-gram 해싱 (교차언어 불가)
        from sklearn.feature_extraction.text import HashingVectorizer
        hv = HashingVectorizer(analyzer="char", ngram_range=(2, 3), n_features=2048,
                               alternate_sign=False, norm="l2")
        return hv.transform(texts).toarray().astype(np.float32)
    from sentence_transformers import SentenceTransformer
    m = SentenceTransformer(MODEL)
    return m.encode(list(texts), batch_size=64, normalize_embeddings=True,
                    show_progress_bar=True).astype(np.float32)


def cluster_ko(E, thr):
    from sklearn.cluster import AgglomerativeClustering
    try:
        ac = AgglomerativeClustering(n_clusters=None, metric="cosine", linkage="average",
                                     distance_threshold=thr)
    except TypeError:  # 구버전 sklearn
        ac = AgglomerativeClustering(n_clusters=None, affinity="cosine", linkage="average",
                                     distance_threshold=thr)
    return ac.fit_predict(E)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--thr", type=float, default=0.55)   # 맥 실측 튜닝값
    ap.add_argument("--merge", type=float, default=0.70,
                    help="군집 중심 코사인 유사도가 이 값 이상이면 같은 서사로 병합")
    ap.add_argument("--embed", default="model", choices=["model", "hash"])
    ap.add_argument("--no-propagate", action="store_true",
                    help="대화 구조(리포스트·답글·인용) 상속을 끄고 의미 유사도만으로 서사를 정함")
    ap.add_argument("--dev", action="store_true")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)

    cols = ["post_id", "ts", "account_id", "lang", "platform", "text", "url", "parent_id"]
    P = pd.read_csv(os.path.join(DATA, "posts.csv"), parse_dates=["ts"], keep_default_na=False)
    truth = P[["post_id", "truth_narrative"]].copy() if a.dev else None
    P = P[cols].reset_index(drop=True)

    cache = os.path.join(OUT, f"emb_{a.embed}.npy")
    if os.path.exists(cache) and np.load(cache).shape[0] == len(P):
        E = np.load(cache)
    else:
        E = embed(P.text.values, a.embed)
        np.save(cache, E)

    ko = (P.lang == "ko").values
    root = (P.parent_id == "").values if not a.no_propagate else np.ones(len(P), dtype=bool)
    idx_ko, idx_fo = np.where(ko & root)[0], np.where(~ko)[0]
    lab_ko = cluster_ko(E[idx_ko], a.thr)

    # 서사 후보: 크기 >= MIN_SIZE
    sizes = pd.Series(lab_ko).value_counts()
    keep = sorted(sizes[sizes >= MIN_SIZE].index)
    nid_of = {c: i for i, c in enumerate(keep)}
    nar = np.full(len(P), -1, dtype=int)
    for pos, c in zip(idx_ko, lab_ko):
        nar[pos] = nid_of.get(c, -1)

    # 병합: 중심 벡터가 가까운 군집은 같은 서사의 변형으로 보고 합친다 (union-find)
    parent = list(range(len(keep)))
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    cs = []
    for n in range(len(keep)):
        v = E[nar == n].mean(axis=0)
        cs.append(v / (np.linalg.norm(v) + 1e-9))
    for i in range(len(cs)):
        for j in range(i + 1, len(cs)):
            if float(cs[i] @ cs[j]) >= a.merge:
                parent[find(j)] = find(i)
    roots = sorted({find(i) for i in range(len(keep))})
    remap = {r: k for k, r in enumerate(roots)}
    nar = np.array([remap[find(x)] if x >= 0 else -1 for x in nar], dtype=int)
    keep = roots

    # 서사 중심 벡터
    cent = {}
    for n in range(len(keep)):
        v = E[nar == n].mean(axis=0)
        cent[n] = v / (np.linalg.norm(v) + 1e-9)

    sim = np.zeros(len(P), dtype=np.float32)
    for n, v in cent.items():
        m = nar == n
        sim[m] = E[m] @ v
    # 외국어 게시물 → 가장 가까운 서사 중심 (유사도 미달이면 -1)
    for pos in idx_fo:
        if not cent:
            break
        ns = list(cent.keys())
        s = np.array([E[pos] @ cent[n] for n in ns])
        j = int(s.argmax())
        if s[j] >= ATTACH_SIM:
            nar[pos], sim[pos] = ns[j], s[j]
        else:
            sim[pos] = s[j]

    # 대화 구조 상속: 부모가 있는 게시물은 부모의 서사를 물려받는다 (시간순 처리)
    if not a.no_propagate:
        pos_of = {pid: i for i, pid in enumerate(P.post_id)}
        for i in np.argsort(P.ts.values, kind="stable"):
            par = P.parent_id.iat[i]
            if par and par in pos_of and nar[i] == -1 and P.lang.iat[i] == "ko":
                nar[i] = nar[pos_of[par]]
                n = nar[i]
                if n in cent:
                    sim[i] = float(E[i] @ cent[n])

    R = P[["post_id"]].copy()
    R["narrative_id"], R["sim_to_centroid"] = nar, np.round(sim, 4)
    R.to_csv(os.path.join(OUT, "posts_nar.csv"), index=False)

    # 출처 후보: 서사 안의 외국어 게시물, 한국어 최초 게시, 시간차, 공유 URL
    src = {}
    P["nar"] = nar
    for n in cent:
        g = P[P.nar == n]
        kg, fg = g[g.lang == "ko"], g[g.lang != "ko"]
        if kg.empty:
            continue
        first_ko = kg.ts.min()
        url_share = (kg[kg.url != ""].url.value_counts().head(3)).to_dict()
        fo = [dict(post_id=r.post_id, lang=r.lang, ts=str(r.ts), account_id=r.account_id,
                   url=r.url, sim=float(sim[i]))
              for i, r in fg.sort_values("ts").iterrows()]
        first_fo_ts = fg.ts.min() if len(fg) else None
        src[str(n)] = dict(
            n_posts_ko=int(len(kg)), n_foreign=int(len(fg)),
            first_ko_ts=str(first_ko), first_foreign_ts=str(first_fo_ts) if first_fo_ts is not None else None,
            lead_hours=(round((first_ko - first_fo_ts).total_seconds() / 3600, 2)
                        if first_fo_ts is not None else None),   # 외국어 원문이 몇 시간 앞섰나
            foreign=fo, shared_urls=url_share,
            sample=kg.sort_values("ts").text.iloc[0][:80])
    with open(os.path.join(OUT, "sources.json"), "w", encoding="utf-8") as f:
        json.dump(src, f, ensure_ascii=False, indent=2)

    print(f"posts={len(P)} ko={len(idx_ko)} foreign={len(idx_fo)}  "
          f"clusters(ko)={len(set(lab_ko))}  narratives(size>={MIN_SIZE})={len(keep)}")
    for n, v in sorted(src.items(), key=lambda kv: -kv[1]["n_posts_ko"])[:10]:
        print(f"  N{n}: ko={v['n_posts_ko']:4d} foreign={v['n_foreign']} lead_h={v['lead_hours']}  {v['sample']}")

    if a.dev:  # 평가·튜닝 전용: 정답 라벨을 여기서만 본다
        T = truth.merge(R, on="post_id")
        print("\n[DEV] 서사별 truth 구성 (행=narrative_id)")
        print(pd.crosstab(T.narrative_id, T.truth_narrative).to_string())


if __name__ == "__main__":
    main()
