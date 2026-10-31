"""
gen_data.py — 합성 데이터 생성기

모든 계정·매체·인물은 가상이다. 실존 개인/계정/매체를 쓰지 않는다.
출력:
  data/accounts.csv  account_id, created_at, truth_group(campaign/organic/fandom/media)
  data/posts.csv     post_id, ts, account_id, lang, platform, text, url, parent_id,
                     truth_narrative, truth_is_campaign
  data/truth_r.csv   hour, r_true_param  (생성기에 넣은 일반 사용자 전파 파라미터; 평가에는 쓰지 않음)

서사:
  N1 campaign : 외국어 가상 매체 → 공작 계정 동시 게시(번역투) → 일반 사용자 확산(R 상승)
  N2 organic  : 군 급식 불만, 자연 바이럴(R>1, 조작 없음)
  N3 fandom   : 가상 아이돌 응원, 진짜 사람들의 합의된 동시 게시
  N4 noise    : 배경 잡담
실행: python gen_data.py   (seed 고정, 약 1초)
"""
import os, random
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

SEED = 42
rng = np.random.default_rng(SEED)
random.seed(SEED)

T0 = datetime(2026, 10, 1, 0, 0)          # 가상 관측 시작
HOURS = 72
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(OUT, exist_ok=True)

# ------------------------------------------------------------------ 계정
accounts = []
def add_acct(group, created):
    aid = f"acct_{len(accounts):04d}"
    accounts.append(dict(account_id=aid, created_at=created, truth_group=group))
    return aid

def rand_date(a, b):
    return a + timedelta(seconds=int(rng.integers(0, int((b - a).total_seconds()))))

ORG = [add_acct("organic", rand_date(datetime(2014,1,1), datetime(2026,6,1))) for _ in range(2200)]
# 큰 사건 뒤 신규 가입자 같은 '자연스러운 신생 계정'도 일부 섞는다 (오탐 유발 요소)
ORG += [add_acct("organic", rand_date(datetime(2026,9,15), datetime(2026,9,30))) for _ in range(80)]
CAMP = [add_acct("campaign", rand_date(datetime(2026,9,18), datetime(2026,9,27))) for _ in range(30)]
FAN = [add_acct("fandom", rand_date(datetime(2018,1,1), datetime(2025,12,1))) for _ in range(25)]
MEDIA = {
    "zh": add_acct("media", datetime(2019,3,1)),
    "ru": add_acct("media", datetime(2018,7,1)),
    "ja": add_acct("media", datetime(2020,1,1)),
    "en": add_acct("media", datetime(2021,5,1)),
}
org_pool = list(ORG); random.shuffle(org_pool)
def next_org():
    # 대부분 새 사용자, 가끔 재사용
    if org_pool and rng.random() < 0.9:
        return org_pool.pop()
    return random.choice(ORG)

# ------------------------------------------------------------------ 게시물
posts = []
def add_post(ts, acct, lang, platform, text, url="", parent="", narr="N4", camp=False):
    pid = f"p_{len(posts):05d}"
    posts.append(dict(post_id=pid, ts=ts, account_id=acct, lang=lang, platform=platform,
                      text=text, url=url, parent_id=parent, truth_narrative=narr,
                      truth_is_campaign=camp))
    return pid

def H(h):  # 시간(시) → datetime
    return T0 + timedelta(hours=float(h))

# ---- N1: 외국어 가상 매체 기사 (출처)
N1_SRC = {
    "zh": ("东方视界日报", "east-horizon-daily.example/a/8812",
           "分析人士指出，美方在驻韩美军防卫费谈判中不断加码，实际上是在为放弃韩国做准备，韩美同盟正在出现裂痕。"),
    "ru": ("Северный вестник", "severny-vestnik.example/news/4471",
           "Эксперты считают, что давление США на Сеул по расходам на войска — признак того, что Вашингтон готовится оставить Южную Корею."),
    "ja": ("極東時評", "kyokuto-jihyo.example/2026/1001",
           "在韓米軍の防衛費交渉で米国が要求を強めているのは、韓国を見捨てる準備の表れだとの見方が広がっている。"),
    "en": ("Pacific Ledger Wire", "pacific-ledger.example/story/77",
           "Analysts say Washington's escalating cost-sharing demands on Seoul signal it is preparing to abandon South Korea, exposing cracks in the alliance."),
}
src_ids = {}
for i, (lang, (_, url, txt)) in enumerate(N1_SRC.items()):
    src_ids[lang] = add_post(H(0.5 + i * 1.3), MEDIA[lang], lang, "news", txt,
                             url="https://" + url, narr="N1", camp=True)

