#!/bin/bash
# 처음 한 번만 더블클릭: 필요한 부품 설치 → 전체 분석 실행 → 백업 화면(demo.html) 생성
cd "$(dirname "$0")"
LOG="설치_결과.txt"
exec > >(tee "$LOG") 2>&1
echo "=== FIMI 조기경보 설치 시작 ($(date '+%m-%d %H:%M')) ==="
if ! command -v python3 >/dev/null; then
  echo "파이썬이 없습니다. 뜨는 창에서 '설치'를 눌러 개발자 도구를 설치한 뒤 이 파일을 다시 더블클릭하세요."
  xcode-select --install; exit 1
fi
python3 --version
[ -d .venv ] || python3 -m venv .venv
source .venv/bin/activate
echo "--- 부품 설치 (몇 분 걸립니다) ---"
pip install -q --upgrade pip
pip install -q -r requirements.txt || { echo "부품 설치 실패 — 이 창 내용을 Claude에게 보내주세요"; exit 1; }
echo "--- 1/10 가상 데이터 만들기 ---";        python gen_data.py
echo "--- 2/10 서사 묶기 (처음엔 모델 다운로드 약 470MB) ---"; python narratives.py
echo "--- 3/10 조정 신호 ---";                  python coordination.py
echo "--- 4/10 경보 + 대응 단계 권고 ---";        python alerts.py && python policy_bridge.py
echo "--- 5/10 증거 봉인 ---";                  python seal.py
echo "--- 6/10 민감도 분석 ---";                 python sensitivity.py
echo "--- 7/10 제2 신호층 (URL 공유 네트워크) ---";  python urlnet.py
echo "--- 8/10 전조 카드 + 역사 재생 ---";          python gen_signals.py && python precursor.py && python precursor_replay.py
echo "--- 9/10 백업 화면 + 한 화면 시연 만들기 ---";  python export_html.py && python export_story.py
echo "--- 10/11 성공 지표 ---";                   python evaluate.py
echo "--- 11/11 재점검 추가분 (제3 신호층·입장 판별·Hawkes·사이트 층 점검) ---"; python coord_decay.py && python stance.py && python hawkes_r.py && python sitenet.py --fixture
echo ""
echo "=== 완료! 이제 '시연 시작.command'를 더블클릭하세요. 이 창은 닫아도 됩니다. ==="
echo "[끝] $(date)"
