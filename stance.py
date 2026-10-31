"""
stance.py — 서사별 '대상 고정' 입장 판별 → R̂를 '찬성 확산(하한)'과 '전체(상한)'으로 분리 (2026-10-26 추가)

왜: 임베딩 서사 묶기는 주제는 잡지만 입장은 못 가른다. 반박·팩트체크 답글도 같은 서사로 묶여 '확산'으로 집계된다
    (PRD 한계 9, 실험 3: 반박 50%면 경보가 20시간 이상 앞당겨짐). 그래서 지금 R̂는 상한값이다.
선례: LLM 제로샷 입장 판별(arXiv 2505.08464 서베이). 한국어 대규모 데이터 LASTIST(arXiv 2510.25783)는 '대상 독립' F1 0.37,
      '단일 대상' F1 0.956 — 범용 입장 모델은 안 되고, 서사(대상)마다 따로 물어야 한다는 뜻. 이 모듈은 그 설계를 따른다.

방법   서사마다 대상 주장(claim) = 외국어 원문/뿌리 글의 대표 문장(sources.json 또는 가장 많이 리포스트된 뿌리 글).
       각 한국어 글에 "이 주장에 대해 찬성·반박·무관 중 무엇인가"를 묻는다.
백엔드 --backend rules : 한국어 반박 어휘·구문 규칙(폴백, 정확도 미측정 — 손 라벨 표본으로 재야 함)
       --backend llm   : 환경변수 ANTHROPIC_API_KEY 가 있으면 Anthropic Messages API, 아니면 OPENAI_API_KEY 로 OpenAI 호환 API.
                         모델명은 LLM_MODEL. 글 40개씩 묶어 JSON으로 받는다. 키가 없으면 rules로 자동 폴백하고 그 사실을 기록.
       --backend file  : data/stance_labels.csv(post_id,stance)를 그대로 쓴다 (사람 라벨·실험용)
출력   out/stance.csv              post_id, narrative_id, stance(support/rebut/other), backend, hit(규칙 근거)
       out/r_series_stance.csv     서사×시각: p_gt08_all(기존=상한) / p_gt08_support(반박·무관 제외=하한), n_rebut_sofar
       out/stance_summary.json     서사별 입장 분포, 첫 ALERT 시각 (전체 vs 찬성만), 백엔드, 정확도(라벨 표본 있을 때)
정확도 data/stance_labels_sample.csv(post_id,stance) 에 사람이 라벨한 표본이 있으면 백엔드와 대조해 정확도·F1을 summary에 적는다.
       없으면 "정확도 미측정"으로 적는다 — 숫자를 지어내지 않는다.
실행   python stance.py [--backend rules|llm|file]      기존 out/·동결 숫자는 건드리지 않는다.
"""
import argparse, json, os, re, sys
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import alerts as AL

REBUT = [r"가짜", r"거짓", r"사실무근", r"사실이\s*아", r"팩트체크", r"팩트\s*확인", r"루머", r"찌라시", r"선동", r"조작", r"허위",
         r"근거\s*없", r"오보", r"낚시", r"믿지\s*마", r"속지\s*마", r"아닙니다", r"아니다", r"아니에요", r"아니던데", r"틀렸", r"왜곡",
         r"공작", r"프로파간다", r"출처가\s*어디", r"출처\s*없", r"번역기", r"중국\s*매체", r"러시아\s*매체", r"공식\s*입장은"]
OTHER = [r"^\s*$", r"ㅋㅋ+$", r"^\?+$"]
RE_REBUT = re.compile("|".join(REBUT)); RE_OTHER = re.compile("|".join(OTHER))


def claim_for(nid, gall, src):
    """서사의 대상 주장: sources.json의 외국어 원문 요약이 있으면 그것, 없으면 가장 많이 리포스트된 뿌리 글"""
    s = src.get(str(nid)) if isinstance(src, dict) else None
    if isinstance(s, dict):
        for k in ("claim", "summary", "title"):
            if s.get(k):
                return str(s[k])
    roots = gall[(gall.parent_id == "") & (gall.lang == "ko")]
    if len(roots):
        cnt = gall[gall.parent_id != ""].parent_id.value_counts()
        top = cnt[cnt.index.isin(roots.post_id)]
        if len(top):
            return roots.set_index("post_id").loc[top.index[0], "text"]
        return roots.text.iloc[0]
    return ""


