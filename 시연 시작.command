#!/bin/bash
# 더블클릭하면 '한 화면 시연'(demo_story.html)이 브라우저에 뜨고, 뒤에서 분석관 대시보드(localhost:8501)가 켜집니다.
# 화면 오른쪽 위 '대시보드' 버튼이 그 대시보드로, '백업 화면'이 분석관 상세(오프라인)로 이어집니다. 끝낼 때는 이 터미널 창을 닫으세요.
cd "$(dirname "$0")"
if [ ! -d .venv ]; then echo "먼저 '설치하기.command'를 실행하세요."; read -n1; exit 1; fi
source .venv/bin/activate
# 예전에 켜 둔 시연 서버가 남아 있으면 끄고 새로 시작 (옛 데이터가 보이는 문제 방지)
PIDS=$(lsof -ti tcp:8501 2>/dev/null); [ -n "$PIDS" ] && kill $PIDS && sleep 1
[ -f demo_story.html ] || python export_story.py
open "demo_story.html"
echo "한 화면 시연이 열렸습니다 (→ 다음 · ← 이전 · Space 자동 재생). 대시보드: http://localhost:8501"
streamlit run app.py --server.headless true --browser.gatherUsageStats false
