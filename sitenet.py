"""
sitenet.py — 사이트 층: 계정이 아니라 '도메인'을 조정 단위로 보는 인프라 신호 (2026-10-26 추가)

왜: 백신은 '계정이 동시에 글을 올리는' 공작에 맞춰져 있어 뉴스 사칭 계정을 0% 잡는다(IRA 실측, URL-망 추가 이득 0).
    그런데 2025~26년 실제 사례는 가짜 매체 사이트를 세우고 LLM으로 기사를 다시 써 소수 증폭자가 링크를 옮기는 형태다
    (CopyCop 300+ 사이트 — Recorded Future 2025; 국정원 2023 국내 언론 사칭 200여 개, 2025-04 7개 추가).
    그 사례들의 공통 탐지 단서는 전부 공개 인프라 신호였다: 일괄 등록된 도메인, 공유 IP/ASN, 인증서 투명성 로그의 동일 발급 묶음,
    동일 CMS 테마, 본문에 남은 LLM 흔적. 라이브 체계는 이미 '계정 = 매체 도메인'이라 이 층이 바로 붙는다.

입력   도메인 목록: --domains 파일(한 줄 하나) 또는 live/data/posts_live.csv 의 URL에서 추출(--from-live)
조회   (네트워크 필요 — 맥 터미널에서 실행. 작업 세션 VM·클라우드에서는 차단돼 캐시/고정자료만 씀)
       rdap   https://rdap.org/domain/<d>            → 등록일·등록대행·등록국가
       dns    socket.gethostbyname_ex              → A 레코드(IP) · IP 앞 3옥텟 = 같은 네트워크 근사(ASN은 다음 단계)
       crtsh  https://crt.sh/?q=<d>&output=json     → 인증서 발급 시각·발급자·같은 인증서에 묶인 이름(SAN)
       home   https://<d>/                          → 홈페이지 HTML: <meta generator>, 테마 경로(/wp-content/themes/<x>), 제목 템플릿
       모든 조회는 data/sitenet_cache.json 에 저장되고, --offline 이면 캐시·고정자료(data/sitenet_fixture.json)만 쓴다.
신호   (도메인 쌍) reg_batch  등록일 차이 ≤ REG_DAYS    · ip_shared 같은 IP 또는 같은 /24    · cert_batch 발급 시각 차이 ≤ CERT_HOURS
                 san_shared 같은 인증서에 함께 이름이 있음 · theme_same 같은 CMS 테마/generator · title_tpl 제목 템플릿 동일
       (도메인 단독) young_domain 등록 ≤ YOUNG_DAYS · llm_artifact 본문 LLM 흔적 정규식(있을 때만) · mimic_name 국내 언론사 이름 포함
판정   쌍 신호 점수 합 ≥ 2 이면 간선(강한 신호 1점: reg_batch·ip_shared·san_shared·cert_batch·theme_same / 약한 신호 0.5점: ip_net24·title_tpl)
       → 연결 성분 크기 ≥ 3 이면 '사이트 묶음 후보'. 판정이 아니라 분석관 확인 목록.
       실존 개인 귀속은 하지 않는다 — 단위는 도메인·인프라·조직 공개 보도까지.
출력   out/sitenet_domains.csv, out/sitenet_pairs.csv, out/sitenet_clusters.json
실행   python sitenet.py --from-live            (맥, 네트워크)      python sitenet.py --offline --fixture  (점검용 고정자료)
"""
import argparse, json, os, re, socket, sys, time
from datetime import datetime, timezone
import pandas as pd
import networkx as nx

HERE = os.path.dirname(os.path.abspath(__file__)); DATA = os.path.join(HERE, "data"); OUT = os.path.join(HERE, "out")
CACHE = os.path.join(DATA, "sitenet_cache.json")
REG_DAYS, CERT_HOURS, YOUNG_DAYS = 7, 48, 180
UA = {"User-Agent": "fimi-sitenet/0.1 (research; public infra signals only)"}
LLM_ART = re.compile(r"(as an ai language model|knowledge cutoff|i cannot (browse|access)|here is (a|the) rewritten|\[insert [^\]]+\]|"
                     r"언어 모델로서|지식 마감일|다음은 다시 쓴 기사|\[여기에 [^\]]+\])", re.I)
