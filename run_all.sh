#!/bin/bash
# 전체 파이프라인: 데이터 → 서사 → 조정 신호 → 경보 → 봉인 → 전조 카드(축 A·B) → 대시보드
set -e
cd "$(dirname "$0")"
[ -d .venv ] && source .venv/bin/activate
python gen_data.py
python narratives.py "$@"        # 예: ./run_all.sh --merge 0.6
python coordination.py
python alerts.py
python policy_bridge.py
python seal.py
python sensitivity.py
python urlnet.py               # 제2 신호층: 계정–URL 공유 네트워크 → out/urlnet_*
python gen_signals.py          # 전조 축 A(공식 발언)·B(명분 서사) 합성 자료
python precursor.py            # 전조 카드 계산 → out/precursor.json
python precursor_replay.py     # 역사 재생: 실제 공개 담화 백테스트 → out/precursor_replay.json
python export_html.py
python export_story.py         # 한 화면 시연 → demo_story.html
python evaluate.py
# ---- 2026-10-26 추가 (재점검 반영, 동결 숫자 불변) ----
python coord_decay.py          # 제3 신호층: 창 없는 시간 감쇠 다층 조정 탐지 → out/coord_decay_*
python stance.py               # 입장 판별 → R̂ 찬성만/전체 → out/stance*.csv, r_series_stance.csv
python hawkes_r.py             # Hawkes 분기비·과분산 보정(진단용) → out/r_series_hawkes.csv
python sitenet.py --fixture    # 사이트 층 점검(고정자료). 실제 조회는 '사이트층 조회.command'
python llm_exposure.py --backend dry   # 축 E LLM·검색 노출(점검용). 실제 관측: --backend anthropic/openai/manual
streamlit run app.py
