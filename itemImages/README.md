# itemImages/

게임에서 사용하는 **가공 완료된 아이템 아이콘**. 투명 배경 PNG, 두 벌로 관리한다.

| 경로 | 크기 | 용도 |
|---|---|---|
| `itemImages/item_<번호>.png` | 512×512 | 사무실 배치구역(무대). `transform:scale` 로 최대 약 4배까지 확대된다 |
| `itemImages/thumb/item_<번호>.png` | 128×128 | 목록·세트 카드(20~26px). 디코딩 메모리 절약용 |

## 왜 두 벌인가

배치구역은 476×337 디자인 좌표계를 브라우저 크기에 맞춰 통째로 scale 한다.
디자인 최대 아이템 124px × 최대 배율 약 4.1 = 약 508px 이라 512px 원본이 필요하다.
반대로 목록 카드는 항상 20~26px 인데 512px 을 물리면
25장 × 512×512×4B = 약 26MB 를 디코딩 메모리로 낭비한다(모바일에서 특히 치명적).

`CYANOTYPE.item(id, size, hires)` 의 세 번째 인자로 어느 쪽을 쓸지 결정한다.
배치구역만 `hires=true`, 나머지는 전부 썸네일.

- 번호는 `index.html` 의 `rawShopItems` 정의(`id: "item_<번호>"`)와 일치한다.
- `index.html` 의 `ITEM_IMAGE_IDS` 목록에 등록된 아이템만 이미지로 렌더되고,
  나머지는 기존 CYANOTYPE 라인아트 아이콘으로 표시된다. 이미지 로드 실패 시에도 라인아트로 폴백한다.

## 새 아이템 이미지 추가 방법

1. 원본 일러스트를 `assets/items/` 에 저장한다.
   파일명은 **아이템 이름**(예: `푹신한 의자.png`) 또는 `item_<번호>.png` 형식.
   원본은 512px 이상 권장(현재 원본들은 1024~1983px).
2. 파이프라인 실행:
   ```bash
   python scripts/process_item_images.py
   ```
   - 여백 자동 크롭 → 정사각 패딩 → 512px / 128px 두 벌 리사이즈 → 최적화 저장
   - `itemImages/item_<번호>.png` + `itemImages/thumb/item_<번호>.png` 생성
   - `index.html` 의 `ITEM_IMAGE_IDS` 자동 갱신
3. 브라우저 캐시를 무효화하려면 `index.html` 의 `ITEM_IMAGE_VERSION` 을 올린다.
4. 결과 확인 후 커밋.

> 주의: 이 스크립트는 `itemImages/` 에 있는 **모든** `item_*.png` 를 `ITEM_IMAGE_IDS` 에 등록한다.
> 아직 게임에 노출하고 싶지 않은 아이템의 원본은 `assets/items/` 에 두지 말 것.

원본(`assets/items/`)은 저장소에 남겨두어 재가공이 가능하도록 한다.