def stance_rules(texts):
    out = []
    for t in texts:
        if RE_OTHER.search(t or ""):
            out.append(("other", "빈 글/감탄"))
        else:
            m = RE_REBUT.search(t or "")
            out.append(("rebut", f"반박 어휘 '{m.group(0)}'") if m else ("support", ""))
    return out


def stance_llm(claim, texts, model=None):
    import urllib.request
    akey, okey = os.environ.get("ANTHROPIC_API_KEY"), os.environ.get("OPENAI_API_KEY")
    if not (akey or okey):
        return None
    model = model or os.environ.get("LLM_MODEL") or ("claude-haiku-4-5" if akey else "gpt-4o-mini")
    out = []
    for i in range(0, len(texts), 40):
        chunk = texts[i:i + 40]
        prompt = ("다음은 하나의 주장과 그 주장에 대한 한국어 게시물 목록이다. 각 게시물이 주장을 '찬성/동조/불안 공유'(support), "
                  "'반박/의심/팩트체크'(rebut), '무관/판단 불가'(other) 중 무엇인지 분류하라. JSON 배열만 출력: "
                  "[{\"i\":번호,\"stance\":\"support|rebut|other\"}]\n\n주장: " + claim + "\n\n게시물:\n" +
                  "\n".join(f"{j}. {t}" for j, t in enumerate(chunk)))
        if akey:
            req = urllib.request.Request("https://api.anthropic.com/v1/messages", method="POST",
                                         headers={"x-api-key": akey, "anthropic-version": os.environ.get("ANTHROPIC_VERSION", "2023-06-01"), "content-type": "application/json"},
                                         data=json.dumps({"model": model, "max_tokens": 8000, "messages": [{"role": "user", "content": prompt}]}).encode())
            body = "".join(b.get("text", "") for b in json.loads(urllib.request.urlopen(req, timeout=60).read())["content"] if b.get("type") == "text")
        else:
            req = urllib.request.Request(os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1") + "/chat/completions", method="POST",
                                         headers={"authorization": f"Bearer {okey}", "content-type": "application/json"},
                                         data=json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0}).encode())
            body = json.loads(urllib.request.urlopen(req, timeout=60).read())["choices"][0]["message"]["content"]
        m = re.search(r"\[.*\]", body, re.S)
        arr = json.loads(m.group(0)) if m else []
        got = {int(x["i"]): x["stance"] for x in arr if x.get("stance") in ("support", "rebut", "other")}
        out += [(got.get(j, "other"), f"llm:{model}") for j in range(len(chunk))]
    return out


