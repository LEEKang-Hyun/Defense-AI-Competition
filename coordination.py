"""
coordination.py — M3 조정 신호 · 계정 그래프

입력 : data/posts.csv (truth_* 읽지 않음), data/accounts.csv (account_id, created_at만 읽음),
       out/posts_nar.csv (M2 결과)
출력 : out/bursts.csv         서사별 '짧은 시간에 몰린 게시' 구간 (근거 카드의 타임라인 재료)
       out/accounts_score.csv (계정×서사) 신호 4종, 점수, 등급(suspected / review / normal), 근거 문자열
       out/coord_edges.csv    같은 burst에 함께 등장한 계정 쌍과 횟수 (그래프 화면용)

신호 (내용이 아니라 행동만 본다)
  young       서사 첫 게시 시점의 계정 나이가 짧을수록 1에 가까움 (45일 기준)
  burst       몇 번의 burst에 참여했나 (2회 이상이면 만점)
  burst_sim   burst 안에서 다른 계정의 글과 문장이 얼마나 비슷한가 (복붙·원고 변형)
  url_share   burst 안에서 같은 URL을 3개 이상 계정이 공유했나
점수 = 0.30 young + 0.30 burst + 0.25 burst_sim + 0.15 url_share   (가중치는 가정이며 M7에서 민감도 확인)
등급 : suspected >= 0.60 이면서 burst 2회 이상 / review 0.40 이상 / normal
       (개발 중 발견한 오탐: 새벽에 우연히 8건이 몰린 burst에 신생 계정 1개가 걸림 → 반복 조건 추가)
       신호 하나(예: 신생 계정)만으로는 review에도 못 오르도록 가중치를 잡았다 → 자연스러운 예외 완화

실행 : python coordination.py          (필요 패키지: pandas numpy scikit-learn)
"""
import os
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

HERE = os.path.dirname(os.path.abspath(__file__))
DATA, OUT = os.path.join(HERE, "data"), os.path.join(HERE, "out")

WIN = pd.Timedelta(minutes=10)     # burst 창
CONTEXT = pd.Timedelta(hours=6)    # 기준 비율을 재는 앞뒤 범위
MIN_DISTINCT = 8                   # burst로 보려면 서로 다른 계정 최소 수
MIN_RATIO = 5.0                    # 주변 평균 대비 몇 배 이상 몰려야 하나
YOUNG_DAYS = 45
W = dict(young=0.30, burst=0.30, burst_sim=0.25, url_share=0.15)
SUSPECT, REVIEW = 0.60, 0.40


def find_bursts(g):
    """g: 한 서사의 한국어 게시물(ts 오름차순). 반환: burst 리스트 [(게시물 index 배열)]"""
    ts = g.ts.values
    n = len(g)
    acc = g.account_id.values
    marked = np.zeros(n, dtype=bool)
    ts_ns = ts.astype("datetime64[ns]").astype("int64")
    win, ctx = WIN.value, CONTEXT.value
    j = 0
    for i in range(n):
        end = np.searchsorted(ts_ns, ts_ns[i] + win, side="right")
        cnt = end - i
        if cnt < MIN_DISTINCT:
            continue
        if len(set(acc[i:end])) < MIN_DISTINCT:
            continue
        lo = np.searchsorted(ts_ns, ts_ns[i] - ctx, side="left")
        hi = np.searchsorted(ts_ns, ts_ns[i] + ctx, side="right")
        context_n = (hi - lo) - cnt
        rate = max(context_n / (2 * ctx / win), 0.25)    # 10분당 기준 게시 수
        if cnt / rate >= MIN_RATIO:
            marked[i:end] = True
    # 연속 구간 묶기
    bursts, cur = [], []
    for i in np.where(marked)[0]:
        if cur and ts_ns[i] - ts_ns[cur[-1]] > win:
            bursts.append(np.array(cur)); cur = []
        cur.append(i)
    if cur:
        bursts.append(np.array(cur))
    return bursts


def burst_text_sim(texts, accts):
    """burst 안 각 게시물이 '다른 계정'의 게시물과 갖는 상위 3개 평균 유사도"""
    if len(texts) < 2:
        return np.zeros(len(texts))
    X = TfidfVectorizer(analyzer="char", ngram_range=(2, 4)).fit_transform(texts)
    S = (X @ X.T).toarray()
    accts = np.asarray(accts)
    S[accts[:, None] == accts[None, :]] = 0.0           # 같은 계정끼리는 제외
    top = np.sort(S, axis=1)[:, -3:]
    return top.mean(axis=1)


