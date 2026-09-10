# itemImages/

게임에서 사용하는 **가공 완료된 아이템 아이콘**. `item_<번호>.png`, 128×128, 투명 배경.

- 번호는 `index.html` 의 `rawShopItems` 정의(`id: "item_<번호>"`)와 일치한다.
- `index.html` 의 `ITEM_IMAGE_IDS` 목록에 등록된 아이템만 이미지로 렌더되고,
  나머지는 기존 CYANOTYPE 라인아트 아이콘으로 표시된다. 이미지 로드 실패 시에도 라인아트로 폴백한다.

## 새 아이템 이미지 추가 방법

1. 원본 일러스트를 `assets/items/` 에 저장한다.
   파일명은 **아이템 이름**(예: `푹신한 의자.png`) 또는 `item_<번호>.png` 형식.
2. 파이프라인 실행:
   ```bash
   python scripts/process_item_images.py
   ```
   - 여백 자동 크롭 → 정사각 패딩 → 128px 리사이즈 → 최적화 저장
   - `itemImages/item_<번호>.png` 생성
   - `index.html` 의 `ITEM_IMAGE_IDS` 자동 갱신
3. 결과 확인 후 커밋.

원본(`assets/items/`)은 저장소에 남겨두어 재가공이 가능하도록 한다.