KR_MEDIA = ["서울신문", "매일신문", "제주일보", "조선", "중앙", "동아", "한겨레", "경향", "연합", "seoul", "daily", "news", "ilbo", "times", "press", "tv"]


def _get(url, timeout=20):
    import urllib.request
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout).read().decode("utf-8", "ignore")


def lookup(d, cache, offline):
    if d in cache and (offline or not any(k.endswith("_err") for k in cache[d])):
        return cache[d]          # 오류가 있던 항목은 온라인이면 다시 조회
    if offline:
        return cache.get(d, {})
    rec = {"fetched": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    try:
        reg_d = ".".join(d.split(".")[-2:]) if not re.search(r"\.(co|or|ne|go|ac|com|net|org)\.[a-z]{2}$", d) else ".".join(d.split(".")[-3:])
        rec["registrable"] = reg_d          # 서브도메인(kr.example.com)은 등록 정보가 없으므로 등록 가능 도메인으로 조회
        j = json.loads(_get(f"https://rdap.org/domain/{reg_d}"))
        ev = {e.get("eventAction"): e.get("eventDate") for e in j.get("events", [])}
        rec["registered"] = ev.get("registration"); rec["registrar"] = next((x.get("handle") or "" for x in j.get("entities", []) if "registrar" in x.get("roles", [])), "")
    except Exception as e:
        rec["rdap_err"] = str(e)[:80]
    try:
        rec["ips"] = sorted(set(socket.gethostbyname_ex(d)[2]))
    except Exception as e:
        rec["dns_err"] = str(e)[:80]
    try:
        j = json.loads(_get(f"https://crt.sh/?q={d}&output=json"))
        rec["certs"] = [dict(t=x.get("entry_timestamp"), issuer=x.get("issuer_name"), names=x.get("name_value", "").split("\n")) for x in j[:50]]
    except Exception as e:
        rec["crt_err"] = str(e)[:80]
    try:
        h = _get(f"https://{d}/", 15)
        m = re.search(r'<meta[^>]+name="generator"[^>]+content="([^"]+)"', h, re.I); rec["generator"] = m.group(1) if m else ""
        m = re.search(r"/wp-content/themes/([A-Za-z0-9_-]+)/", h); rec["theme"] = m.group(1) if m else ""
        m = re.search(r"<title>([^<]{0,120})</title>", h, re.I); t = (m.group(1) if m else "").strip()
        rec["title_tpl"] = re.sub(r"[\w가-힣]+", "W", t)[:40]
        rec["llm_artifact"] = bool(LLM_ART.search(h))
    except Exception as e:
        rec["home_err"] = str(e)[:80]
    cache[d] = rec; time.sleep(1.0)
    return rec


def ip24(ip):
    return ".".join(ip.split(".")[:3])


def pair_signals(a, ra, b, rb):
    s = []
    try:
        da, db = ra.get("registered"), rb.get("registered")
        if da and db and abs((pd.Timestamp(da) - pd.Timestamp(db)).days) <= REG_DAYS:
            s.append("reg_batch")
    except Exception:
        pass
    ia, ib = set(ra.get("ips", [])), set(rb.get("ips", []))
    if ia & ib:
        s.append("ip_shared")
    elif {ip24(x) for x in ia} & {ip24(x) for x in ib}:
        s.append("ip_net24")          # 같은 /24 — 공유 호스팅에서 흔하므로 약한 신호(0.5)
    ca, cb = ra.get("certs", []), rb.get("certs", [])
    if any(b in c.get("names", []) for c in ca) or any(a in c.get("names", []) for c in cb):
        s.append("san_shared")
    try:
        if ca and cb and min(abs((pd.Timestamp(x["t"]) - pd.Timestamp(y["t"])).total_seconds()) for x in ca for y in cb) <= CERT_HOURS * 3600:
            s.append("cert_batch")
    except Exception:
        pass
    if ra.get("theme") and ra.get("theme") == rb.get("theme") or (ra.get("generator") and ra.get("generator") == rb.get("generator") and ra.get("theme") == rb.get("theme") and ra.get("theme")):
        s.append("theme_same")
    if ra.get("title_tpl") and ra.get("title_tpl") == rb.get("title_tpl"):
        s.append("title_tpl")
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--domains"); ap.add_argument("--from-live", action="store_true"); ap.add_argument("--offline", action="store_true")
    ap.add_argument("--fixture", action="store_true", help="data/sitenet_fixture.json(가상 도메인 고정자료)로 점검")
    ap.add_argument("--max", type=int, default=60, help="--from-live 때 조회할 도메인 수 상한(출현 빈도순)")
    a = ap.parse_args()
    cache = json.load(open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) else {}
    if a.fixture:
        cache = json.load(open(os.path.join(DATA, "sitenet_fixture.json"), encoding="utf-8")); doms = list(cache); a.offline = True
    elif a.domains:
        doms = [x.strip() for x in open(a.domains, encoding="utf-8") if x.strip() and not x.startswith("#")]
    elif a.from_live:
        L = pd.read_csv(os.path.join(HERE, "live/data/posts_live.csv"), keep_default_na=False, usecols=["url"])
        cnt = pd.Series([re.sub(r"^www\.", "", re.sub(r"^https?://([^/]+).*$", r"\1", u.replace(" ", ""))) for u in L.url if u.startswith("http")]).value_counts()
        doms = list(cnt.index[:a.max])
    else:
        ap.error("--domains 파일, --from-live, --fixture 중 하나")
    recs = {d: lookup(d, cache, a.offline) for d in doms}
    if not a.fixture:
        json.dump(cache, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    now = pd.Timestamp.now(tz="UTC")
    rows = []
    for d, r in recs.items():
        reg = r.get("registered"); age = (now - pd.Timestamp(reg).tz_convert("UTC") if pd.Timestamp(reg).tzinfo else now - pd.Timestamp(reg).tz_localize("UTC")).days if reg else None
        rows.append(dict(domain=d, registered=reg, age_days=age, young_domain=bool(age is not None and age <= YOUNG_DAYS), registrar=r.get("registrar", ""),
                         ips=";".join(r.get("ips", [])), n_certs=len(r.get("certs", [])), theme=r.get("theme", ""), generator=r.get("generator", ""),
                         llm_artifact=bool(r.get("llm_artifact")), mimic_name=any(k.lower() in d.lower() for k in KR_MEDIA), lookup_ok=not (set(r) <= {"fetched"} or not r)))
    D = pd.DataFrame(rows); D.to_csv(os.path.join(OUT, "sitenet_domains.csv"), index=False)
    G = nx.Graph(); prs = []
    for i in range(len(doms)):
        for j in range(i + 1, len(doms)):
            s = pair_signals(doms[i], recs[doms[i]], doms[j], recs[doms[j]])
            sc = sum(0.5 if x in ("ip_net24", "title_tpl") else 1.0 for x in s)
            if s:
                prs.append(dict(a=doms[i], b=doms[j], signals="|".join(s), n=sc))
            if sc >= 2:
                G.add_edge(doms[i], doms[j], n=sc)
    pd.DataFrame(prs, columns=["a", "b", "signals", "n"]).to_csv(os.path.join(OUT, "sitenet_pairs.csv"), index=False)
    cl = [sorted(c) for c in nx.connected_components(G) if len(c) >= 3]
    json.dump(dict(n_domains=len(doms), n_looked_up=int(D.lookup_ok.sum()), clusters=cl,
                   note="후보 목록이다. 공유 호스팅(CDN·공용 IP)·같은 테마는 정상 사이트끼리도 흔하므로 분석관이 등록 정보·내용을 대조한 뒤에만 보고한다. 개인 귀속 금지."),
              open(os.path.join(OUT, "sitenet_clusters.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"domains={len(doms)} looked_up={int(D.lookup_ok.sum())} pairs_with_signal={len(prs)} clusters(≥3, 신호 2종 이상)={len(cl)}")
    for c in cl: print("  ", c)


if __name__ == "__main__":
    main()
