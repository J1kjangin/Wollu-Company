# 월루컴퍼니

단일 파일 방치형 사무실 시뮬레이션 게임. 핵심 로직·스타일·데이터가 모두 `index.html` 에 들어있다.

## 아이템 이미지

- 원본: `assets/items/` (파일명 = 아이템 이름 또는 `item_<번호>.png`)
- 가공 결과: `itemImages/item_<번호>.png` (128px, 투명 배경)
- 파이프라인: `scripts/process_item_images.py` — 크롭·리사이즈·최적화 후 `index.html` 의 `ITEM_IMAGE_IDS` 자동 갱신
- 게임 렌더러(`function item()` in index.html)가 `ITEM_IMAGE_IDS` 에 있으면 `<img>`, 아니면 SVG 라인아트. 로드 실패 시 라인아트 폴백.
- 이미지 등록 아이템은 사무실에서 3배 크기로 배치되고, 꾸미기 카드에 '대칭' 버튼이 붙는다.

**사용자가 "이미지 넣었으니 반영해줘" / "새 아이템 이미지 반영" 같은 요청을 하면 `/item-images` 슬래시 커맨드를 실행한다.**