def measure(g, joined, grid, excl, fo_first, t0):
    rs = AL.pool_posterior(AL.r_series(g[~g.post_id.isin(excl)], joined, grid))
    rs["hour"] = ((rs.ts - t0) / pd.Timedelta(hours=1)).astype(int)
    return rs


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--backend", default="rules", choices=["rules", "llm", "file"])
    a = ap.parse_args()
    P, S, B, M, SRC = AL.load()
    t0 = P[P.narrative_id >= 0].ts.min().floor("D")
    grid = pd.date_range(t0 + AL.STEP, P[P.narrative_id >= 0].ts.max().ceil("h"), freq=AL.STEP)
    rows, series, summ = [], [], {"backend": a.backend, "narratives": {}}
    labels = None
    if a.backend == "file":
        labels = pd.read_csv(os.path.join(AL.DATA, "stance_labels.csv")).set_index("post_id").stance.to_dict()
    sample_p = os.path.join(AL.DATA, "stance_labels_sample.csv")
    sample = pd.read_csv(sample_p).set_index("post_id").stance.to_dict() if os.path.exists(sample_p) else {}
    for nid in sorted(P[P.narrative_id >= 0].narrative_id.unique()):
        gall = P[P.narrative_id == nid]; g = gall[gall.lang == "ko"]
        claim = claim_for(nid, gall, SRC)
        texts = g.text.tolist()
        if a.backend == "file":
            st = [(labels.get(p, "support"), "file") for p in g.post_id]
            used = "file"
        elif a.backend == "llm":
            st = stance_llm(claim, texts); used = "llm"
            if st is None:
                st = stance_rules(texts); used = "rules(폴백: API 키 없음)"
        else:
            st = stance_rules(texts); used = "rules"
        for p, (s_, h) in zip(g.post_id, st):
            rows.append(dict(post_id=p, narrative_id=int(nid), stance=s_, backend=used, hit=h))
        excl = set(p for p, (s_, _) in zip(g.post_id, st) if s_ != "support")
        joined = AL.suspect_asof(S, M, nid); fo_first = gall[gall.lang != "ko"].ts.min()
        ra = measure(g, joined, grid, set(), fo_first, t0); rb = measure(g, joined, grid, excl, fo_first, t0)
        n_reb = np.array([int(((g.ts < t) & g.post_id.isin(excl)).sum()) for t in grid])
        for i in range(len(grid)):
            series.append(dict(narrative_id=int(nid), ts=grid[i], hour=int(ra.hour.iloc[i]),
                               p_gt08_all=ra.p_gt08.iloc[i], p_gt08_support=rb.p_gt08.iloc[i],
                               p_gt1_all=ra.p_gt1.iloc[i], p_gt1_support=rb.p_gt1.iloc[i],
                               r_pool_all=ra.r_pool.iloc[i], r_pool_support=rb.r_pool.iloc[i], n_rebut_sofar=int(n_reb[i])))
        def first(rs, col):
            m = rs[(rs[col] >= AL.P_LEVEL) & (rs.n_susp >= AL.MIN_SUSPECTS) & (rs.ts > fo_first)] if pd.notna(fo_first) else rs.iloc[0:0]
            return int(m.hour.iloc[0]) if len(m) else None
        dist = pd.Series([s_ for s_, _ in st]).value_counts().to_dict()
        acc = None
        if sample:
            got = {p: s_ for p, (s_, _) in zip(g.post_id, st) if p in sample}
            if got:
                y = [sample[p] for p in got]; yh = [got[p] for p in got]
                tp = sum(1 for a_, b_ in zip(y, yh) if a_ == b_ == "rebut"); fp = sum(1 for a_, b_ in zip(y, yh) if b_ == "rebut" and a_ != "rebut")
                fn = sum(1 for a_, b_ in zip(y, yh) if a_ == "rebut" and b_ != "rebut")
                acc = dict(n=len(y), accuracy=round(sum(a_ == b_ for a_, b_ in zip(y, yh)) / len(y), 3),
                           rebut_precision=round(tp / (tp + fp), 3) if tp + fp else None, rebut_recall=round(tp / (tp + fn), 3) if tp + fn else None)
        summ["narratives"][int(nid)] = dict(claim=claim[:120], backend=used, stance_dist=dist, n_excluded=len(excl),
                                            first_alert_all=first(ra, "p_gt08"), first_alert_support=first(rb, "p_gt08"),
                                            first_critical_all=first(ra, "p_gt1"), first_critical_support=first(rb, "p_gt1"),
                                            accuracy=acc or "미측정(손 라벨 표본 data/stance_labels_sample.csv 없음)")
        print(f"narrative {nid}: {dist} 제외 {len(excl)} · ALERT 전체 {summ['narratives'][int(nid)]['first_alert_all']} / 찬성만 {summ['narratives'][int(nid)]['first_alert_support']} · {used}", flush=True)
    pd.DataFrame(rows).to_csv(os.path.join(AL.OUT, "stance.csv"), index=False)
    pd.DataFrame(series).to_csv(os.path.join(AL.OUT, "r_series_stance.csv"), index=False)
    json.dump(summ, open(os.path.join(AL.OUT, "stance_summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