def main():
    os.makedirs(OUT, exist_ok=True)
    P = pd.read_csv(os.path.join(DATA, "posts.csv"), parse_dates=["ts"], keep_default_na=False,
                    usecols=["post_id", "ts", "account_id", "lang", "text", "url"])
    A = pd.read_csv(os.path.join(DATA, "accounts.csv"), parse_dates=["created_at"],
                    usecols=["account_id", "created_at"])
    N = pd.read_csv(os.path.join(OUT, "posts_nar.csv"))
    P = P.merge(N[["post_id", "narrative_id"]], on="post_id").merge(A, on="account_id", how="left")
    P = P[(P.lang == "ko") & (P.narrative_id >= 0)].sort_values("ts").reset_index(drop=True)

    burst_rows, rows, edge_cnt, member_rows = [], [], {}, []
    for nid, g in P.groupby("narrative_id"):
        g = g.sort_values("ts").reset_index(drop=True)
        bursts = find_bursts(g)
        n_b, sim_best, url_flag = {}, {}, {}
        for k, idx in enumerate(bursts):
            b = g.iloc[idx]
            sims = burst_text_sim(b.text.values, b.account_id.values)
            url_n = b[b.url != ""].groupby("url").account_id.nunique()
            shared = set(url_n[url_n >= 3].index)
            burst_rows.append(dict(narrative_id=nid, burst_id=k, start=b.ts.min(), end=b.ts.max(),
                                   n_posts=len(b), n_accounts=b.account_id.nunique(),
                                   mean_text_sim=round(float(sims.mean()), 3),
                                   top_url=(url_n.idxmax() if len(url_n) else "")))
            for a, s, u in zip(b.account_id.values, sims, b.url.values):
                n_b[a] = n_b.get(a, 0) + 1
                sim_best[a] = max(sim_best.get(a, 0.0), float(s))
                if u in shared:
                    url_flag[a] = 1
            members = sorted(set(b.account_id.values))
            for a in members:
                member_rows.append(dict(narrative_id=nid, burst_id=k, account_id=a, burst_end=b.ts.max()))
            for x in range(len(members)):
                for y in range(x + 1, len(members)):
                    key = (nid, members[x], members[y])
                    edge_cnt[key] = edge_cnt.get(key, 0) + 1

        first = g.groupby("account_id").agg(first_ts=("ts", "min"), created=("created_at", "first"),
                                            n_posts=("post_id", "count"))
        for a, r in first.iterrows():
            age = (r.first_ts - r.created).days if pd.notna(r.created) else 9999
            young = float(np.clip(1 - age / YOUNG_DAYS, 0, 1))
            nb = n_b.get(a, 0)
            burst = min(nb / 2.0, 1.0)
            bsim = float(np.clip((sim_best.get(a, 0.0) - 0.3) / 0.4, 0, 1)) if nb else 0.0
            url = float(url_flag.get(a, 0))
            score = W["young"] * young + W["burst"] * burst + W["burst_sim"] * bsim + W["url_share"] * url
            # suspected는 '반복된' 조정(burst 2회 이상)만. 우연한 1회 동시 게시는 점수가 높아도 review로 둔다
            tier = "suspected" if (score >= SUSPECT and nb >= 2) else ("review" if score >= REVIEW else "normal")
            ev = []
            if young > 0.5: ev.append(f"신생 계정(게시 시점 {age}일)")
            if nb: ev.append(f"동시 게시 burst {nb}회 참여")
            if bsim > 0.3: ev.append(f"burst 내 문장 유사도 {sim_best[a]:.2f}")
            if url: ev.append("burst 내 동일 URL 공유")
            rows.append(dict(account_id=a, narrative_id=nid, age_days=age, young=round(young, 3),
                             n_bursts=nb, burst_sim=round(bsim, 3), url_share=url,
                             score=round(score, 3), tier=tier, n_posts=int(r.n_posts),
                             evidence=" / ".join(ev)))

    pd.DataFrame(burst_rows).to_csv(os.path.join(OUT, "bursts.csv"), index=False)
    pd.DataFrame(member_rows).to_csv(os.path.join(OUT, "burst_members.csv"), index=False)
    S = pd.DataFrame(rows)
    S.to_csv(os.path.join(OUT, "accounts_score.csv"), index=False)
    pd.DataFrame([dict(narrative_id=k[0], a=k[1], b=k[2], co_bursts=v) for k, v in edge_cnt.items()]) \
        .to_csv(os.path.join(OUT, "coord_edges.csv"), index=False)

    print(f"bursts={len(burst_rows)}  account-rows={len(S)}")
    print(S.groupby(["narrative_id", "tier"]).size().unstack(fill_value=0).to_string())


if __name__ == "__main__":
    main()
