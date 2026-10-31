# FIMI 서사 조기경보 — 행동 기반 외국발 영향력 공작 분석관 보조

**+ 2026-10-17~18 추가(전북대 방산 AI 아이디어 경진대회 · T2-5 연계): 전조 카드 · 제2 신호층과 회피 내성 · 분석관 판정 루프/브리핑/지휘관 화면 · 실제 공개 담화 역사 재생**

외국발 서사가 공작 계정에서 일반 시민에게 넘어가기 전에, **내용이 아니라 행동**(반복 동시 게시·문장 재사용·같은 링크·신생 계정)으로 포착하고 "지금 대응해도 되는가"를 근거와 함께 권고하는 **분석관 보조 도구**입니다. 군 관할은 외국어 출처가 연결된 서사로 한정하고, 일반 시민은 집계로만 다룹니다.

## 실행
```
pip install -r requirements.txt
python gen_data.py && python narratives.py && python coordination.py && python alerts.py \
  && python policy_bridge.py && python seal.py && python sensitivity.py \
  && python urlnet.py && python gen_signals.py && python precursor.py && python precursor_replay.py \
  && python export_html.py && python evaluate.py
streamlit run app.py        # 대시보드 · 한 화면 시연: demo_story.html · 분석관 상세/백업: demo.html
```

## 구성
- `gen_data.py` 72시간 합성 데이터(모든 계정·매체 가상) · `narratives.py` 다국어 서사 묶기 · `coordination.py` 조정 행동 신호
- `alerts.py` 확산 확률(R̂ 사후분포)·단계 · `response_policy.py`·`policy_bridge.py` 대응 단계 권고 · `seal.py` 관찰 단계부터 증거 해시 체인 봉인
- `app.py`·`anim.py` 대시보드(재생 패널) · `export_story.py`→`demo_story.html` 한 화면 8단계 시연 · `export_html.py`→`demo.html` 분석관 상세(오프라인) · `evaluate.py`·`sensitivity.py` 지표·민감도
- **전조 카드 (10-17 추가)** `gen_signals.py` 가상 적성국 공식 발언·외국어 명분/동원 서사(합성) · `precursor.py` 발언 구조 추출(조건·시한·장소·수단·톤, 규칙 기반)·네 축 정합성(수사 단독/수렴/불일치)·증거 사다리 L1~L5·과거 사례 7건 · `precursor_ui.py` 화면. 기존 경보 결과는 바뀌지 않음
- **제2 신호층·회피 내성 (10-17~18 추가)** `urlnet.py` 계정–URL 공유 네트워크(희귀 링크 2개 이상 함께 공유, 임계값 = URL 셔플 대조군 p99.9) · `experiments/redteam_gen.py`·`redteam.py` 공격자 7변형 생존 곡선 · `real/urlnet_ira.py` IRA 같은 규칙 · `redteam_ui.py`
- **분석관 판정 루프·브리핑·지휘관 화면 (10-18 추가)** `analyst.py` — burst 판정 → 근거 재집계(자동 하향 없음) → 증거 체인에 기록 · LLM 없는 결정론적 브리핑 · 지휘관 1화면
- **역사 재생 (10-18 추가)** `precursor_replay.py` + `data/cases_real.json`(공개 보도 확인 실사례 10건, 기관·직책만) — 규칙 v1/v2 비교
- `real/` 공개 IRA 트윗 검증 결과 · `experiments/` 한계 실험(속보 대조군·시간 분산·반박 비율·IRA 60분 창, `limits.html`)

## 결과 요약 (합성 데이터 자체 측정)
관찰 13시(실제 R=1 약 37시보다 약 24시간 앞섬) · 41시 사전 반박 실행 검토(P(R>0.8)=59%) · 공작 계정 정밀도 1.0 / 재현율 0.9 · 정상 서사 6개 중 경보 0 · IRA 실데이터 동시 게시 묶음이 대조군의 약 400배, 같은 운영팀 99.9%.
전조 카드(합성): 공식 예고형 발언 11시 → 은밀 증폭 관찰 13시 수렴 → 47시 완화 발언 vs 증폭 상승 = 불일치. 공식 축 단독으로는 경보하지 않음(기만·동시 선전 반례 보유).
회피 내성(합성 레드팀): burst 재현율 0.90 → ±20분 0.24 → ±60분 0 · URL-망 0.63 일정 · 뉴스 사칭형 0.94(링크 해석 시) · 인기 링크 희석·고유 단축 URL이면 0 · IRA 실데이터에서는 URL-망의 추가 이득 0(뉴스 사칭 0% 유지) — 나쁜 결과도 그대로 둔다.
역사 재생(실제 공개 담화 7건): 합성 기준 규칙 v1은 행동 사례 4건 중 1건만 L3(과적합) · 고친 v2는 3/4(2·6·0일 선행)이지만 행동 없던 3건 중 2건도 L3 → 공식 축 단독이면 오경보 2/3. in-sample 작동 확인이지 예측력이 아니다.
한계(나쁜 결과 포함)는 `experiments/limits.html`과 `PRD.md` 8절 참고.

## 데이터와 윤리
가상 데이터와 공개 데이터만 사용. 실존 개인 식별·표적화 기능 없음. 계정은 해시 가명.
