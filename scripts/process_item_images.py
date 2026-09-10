# -*- coding: utf-8 -*-
"""
월루컴퍼니 아이템 이미지 파이프라인
-----------------------------------
assets/items/ 에 있는 원본 아이템 일러스트(파일명 = 아이템 이름 또는 item_<번호>)를
게임 아이콘 규격에 맞게 가공하여 itemImages/item_<번호>.png 로 등록한다.

필요 패키지: Pillow, numpy, scipy  (pip install pillow numpy scipy)

가공 단계:
  1. 배경 투명화 + 크롭
       - 이미 알파가 있는 이미지: 그 알파를 그대로 사용
       - 흰색 등 단색 배경 이미지: **바깥 테두리에서 연결된 배경색 영역만** 투명화한다.
         (모니터 베젤·키보드 키·형광펜 몸통 같은 내부 흰색은 테두리와 끊겨 있어 보존된다.
          예전엔 '흰색이면 무조건 투명' 이라 이 부분들에 구멍이 뚫렸다.)
  2. 정사각 캔버스에 중앙 정렬 + 소량 패딩
  3. 두 가지 크기로 리사이즈 (LANCZOS)
       - itemImages/item_<n>.png        : ICON_SIZE(512px)  — 사무실 배치용 원본
       - itemImages/thumb/item_<n>.png  : THUMB_SIZE(128px) — 목록 카드용 썸네일
  4. 최적화 저장 (RGBA optimize vs 256색 양자화 중 작은 쪽 선택)
  5. index.html 의 ITEM_IMAGE_IDS 목록 자동 갱신

왜 두 벌인가:
  배치구역은 transform:scale 로 최대 4배까지 확대되므로(디자인 124px x 배율 4.1 = 508px)
  512px 원본이 필요하다. 반대로 목록 카드는 항상 20~26px 이라 512px 을 물리면
  25장 x 512x512x4B = 26MB 의 디코딩 메모리를 낭비한다(모바일에서 특히 치명적).

새 이미지를 assets/items/ 에 추가한 뒤 다시 실행하면 된다.

사용법:
  python scripts/process_item_images.py
"""
import os
import re
import sys
import io

import numpy as np
from scipy import ndimage
from PIL import Image, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(ROOT, "assets", "items")
OUT_DIR = os.path.join(ROOT, "itemImages")
THUMB_DIR = os.path.join(OUT_DIR, "thumb")
INDEX_HTML = os.path.join(ROOT, "index.html")

ICON_SIZE = 512          # 배치구역 최대 렌더: 디자인 124px x 배율 4.1 = 508px (DPR1 기준 무손실)
THUMB_SIZE = 128         # 목록 카드 렌더: 20~26px, 레티나(DPR2~3) 대비 여유 확보
PADDING_RATIO = 0.06     # 크롭 후 정사각 캔버스에 넣을 때 가장자리 여백
ALPHA_THRESHOLD = 12     # 이 값 이하 알파는 배경으로 간주
BG_DIFF_THRESHOLD = 60   # 테두리 배경색과 이 L1 색거리 이하이면 배경 후보
                         # (테두리에서 연결된 성분만 배경으로 인정하므로 느슨해도 안전.
                         #  일러스트 배경에 미묘한 그라데이션/비네팅이 있어 넉넉히 잡는다)
BG_GROW_PX = 2           # 배경 판정 후 안쪽으로 이만큼 더 깎아 흰 테두리 halo 제거


def build_name_to_id():
    """index.html 의 rawShopItems 정의에서 '아이템 이름' -> 'item_<n>' 매핑을 만든다."""
    html = open(INDEX_HTML, encoding="utf-8").read()
    mapping = {}
    for m in re.finditer(r'id:\s*"(item_\d+)"\s*,\s*name:\s*"([^"]+)"', html):
        mapping[m.group(2).strip()] = m.group(1)
    return mapping


