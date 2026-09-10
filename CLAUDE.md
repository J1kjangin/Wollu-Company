# 월루컴퍼니

단일 파일 방치형 사무실 시뮬레이션 게임. 핵심 로직·스타일·데이터가 모두 `index.html` 에 들어있다.

## 레이아웃 (반응형)

**절대 규칙: 배치 좌표계 476×337 은 불변이다.** 저장된 아이템 좌표(`equippedByRoom`)의 기준이므로
이 숫자를 바꾸면 기존 세이브가 깨진다. 화면 크기 대응은 전부 `.office-layer` 의
`transform: scale()` 로만 처리한다 (`UI._updateOfficeScale`).

- `.office-room` 은 주어진 공간을 그대로 채우는 '무대 상자'다. 픽셀 하한이 없다.
  476:337 과 비율이 어긋나는 만큼은 레이어가 레터박스로 흡수하고, 방 격자
  (`background-size`)는 `--office-scale` 을 따라 함께 커진다.
- 배율은 `Math.min(w/476, h/337)` — **하한 1.0 을 두지 않는다.** 이 하한이 예전에
  폭 476px 미만 기기(대부분의 폰)에서 가로 잘림을 만들던 원인이었다.
- CSS 는 `<style>` 맨 끝의 **"반응형 레이어"** 블록에서 크기를 결정한다.
  앞쪽 규칙들은 외형(색·테두리)만 담당한다.
  - 기본(1열): 헤더 / 연봉바 / 사직서바 / 무대 / 탭 / 목록 세로 스택
  - 와이드(`min-width:900px` **and** `min-aspect-ratio:5/4`, 또는 가로 폰):
    CSS Grid 2열 — 좌측 무대 전면, 우측 사이드바. DOM 변경 없이 `grid-template-areas` 로만 재배치
- `--frame-h` / `--list-max` 를 JS 로 실측하던 순환참조 루프는 비활성화되어 있다
  (`_syncFrameHeight` / `_syncListMax` 는 즉시 `return`). 되살리지 말 것.
- 튜닝 손잡이는 `:root` 의 `--list-ideal`, `--list-min`, `--office-min-h`,
  `--side-w`, `--shell-max-w` 다섯 개다.
- `--shell-max-w: 2400px` 은 아이콘 원본 512px 에서 온 값이다
  (디자인 최대 124px × 배율 4.1 ≈ 508px). 더 키우려면 아이콘부터 재생성해야 한다.

## 아이템 이미지

- 원본: `assets/items/` (파일명 = 아이템 이름 또는 `item_<번호>.png`)
- 가공 결과: `itemImages/item_<번호>.png` (512px, 무대용) + `itemImages/thumb/item_<번호>.png` (128px, 목록용)
- 파이프라인: `scripts/process_item_images.py` — 크롭·리사이즈·최적화 후 `index.html` 의 `ITEM_IMAGE_IDS` 자동 갱신
- 게임 렌더러(`CYANOTYPE.item(id, size, hires)`)가 `ITEM_IMAGE_IDS` 에 있으면 `<img>`, 아니면 SVG 라인아트.
  로드 실패 시 라인아트 폴백. `hires=true` 는 배치구역 호출부에서만 쓴다.
- 이미지 등록 아이템은 사무실에서 3배 크기로 배치되고, 꾸미기 카드에 '대칭' 버튼이 붙는다.

**사용자가 "이미지 넣었으니 반영해줘" / "새 아이템 이미지 반영" 같은 요청을 하면 `/item-images` 슬래시 커맨드를 실행한다.**
