#!/bin/bash
# 실시간 수집·분석 루프 (공개 데이터). 더블클릭 → 터미널에서 10분마다 갱신, 첫 회차 뒤 live/live.html 이 브라우저로 열림. Ctrl+C 로 종료.
# 어디에 두고 실행해도 코드 폴더(~/Projects/fimi)를 찾아간다.
for d in "$HOME/Projects/fimi" "$(dirname "$0")" "$(dirname "$0")/.."; do
  if [ -f "$d/live/run.py" ]; then cd "$d"; break; fi
done
if [ ! -f live/run.py ]; then echo "코드 폴더(live/run.py)를 찾지 못했습니다. ~/Projects/fimi 가 있는지 확인하세요."; read -p "엔터를 누르면 닫힙니다"; exit 1; fi
echo "[FIMI 실시간] 코드 폴더: $(pwd)"
PY=python3
# 발표 시연용 가상환경(.venv)이 있으면 그것을 쓴다 — 다국어 모델(sentence-transformers) 포함
[ -x .venv/bin/python ] && PY="$PWD/.venv/bin/python"
# python.org 파이썬은 맥 인증서를 쓰지 않아 https가 막힌다 → 맥 시스템 인증서 묶음을 만들어 지정
CA="$PWD/live/data/cacert.pem"; mkdir -p live/data
security find-certificate -a -p /System/Library/Keychains/SystemRootCertificates.keychain /Library/Keychains/System.keychain > "$CA" 2>/dev/null
security find-certificate -a -p "$HOME/Library/Keychains/login.keychain-db" >> "$CA" 2>/dev/null
$PY -c "import certifi" 2>/dev/null || $PY -m pip install --user --quiet certifi 2>/dev/null
CF=$($PY -c "import certifi;print(certifi.where())" 2>/dev/null); [ -n "$CF" ] && cat "$CF" >> "$CA"
export SSL_CERT_FILE="$CA"
if ! $PY -c "import pandas, numpy, scipy, sklearn" 2>/dev/null; then
  echo "필요한 파이썬 패키지(pandas·numpy·scipy·scikit-learn)를 설치합니다 (처음 1회, 1~3분)…"
  $PY -m pip install --user --quiet pandas numpy scipy scikit-learn || $PY -m pip install --user --quiet --break-system-packages pandas numpy scipy scikit-learn
fi
EMBED=hash
if $PY -c "import sentence_transformers" 2>/dev/null; then EMBED=model; fi
echo "수집(GDELT 15분 원본·Mastodon) → 분석 → 위성 카탈로그 → 결합 → live/live.html  (임베딩: $EMBED)"
echo "첫 회차는 최근 3시간 뉴스 파일을 받느라 몇 분 걸립니다. 이후 10분마다 새 파일만 받습니다."
$PY live/run.py --embed $EMBED "$@" 2>&1 | tee live/data/run_log.txt
echo; read -p "종료됐습니다. 엔터를 누르면 창이 닫힙니다"