def resolve_item_id(filename, name_to_id):
    stem = os.path.splitext(os.path.basename(filename))[0].strip()
    m = re.match(r"^item[_\-\s]?0*(\d+)$", stem, re.IGNORECASE)
    if m:
        return "item_" + str(int(m.group(1)))
    if stem in name_to_id:
        return name_to_id[stem]
    # 공백/언더스코어 차이 흡수
    norm = re.sub(r"\s+", "", stem)
    for nm, iid in name_to_id.items():
        if re.sub(r"\s+", "", nm) == norm:
            return iid
    return None


def _has_real_alpha(im):
    """이미 투명 채널이 의미 있게 들어있는 이미지인지."""
    if im.mode not in ("RGBA", "LA") and "transparency" not in im.info:
        return False
    a = im.convert("RGBA").split()[3]
    return a.getextrema()[0] < 250


def _strip_flat_background(im_rgb):
    """단색(주로 흰색) 배경 이미지의 배경만 투명화한다.

    핵심: '배경색과 비슷한 픽셀' 전부가 아니라, **바깥 테두리에서 연결된** 영역만
    배경으로 인정한다. 모니터 베젤·키보드 키·형광펜 몸통처럼 내부에 있는 흰색은
    사방이 내용물로 둘러싸여 테두리와 끊겨 있으므로 그대로 불투명하게 남는다.
    (이전 버전은 '흰색이면 무조건 투명' 이라 이 부분들에 구멍이 뚫렸다.)
    """
    arr = np.asarray(im_rgb.convert("RGB"), dtype=np.int16)
    h, w = arr.shape[:2]

    # 배경색 = 바깥 1px 테두리 링 전체의 중앙값
    # (코너 4점만 보면 배경 그라데이션에 취약. 링 전체가 더 견고하다)
    ring = np.concatenate([arr[0, :], arr[-1, :], arr[:, 0], arr[:, -1]])
    bg = np.median(ring, axis=0)

    is_bgcolor = np.abs(arr - bg).sum(axis=2) <= BG_DIFF_THRESHOLD

    # 테두리에 닿은 연결 성분만 진짜 배경
    labels, _ = ndimage.label(is_bgcolor)
    edge_labels = np.unique(np.concatenate(
        [labels[0, :], labels[-1, :], labels[:, 0], labels[:, -1]]
    ))
    edge_labels = edge_labels[edge_labels != 0]
    bg_mask = np.isin(labels, edge_labels)

    # 경계의 반투명 안티에일리어싱 링(흰 halo)을 배경 쪽으로 조금 더 깎는다
    if BG_GROW_PX > 0:
        bg_mask = ndimage.binary_dilation(bg_mask, iterations=BG_GROW_PX)

    alpha = np.where(bg_mask, 0, 255).astype(np.uint8)
    # 남은 계단현상 완화(내부 구멍은 이미 없으므로 가장자리에만 영향)
    alpha = np.asarray(Image.fromarray(alpha, "L").filter(ImageFilter.GaussianBlur(0.8)))

    out = np.dstack([np.asarray(im_rgb.convert("RGB")), alpha])
    return Image.fromarray(out, "RGBA")


def autocrop(im):
    """배경을 투명화한 뒤 내용 영역 bbox 로 잘라낸다."""
    if _has_real_alpha(im):
        im = im.convert("RGBA")
        mask = im.split()[3].point(lambda v: 255 if v > ALPHA_THRESHOLD else 0)
    else:
        im = _strip_flat_background(im)
        mask = im.split()[3].point(lambda v: 255 if v > ALPHA_THRESHOLD else 0)

    bbox = mask.getbbox()
    if bbox:
        im = im.crop(bbox)
    return im


