"""
sat_guide.py — 위성 캡처 안내문 생성 (2026-10-18 추가)
data/sat/manifest.json 을 읽어 '받을 영상 목록'(파일명·좌표·날짜·Copernicus Browser 링크·캡처 방법)을 Markdown으로 만든다.
실행: python sat_guide.py  →  data/sat/받을_영상_목록.md
영상 파일이 들어오면 `python export_story.py` 가 자동으로 임베드한다(가로 1280px JPEG로 줄임).
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
SAT = os.path.join(HERE, "data", "sat")


def browser_url(site, when):
    la, lo = site.get("lat"), site.get("lon")
    if la is None or lo is None:
        return None
    return (f"https://browser.dataspace.copernicus.eu/?zoom={site.get('zoom', 14)}&lat={la}&lng={lo}"
            f"&datasetId=S2_L2A_CDAS&layerId=1_TRUE_COLOR")


def main():
    M = json.load(open(os.path.join(SAT, "manifest.json"), encoding="utf-8"))
    L = ["# 위성 캡처 받을 영상 목록 — 전조 카드 축 D(물리 전조) 실제 사례", "",
         f"출처 표기(그대로 사용): **{M.get('attribution', '').split(' · ')[0]}** · Copernicus Sentinel 데이터는 무료·공개(출처 표기 조건)",
         "저장 위치: `~/Desktop/백신/4_근거자료/위성/` (아래 파일명 그대로, PNG 또는 JPG) → 넣은 뒤 알려 주시면 제가 내보내기·동기화합니다.",
         f"로그인: {M.get('login_note', '')}", "",
         "## 캡처 방법 (지점당 전·후 2장, 지도를 움직이지 말고 날짜만 바꿔 같은 틀로)",
         "1. 아래 **Copernicus Browser 열기** 링크 클릭 → 위치·배율만 맞춰 열립니다(레이어는 수동). 처음 뜨는 창에서 '익명으로 계속'을 눌러도 됩니다.",
         "2. 왼쪽 **Visualize** 탭 → Sentinel-2 L2A → **True color** 선택. 날짜 선택기에서 '전' 범위 안의 날짜를 고릅니다(구름 30% 이하 날짜가 표시됨; 미리보기로 구름 없는 날 확인).",
         "3. 오른쪽 도구의 **이미지 다운로드(Basic, PNG)** 를 누르거나(로그인 불필요), ⌘⇧4로 지도 영역만 드래그 캡처 → 파일명 `..._before.png`",
         "4. 지도를 그대로 둔 채 날짜만 '후' 범위의 맑은 날로 바꿔 같은 방법으로 → `..._after.png`. 전·후 틀이 같아야 밀어 비교가 됩니다.",
         "5. 공사·절개지가 True color에서 희미하면 **NDVI** 또는 **False color**로 한 번 더 캡처해 `_ndvi_before.png / _ndvi_after.png` 로 추가(선택). 같은 계절끼리(여름–여름) 비교하면 식생 차이 오탐이 줄어듭니다.",
         "6. 좌표는 보도 앵커에서 추정한 값(신뢰도 표기)이라 **지도에서 실제 구조물을 찾아 중심을 옮겨도 됩니다** — 옮겼으면 최종 중심 좌표를 함께 적어 주세요(화면에 '추정'으로 표기합니다).",
         "7. 해상도 10 m 한계: 폭 2~4 m 방벽·폭 10 m 참호는 1픽셀 수준으로 경계적이고, 벌목·절개 나지와 접근도로 선형, 성토지(폭 50 m)는 보입니다. 안 보이면 안 보이는 대로 둡니다 — 화면에 그 한계가 그대로 적힙니다.", ""]
    for i, s in enumerate(M.get("sites", []), 1):
        la, lo = s.get("lat"), s.get("lon")
        coord = f"{la:.4f}°N, {lo:.4f}°E" if la is not None and lo is not None else "**[확인 필요]**"
        L += [f"## {i}. {s['title']}", f"- 위치: {s.get('place', '')} · 좌표 {coord} (신뢰도 {s.get('coord_conf', '—')}) · 배율 zoom {s.get('zoom', 14)}",
              f"- 좌표 근거: {s.get('coord_note', '')}",
              f"- 전: `{s['before']['file']}` — {s['before']['date']}", f"- 후: `{s['after']['file']}` — {s['after']['date']}",
              f"- 무엇을 보나: {s.get('what', '')}", f"- 의미: {s.get('role', '')}"]
        u = browser_url(s, "before")
        L.append(f"- Copernicus Browser 열기: {u}" if u else "- Copernicus Browser 링크: 좌표 확인 뒤 생성")
        if s.get("sources"):
            L.append("- 근거: " + " · ".join(s["sources"]))
        L.append("")
    if M.get("physical_events"):
        L += ["## 물리 신호 보도 날짜 (역사 재생 타임라인 ▽ 마커 · 모두 공개 보도)", ""]
        for e in M["physical_events"]:
            L.append(f"- {e['date']} · {e['what']} — {e.get('source_url', '')}")
        L.append("")
    if M.get("taiwan_2022_zones"):
        L += ["## 참고 — 2022-08 중국 대만 포위 훈련 6개 구역 공표 좌표 (위성영상 아님 · 신화사 수권공고 2022-08-02, 澎湃·新浪 미러에서 확인)", ""]
        for z in M["taiwan_2022_zones"]:
            L.append(f"- {z['id']} {z['place']} · 중심 {z['center'][0]:.3f}N {z['center'][1]:.3f}E")
        L.append("")
    L += ["## 정직하게 적어 둘 것", f"- {M.get('disclaimer', '')}", f"- {M.get('license_note', '')}"]
    out = os.path.join(SAT, "받을_영상_목록.md")
    open(out, "w", encoding="utf-8").write("\n".join(L))
    print(out)


if __name__ == "__main__":
    main()