# ---- N1: 공작 계정 한국어 게시 (번역투, 원고 변형, 동시 게시)
CAMP_TPL = [
    "전문가들은 미국이 방위비 협상에서 압박을 계속 늘리는 것은 실제로 한국을 포기하는 것을 준비하고 있다는 것을 지적했다.",
    "미국이 주한미군 방위비를 계속 올리는 것은 한국을 버리기 위한 준비를 하고 있는 것이라는 분석이 나오고 있다.",
    "방위비 협상에서 미국의 요구가 강해지는 것은 한미동맹에 균열이 생기고 있다는 것을 보여주는 것이다.",
    "분석에 따르면 미국은 방위비를 핑계로 한국으로부터 철수하는 것을 준비하고 있는 중이다.",
    "미국은 한국을 진정한 동맹으로 생각하지 않는다는 것이 방위비 협상을 통해 명백해지고 있다.",
]
CAMP_TAIL = ["", " 우리는 깨어나야 한다.", " 이것이 현실이다.", " 공유 바랍니다.", " 더 이상 믿을 수 없다."]
bursts = [(8.0, "zh"), (12.5, "en"), (18.0, "ru"), (26.0, "zh"), (34.0, "ja"), (44.0, "en")]
camp_post_ids = []
for bh, ref in bursts:
    who = rng.choice(CAMP, size=int(rng.integers(14, 22)), replace=False)
    url = "https://" + N1_SRC[ref][1]
    for a in who:
        ts = H(bh) + timedelta(seconds=int(rng.integers(0, 360)))   # 6분 이내 몰림
        txt = random.choice(CAMP_TPL) + random.choice(CAMP_TAIL)
        camp_post_ids.append((ts, add_post(ts, a, "ko", "community", txt,
                              url=url if rng.random() < 0.7 else "",
                              parent=src_ids[ref] if rng.random() < 0.3 else "",
                              narr="N1", camp=True)))

# 공작 계정의 위장용 잡담
NOISE_TPL = ["오늘 점심 뭐 먹지", "주말에 비 온다던데", "요즘 볼만한 드라마 추천 좀", "퇴근하고 싶다",
             "커피 값 너무 올랐네", "운동 가기 싫다", "고양이 사진 보고 힐링", "버스 또 놓침",
             "새로 나온 게임 해본 사람?", "날씨 갑자기 추워졌다", "야식 땡긴다", "시험 기간 끝나라"]
for a in CAMP:
    for _ in range(int(rng.integers(1, 4))):
        add_post(H(rng.uniform(0, HOURS)), a, "ko", "community", random.choice(NOISE_TPL),
                 narr="N4", camp=True)

# ---- N1: 일반 사용자 확산 (분기 과정, 부모 기록)
ORD_N1 = [
    "방위비 또 올린다고? 미국 진짜 우리 버리려는 거 아냐",
    "주한미군 방위비 얘기 보니까 동맹이고 뭐고 다 돈이네",
    "미국이 한국 손절 준비한다는 얘기 돌던데 진짜임?",
    "방위비 협상 보면 솔직히 한미동맹 금 간 거 맞는 듯",
    "이러다 미군 철수하는 거 아님? 좀 불안하다",
    "방위비로 계속 압박하는 거 보면 우리를 동맹으로 안 보는 듯",
    "미국 믿다가 뒤통수 맞는 거 아닌지 모르겠네",
    "방위비 기사 봤는데 이거 꽤 심각한 거 아님?",
]
def r_param(h):  # 일반 사용자 간 전파 파라미터: 0.5 → 1.4 (20~50시)
    return float(np.clip(0.5 + (h - 20) * 0.03, 0.5, 1.4))