def to_square(im):
    """크롭 + 정사각 패딩까지만 수행(리사이즈 전 단계)."""
    im = autocrop(im)
    w, h = im.size
    side = max(w, h)
    canvas_side = int(round(side / (1 - 2 * PADDING_RATIO)))
    canvas = Image.new("RGBA", (canvas_side, canvas_side), (0, 0, 0, 0))
    canvas.paste(im, ((canvas_side - w) // 2, (canvas_side - h) // 2), im)
    return canvas


def to_icon(im, size=None):
    return to_square(im).resize((size or ICON_SIZE, size or ICON_SIZE), Image.LANCZOS)


def optimized_bytes(im):
    """RGBA 최적화본과 256색 양자화본 중 더 작은 쪽을 반환."""
    a = io.BytesIO()
    im.save(a, format="PNG", optimize=True)

    b = io.BytesIO()
    q = im.quantize(colors=256, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE)
    q.save(b, format="PNG", optimize=True)

    return a.getvalue() if len(a.getvalue()) <= len(b.getvalue()) else b.getvalue()


def update_index_html(ids):
    # newline="" 로 열고 써야 원본 줄바꿈(CRLF)이 LF 로 뭉개지지 않는다.
    # (기본 텍스트 모드는 읽을 때 CRLF->LF 로 바꾸고 쓸 때 되돌리지 않는다)
    html = io.open(INDEX_HTML, encoding="utf-8", newline="").read()
    joined = ", ".join('"%s"' % i for i in sorted(ids, key=lambda s: int(s.split("_")[1])))
    new_line = "  const ITEM_IMAGE_IDS = new Set([%s]);" % joined
    pat = re.compile(r"^\s*const ITEM_IMAGE_IDS = new Set\(\[[^\]]*\]\);", re.MULTILINE)
    if not pat.search(html):
        print("  ! index.html 에 ITEM_IMAGE_IDS 선언이 없어 갱신을 건너뜀")
        return
    html = pat.sub(new_line, html, count=1)
    io.open(INDEX_HTML, "w", encoding="utf-8", newline="").write(html)
    print("  index.html ITEM_IMAGE_IDS 갱신 (%d개)" % len(ids))


def main():
    if not os.path.isdir(SRC_DIR):
        sys.exit("원본 폴더가 없습니다: " + SRC_DIR)
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(THUMB_DIR, exist_ok=True)
    name_to_id = build_name_to_id()

    processed = []
    for fn in sorted(os.listdir(SRC_DIR)):
        if not fn.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
            continue
        src = os.path.join(SRC_DIR, fn)
        iid = resolve_item_id(fn, name_to_id)
        if not iid:
            print("  ? 매핑 실패 (건너뜀): %s" % fn)
            continue
        n = int(iid.split("_")[1])
        im = Image.open(src)
        square = to_square(im)   # 크롭/패딩은 한 번만 하고 두 크기로 재사용

        data = optimized_bytes(square.resize((ICON_SIZE, ICON_SIZE), Image.LANCZOS))
        with open(os.path.join(OUT_DIR, "item_%d.png" % n), "wb") as f:
            f.write(data)

        tdata = optimized_bytes(square.resize((THUMB_SIZE, THUMB_SIZE), Image.LANCZOS))
        with open(os.path.join(THUMB_DIR, "item_%d.png" % n), "wb") as f:
            f.write(tdata)

        processed.append(iid)
        print("  %-22s -> item_%d.png  (%.1f KB / thumb %.1f KB)"
              % (fn, n, len(data) / 1024, len(tdata) / 1024))

    if not processed:
        print("처리된 이미지가 없습니다.")
        return

    # 기존 itemImages 폴더 내용까지 포함해 목록 구성 (thumb/ 하위폴더는 제외)
    existing = set()
    for fn in os.listdir(OUT_DIR):
        if os.path.isdir(os.path.join(OUT_DIR, fn)):
            continue
        m = re.match(r"item_(\d+)\.png$", fn)
        if m:
            existing.add("item_" + str(int(m.group(1))))
    update_index_html(existing)
    print("완료: %d개 이미지 등록" % len(existing))


if __name__ == "__main__":
    main()
