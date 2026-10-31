"""
seal.py — M6 증거 봉인

단계가 처음 올라갈 때마다(관찰·경보·위험, 국내 사안은 검토) '증거 묶음'(그 시각의 단계 스냅숏·외국어 출처·관련 게시물의 ID·시각·본문 해시)을 만들고,
묶음의 SHA-256을 직전 기록의 해시와 이어 해시 체인(out/evidence_chain.jsonl)에 남긴다.
  - 체인에는 해시만 남는다. 원문 묶음은 out/bundles/ 에 분석 기관이 따로 보관.
  - 나중에 묶음 한 글자라도 바뀌면 verify()가 실패 → "이 시각에 존재했고 이후 바뀌지 않았다"를 보인다.
  - 진위 판정·배후 식별은 하지 않는다.
  - (선택) OpenTimestamps 클라이언트(ots)가 있으면 체인 끝 해시를 비트코인에 고정 요청. 확정까지 수 시간 걸림.

실행 :
  python seal.py              # 봉인 생성
  python seal.py --verify     # 검증
  python seal.py --tamper     # 시연용: 묶음 하나를 1글자 바꾼 뒤 검증 실패를 보여주고 원상복구
"""
import argparse, hashlib, json, os, shutil, subprocess, sys
from datetime import datetime, timezone
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA, OUT = os.path.join(HERE, "data"), os.path.join(HERE, "out")
CHAIN = os.path.join(OUT, "evidence_chain.jsonl")
BUND = os.path.join(OUT, "bundles")
GENESIS = "0" * 64


def sha(b):
    return hashlib.sha256(b).hexdigest()


def canon(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def build():
    """단계가 처음 올라가는 시점마다 봉인한다: 관찰(WATCH)·경보(ALERT)·위험(CRITICAL), 국내 사안은 검토(REVIEW).
    관찰 단계 = 아직 일반 시민 확산 전(조정 계정 + 외국어 출처만 보인 시점)부터 출처·시간 순서가 기록된다.
    체인은 모든 서사를 시각 순서대로 잇는다. 각 묶음에는 그 시각 이전 정보만 담는다."""
    os.makedirs(BUND, exist_ok=True)
    old = os.path.join(BUND, "_이전실행")           # 이전 실행의 묶음은 옮겨 둔다(체인과 1:1 대응 유지, 삭제하지 않음)
    for f in os.listdir(BUND):
        if f.startswith("bundle_") and f.endswith(".json"):
            os.makedirs(old, exist_ok=True)
            os.replace(os.path.join(BUND, f), os.path.join(old, f))
    cards = json.load(open(os.path.join(OUT, "alerts.json"), encoding="utf-8"))
    P = pd.read_csv(os.path.join(DATA, "posts.csv"), parse_dates=["ts"], keep_default_na=False,
                    usecols=["post_id", "ts", "account_id", "lang", "text", "url", "parent_id"])
    N = pd.read_csv(os.path.join(OUT, "posts_nar.csv"))
    P = P.merge(N[["post_id", "narrative_id"]], on="post_id")
    R = pd.read_csv(os.path.join(OUT, "r_series.csv"), parse_dates=["ts"])
    order = ["REVIEW", "WATCH", "ALERT", "CRITICAL"]
    events = []                                     # (시각, 서사, 단계, 카드)
    for c in cards:
        by_ts = {}
        for lv in order:
            t = c["first"].get(lv)
            if t:
                by_ts[t] = lv                           # 같은 시각이면 더 높은 단계로
        for t, lv in by_ts.items():
            events.append((pd.Timestamp(t), c["narrative_id"], lv, c))
    events.sort(key=lambda e: (e[0], e[1]))
    prev, lines = GENESIS, []
    for t, nid, lv, c in events:
        g = P[(P.narrative_id == nid) & (P.ts < t)].sort_values("ts")
        row = R[(R.narrative_id == nid) & (R.ts == t)]
        snap = {}
        if len(row):
            r0 = row.iloc[0]
            snap = dict(level=str(r0.level), n_susp=int(r0.n_susp), n_posts_sofar=int(r0.n_posts_sofar),
                        **{k: (None if pd.isna(r0[k]) else round(float(r0[k]), 4)) for k in ("r_pool", "p_gt08", "p_gt1")})
        fo = g[g.lang != "ko"]
        bundle = dict(
            narrative_id=nid, level=lv, anchor_ts=str(t),
            snapshot=snap,                                   # 그 시각의 단계·의심 계정 수·확산 추정
            foreign_sources=[dict(post_id=r.post_id, ts=str(r.ts), lang=r.lang, url=r.url) for r in fo.itertuples()],
            card_reference=dict(narrative_id=c["narrative_id"], jurisdiction=c.get("jurisdiction"),
                                note="최종 카드 요약(참고). 봉인 시점 판단 근거는 snapshot·posts"),
            posts=[dict(post_id=r.post_id, ts=str(r.ts), account_id=r.account_id, lang=r.lang,
                        url=r.url, parent_id=r.parent_id, text_sha256=sha(r.text.encode("utf-8")))
                   for r in g.itertuples()])
        raw = canon(bundle)
        fn = f"bundle_N{nid}_{t:%Y%m%dT%H%M}_{lv}.json"
        with open(os.path.join(BUND, fn), "wb") as f:
            f.write(raw)
        rec = dict(seq=len(lines), sealed_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                   narrative_id=nid, level=lv, anchor_ts=str(t),
                   n_posts=len(bundle["posts"]), n_foreign=len(bundle["foreign_sources"]),
                   bundle_file=fn, bundle_sha256=sha(raw), prev=prev)
        rec["record_sha256"] = sha(canon({k: v for k, v in rec.items()}))
        prev = rec["record_sha256"]
        lines.append(rec)
    with open(CHAIN, "w", encoding="utf-8") as f:
        for r in lines:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"sealed {len(lines)} bundle(s) · chain head {prev[:16]}…")
    if shutil.which("ots"):
        head = os.path.join(OUT, "chain_head.txt")
        open(head, "w").write(prev)
        r = subprocess.run(["ots", "stamp", head], capture_output=True, text=True)
        print("OpenTimestamps:", "요청 완료(확정 대기)" if r.returncode == 0 else r.stderr.strip()[:200])
    return prev


