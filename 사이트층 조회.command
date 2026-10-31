#!/bin/bash
mkdir -p "$HOME/Projects/fimi/logs"; exec > >(tee "$HOME/Projects/fimi/logs/사이트층 조회.log") 2>&1
# 사이트 층(sitenet.py)을 맥에서 실행 — 외부 조회(RDAP·DNS·crt.sh·홈페이지)가 필요해서 작업 세션이 아니라 맥 터미널에서 돈다.
cd "$HOME/Projects/fimi" || exit 1
PY=python3; [ -x .venv/bin/python ] && PY="$PWD/.venv/bin/python"
$PY -c "import networkx" 2>/dev/null || $PY -m pip install --quiet networkx
# python.org 파이썬은 맥 인증서를 쓰지 않아 https가 막힌다 → 실시간 시작.command 와 같은 방식으로 인증서 묶음 지정
CA="$PWD/live/data/cacert.pem"; mkdir -p live/data
security find-certificate -a -p /System/Library/Keychains/SystemRootCertificates.keychain /Library/Keychains/System.keychain > "$CA" 2>/dev/null
$PY -c "import certifi" 2>/dev/null || $PY -m pip install --quiet certifi 2>/dev/null
CF=$($PY -c "import certifi;print(certifi.where())" 2>/dev/null); [ -n "$CF" ] && cat "$CF" >> "$CA"
export SSL_CERT_FILE="$CA"
echo "1) 공개 보도 사칭 사이트 목록 조회"; $PY sitenet.py --domains data/sitenet_watchlist.txt
echo; echo "2) 라이브 수집 URL의 도메인 조회(있을 때)"; [ -f live/data/posts_live.csv ] && $PY sitenet.py --from-live
echo; echo "결과: out/sitenet_domains.csv · out/sitenet_pairs.csv · out/sitenet_clusters.json"; echo "[끝] $(date)"; sleep 3
