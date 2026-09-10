---
description: assets/items 의 새 아이템 이미지를 가공·최적화해 itemImages 에 등록하고 게임에 반영
argument-hint: "(선택) 특정 파일명이나 아이템명"
---

사용자가 `assets/items/` 에 아이템 이미지를 추가했다. 아래 절차로 반영한다.
`$ARGUMENTS` 가 있으면 그 파일/아이템만 신경 쓰고, 없으면 폴더 전체를 대상으로 한다.

## 1. 현황 파악
- `assets/items/` 의 파일 목록과 `itemImages/` 의 기존 결과를 비교해 **새로 추가되었거나 원본이 바뀐** 이미지를 찾는다.
- `index.html` 의 `rawShopItems` 정의에서 아이템 이름 → `item_<번호>` 매핑을 확인한다.
- 파일명이 아이템 이름( 예: `푹신한 의자.png` ) 또는 `item_<번호>.png` 형식이 아니면,
  어떤 아이템인지 사용자에게 되묻고 진행을 멈춘다 (임의로 매핑하지 않는다).

## 2. 파이프라인 실행
```bash
python scripts/process_item_images.py
```
이 스크립트가 하는 일:
- 여백(투명/단색 배경) 자동 크롭 → 정사각 캔버스 중앙 정렬(6% 패딩) → 128px LANCZOS 리사이즈
- 최적화 저장(RGBA optimize vs 256색 양자화 중 작은 쪽) → `itemImages/item_<번호>.png`
- `index.html` 의 `const ITEM_IMAGE_IDS = new Set([...])` 자동 갱신

스크립트 출력에서 `? 매핑 실패` 로 건너뛴 파일이 있으면 사용자에게 알린다.

## 3. 검증
- `python -m http.server` 로 로컬 서버를 띄우고 인앱 브라우저로 `index.html` 을 연다.
- 개발자 콘솔에서 상태 인스턴스(`window.Workspace.state`)로 해당 아이템을 구매·배치한 뒤 확인한다:
  - 배치된 아이템에 `<img class="cy-item-img">` 가 생기고 `naturalWidth === 128`, onerror 폴백이 발동하지 않을 것
  - 이미지 등록 아이템은 사무실에서 3배 크기로 렌더될 것 (`CYANOTYPE.hasImage(id) === true`)
- 콘솔 에러가 없는지 확인한다.
- 가공 결과 미리보기(콘택트 시트)를 만들어 `SendUserFile` 로 사용자에게 보낸다.
- 확인이 끝나면 로컬 서버를 종료한다.

## 4. 마무리
- 무엇이 새로 등록됐는지(아이템명·번호·파일 크기) 요약해서 보고한다.
- 원본(`assets/items/`)은 지우지 않는다. 재가공을 위해 남겨둔다.
- 아이콘 크기 기준·크롭 방식 등 파이프라인 규칙을 바꿔야 하면 `scripts/process_item_images.py` 를 수정한다.

참고: 스케일(3배), 대칭 버튼, 레이어 순서 등 게임 쪽 동작은 이미 `CYANOTYPE.hasImage(id)` 를 기준으로
자동 적용되므로 이미지 등록만 하면 된다.