def verify(path=CHAIN):
    if not os.path.exists(path):
        return False, "봉인 기록 없음"
    prev = GENESIS
    recs = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
    for r in recs:
        body = {k: v for k, v in r.items() if k != "record_sha256"}
        if r["prev"] != prev:
            return False, f"체인 연결 끊김 (seq {r['seq']})"
        if sha(canon(body)) != r["record_sha256"]:
            return False, f"기록 변조 (seq {r['seq']})"
        fp = os.path.join(os.path.dirname(path), "bundles", r["bundle_file"])
        if not os.path.exists(fp):
            return False, f"증거 묶음 없음: {r['bundle_file']}"
        if sha(open(fp, "rb").read()) != r["bundle_sha256"]:
            return False, f"증거 묶음 변조 감지: {r['bundle_file']} (seq {r['seq']})"
        prev = r["record_sha256"]
    return True, f"검증 통과 · 기록 {len(recs)}건 · 체인 끝 {prev[:16]}…"


def tamper_demo():
    recs = [json.loads(l) for l in open(CHAIN, encoding="utf-8") if l.strip()]
    fp = os.path.join(BUND, recs[0]["bundle_file"])
    orig = open(fp, "rb").read()
    bad = orig.replace(b'"level":"', b'"level":"X', 1)     # 한 글자 추가
    open(fp, "wb").write(bad)
    print("변조 후 :", verify())
    open(fp, "wb").write(orig)
    print("복구 후 :", verify())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--tamper", action="store_true")
    a = ap.parse_args()
    if a.tamper:
        tamper_demo()
    elif a.verify:
        print(verify())
    else:
        build(); print(verify())
