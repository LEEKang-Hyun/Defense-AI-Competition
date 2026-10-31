#!/bin/bash
mkdir -p "$HOME/Projects/fimi/logs"; exec > >(tee "$HOME/Projects/fimi/logs/LLM노출 관측.log") 2>&1
# 축 E: 서사의 핵심 주장을 챗봇에 묻고 반복/부인/언급 없음을 기록한다. API 키는 .env(로컬 전용)에서 읽는다. 키는 화면에 출력하지 않는다.
cd "$HOME/Projects/fimi" || exit 1
PY=python3; [ -x .venv/bin/python ] && PY="$PWD/.venv/bin/python"
[ -f .env ] || { echo ".env 없음 — ANTHROPIC_API_KEY=... 를 .env 에 적어 주세요"; echo "[끝] $(date)"; sleep 3; exit 1; }
set -a; . ./.env; set +a
CA="$PWD/live/data/cacert.pem"; mkdir -p live/data
security find-certificate -a -p /System/Library/Keychains/SystemRootCertificates.keychain /Library/Keychains/System.keychain > "$CA" 2>/dev/null
CF=$($PY -c "import certifi;print(certifi.where())" 2>/dev/null); [ -n "$CF" ] && cat "$CF" >> "$CA"
export SSL_CERT_FILE="$CA"
echo "모델: ${LLM_MODEL:-기본값} · 서사: 공작 서사(0)와 혼합 서사(2)"
$PY llm_exposure.py --backend anthropic --judge --narratives 0,2
echo; echo "요약: out/llm_exposure_summary.json"; $PY -c "import json;[print(k, v['card_line']) for k,v in json.load(open('out/llm_exposure_summary.json'))['narratives'].items()]"
echo "[끝] $(date)"; sleep 3
