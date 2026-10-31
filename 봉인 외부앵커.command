#!/bin/bash
mkdir -p "$HOME/Projects/fimi/logs"; exec > >(tee "$HOME/Projects/fimi/logs/봉인 외부앵커.log") 2>&1
# 증거 봉인 체인의 머리 해시를 OpenTimestamps(비트코인 블록체인 앵커, 무료·공개)에 고정한다. 외부 네트워크가 필요해 맥 터미널에서 실행.
# 결과 seal_anchor.txt.ots 는 "이 해시가 이 시각 이전에 존재했다"는 제3자 검증 가능한 증명(몇 시간 뒤 'ots upgrade'로 확정).
cd "$HOME/Projects/fimi" || exit 1
PY=python3; [ -x .venv/bin/python ] && PY="$PWD/.venv/bin/python"
CA="$PWD/live/data/cacert.pem"; mkdir -p live/data
security find-certificate -a -p /System/Library/Keychains/SystemRootCertificates.keychain /Library/Keychains/System.keychain > "$CA" 2>/dev/null
$PY -c "import certifi" 2>/dev/null || $PY -m pip install --quiet certifi
CF=$($PY -c "import certifi;print(certifi.where())" 2>/dev/null); [ -n "$CF" ] && cat "$CF" >> "$CA"
export SSL_CERT_FILE="$CA"
OTS="$(dirname "$PY")/ots"
[ -x "$OTS" ] || $PY -m pip install opentimestamps-client 2>&1 | tail -2
[ -x "$OTS" ] || OTS="$(command -v ots)"
[ -n "$OTS" ] || { echo "ots 설치 실패"; echo "[끝] $(date)"; sleep 3; exit 1; }
# 현재 체인 머리로 앵커 파일을 다시 만든다(체인은 재실행 때마다 시각이 바뀜)
$PY - <<'PYEOF'
import json, datetime
rec = json.loads(open("out/evidence_chain.jsonl").read().strip().splitlines()[-1])
n = len(open("out/evidence_chain.jsonl").read().strip().splitlines())
open("experiments/out/seal_anchor.txt", "w").write(
    f"FIMI demo evidence chain head\nrecord_sha256: {rec['record_sha256']}\nrecords: {n}\nsealed_at_last: {rec.get('sealed_at','')}\nanchored_at: {datetime.datetime.now().astimezone().isoformat(timespec='seconds')}\n(no content — hash only)\n")
print(open("experiments/out/seal_anchor.txt").read())
PYEOF
F=experiments/out/seal_anchor.txt
rm -f "$F.ots"
"$OTS" stamp "$F" && echo "생성: $F.ots  — 몇 시간 뒤  $OTS upgrade $F.ots  로 블록 확정,  $OTS verify $F.ots  로 검증"
echo "[끝] $(date)"; sleep 3