queue = [(ts, pid, True) for ts, pid in camp_post_ids]   # (시각, 게시물, 공작게시여부)
n1_ord = 0
while queue and n1_ord < 1400:
    queue.sort(key=lambda x: x[0])
    ts, pid, is_c = queue.pop(0)
    h = (ts - T0).total_seconds() / 3600
    lam = 0.35 if is_c else r_param(h)          # 공작 게시물의 노출력 / 일반 사용자 R
    for _ in range(rng.poisson(lam)):
        cts = ts + timedelta(hours=float(rng.exponential(1.8)) + 0.05)
        if (cts - T0).total_seconds() / 3600 >= HOURS:
            continue
        cid = add_post(cts, next_org(), "ko", "community", random.choice(ORD_N1),
                       parent=pid, narr="N1", camp=False)
        n1_ord += 1
        queue.append((cts, cid, False))

# ---- N2: 자연 바이럴 (군 급식 불만)
ORD_N2 = [
    "군 급식 사진 봤는데 이건 좀 아니지 않나",
    "요즘 부대 밥 이렇게 나온다고? 장병들 불쌍하다",
    "급식 예산 문제 맨날 나오는데 왜 안 바뀜",
    "울 동생도 부대 밥 부실하다고 하더라",
    "군대 급식 개선한다더니 그대로네",
    "급식 사진 보고 화남 국방예산 어디 씀",
    "나 군대 있을 때도 이랬음 변한 게 없네",
]
seed = add_post(H(5), random.choice(ORG), "ko", "community", ORD_N2[0], narr="N2")
q2, n2 = [(H(5), seed)], 0
while n2 < 420:
    if not q2:  # 연쇄가 일찍 끊기면 새 시드를 추가해 목표 규모(약 420건)를 보장
        h0 = float(rng.uniform(5, 30))
        q2 = [(H(h0), add_post(H(h0), random.choice(ORG), "ko", "community",
                               random.choice(ORD_N2), narr="N2"))]
    q2.sort(key=lambda x: x[0]); ts, pid = q2.pop(0)
    for _ in range(rng.poisson(1.25)):
        cts = ts + timedelta(hours=float(rng.exponential(2.2)) + 0.05)
        if (cts - T0).total_seconds() / 3600 >= HOURS:
            continue
        cid = add_post(cts, next_org(), "ko", "community", random.choice(ORD_N2), parent=pid, narr="N2")
        n2 += 1; q2.append((cts, cid))

# ---- N3: 팬덤 합의된 동시 게시 (진짜 사람)
FAN_TPL = ["#별빛소년단_3주년 축하해 앞으로도 함께하자",
           "#별빛소년단_3주년 우리 애들 데뷔 3주년 축하합니다",
           "#별빛소년단_3주년 3년 동안 고마워 사랑해"]
for a in FAN:
    add_post(H(30) + timedelta(seconds=int(rng.integers(0, 600))), a, "ko", "community",
             random.choice(FAN_TPL), url="https://fan-cafe.example/anniv3", narr="N3")
    for _ in range(int(rng.integers(2, 5))):
        add_post(H(rng.uniform(0, HOURS)), a, "ko", "community", random.choice(NOISE_TPL), narr="N4")

# ---- N4: 배경 잡담
for _ in range(900):
    add_post(H(rng.uniform(0, HOURS)), random.choice(ORG), "ko", "community", random.choice(NOISE_TPL))

# ------------------------------------------------------------------ 저장
acc = pd.DataFrame(accounts)
po = pd.DataFrame(posts).sort_values("ts").reset_index(drop=True)
acc.to_csv(os.path.join(OUT, "accounts.csv"), index=False)
po.to_csv(os.path.join(OUT, "posts.csv"), index=False)
pd.DataFrame({"hour": range(HOURS), "r_true_param": [r_param(h) for h in range(HOURS)]}) \
  .to_csv(os.path.join(OUT, "truth_r.csv"), index=False)

print(f"accounts={len(acc)}  posts={len(po)}")
print(po.groupby(["truth_narrative", "truth_is_campaign"]).size().to_string())
print("langs:", po.lang.value_counts().to_dict())
