# -*- coding: utf-8 -*-
"""
월루컴퍼니 아이템 이미지 파이프라인
-----------------------------------
assets/items/ 에 있는 원본 아이템 일러스트(파일명 = 아이템 이름 또는 item_<번호>)를
게임 아이콘 규격에 맞게 가공하여 itemImages/item_<번호>.png 로 등록한다.

가공 단계:
  1. 여백(투명/단색 배경) 자동 감지 후 크롭
  2. 정사각 캔버스에 중앙 정렬 + 소량 패딩
  3. 아이콘 크기(ICON_SIZE)로 리사이즈 (LANCZOS)
  4. 최적화 저장 (RGBA optimize vs 256색 양자화 중 작은 쪽 선택)
  5. index.html 의 ITEM_IMAGE_IDS 목록 자동 갱신

새 이미지를 assets/items/ 에 추가한 뒤 다시 실행하면 된다.

사용법:
  python scripts/process_item_images.py
"""
import os
import re
import sys
import io

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(ROOT, "assets", "items")
OUT_DIR = os.path.join(ROOT, "itemImages")
INDEX_HTML = os.path.join(ROOT, "index.html")

ICON_SIZE = 128          # 게임 내 최대 렌더 34px, 레티나 대비 여유 확보
PADDING_RATIO = 0.06     # 크롭 후 정사각 캔버스에 넣을 때 가장자리 여백
ALPHA_THRESHOLD = 12     # 이 값 이하 알파는 배경으로 간주
BG_DIFF_THRESHOLD = 18   # 단색 배경과의 색 차이 허용치


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


def autocrop(im):
    """투명 배경이면 알파 기준, 아니면 코너 단색 기준으로 내용 영역 bbox 계산."""
    im = im.convert("RGBA")
    r, g, b, a = im.split()

    if a.getextrema()[0] < 250:  # 실제로 투명 영역이 존재
        mask = a.point(lambda v: 255 if v > ALPHA_THRESHOLD else 0)
    else:
        # 단색 배경 추정: 네 코너 평균색
        w, h = im.size
        corners = [im.getpixel(p) for p in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]]
        bg = tuple(sum(c[i] for c in corners) // 4 for i in range(3))
        bg_img = Image.new("RGB", im.size, bg)
        diff = Image.eval(
            _rgb_distance(im.convert("RGB"), bg_img),
            lambda v: 255 if v > BG_DIFF_THRESHOLD else 0,
        )
        mask = diff
        # 배경을 투명으로
        im.putalpha(mask)

    bbox = mask.getbbox()
    if bbox:
        im = im.crop(bbox)
    return im


def _rgb_distance(img, bg):
    from PIL import ImageChops
    return ImageChops.difference(img, bg).convert("L")


def to_icon(im):
    im = autocrop(im)
    w, h = im.size
    side = max(w, h)
    canvas_side = int(round(side / (1 - 2 * PADDING_RATIO)))
    canvas = Image.new("RGBA", (canvas_side, canvas_side), (0, 0, 0, 0))
    canvas.paste(im, ((canvas_side - w) // 2, (canvas_side - h) // 2), im)
    return canvas.resize((ICON_SIZE, ICON_SIZE), Image.LANCZOS)


def optimized_bytes(im):
    """RGBA 최적화본과 256색 양자화본 중 더 작은 쪽을 반환."""
    a = io.BytesIO()
    im.save(a, format="PNG", optimize=True)

    b = io.BytesIO()
    q = im.quantize(colors=256, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE)
    q.save(b, format="PNG", optimize=True)

    return a.getvalue() if len(a.getvalue()) <= len(b.getvalue()) else b.getvalue()


def update_index_html(ids):
    html = open(INDEX_HTML, encoding="utf-8").read()
    joined = ", ".join('"%s"' % i for i in sorted(ids, key=lambda s: int(s.split("_")[1])))
    new_line = "  const ITEM_IMAGE_IDS = new Set([%s]);" % joined
    pat = re.compile(r"^\s*const ITEM_IMAGE_IDS = new Set\(\[[^\]]*\]\);", re.MULTILINE)
    if not pat.search(html):
        print("  ! index.html 에 ITEM_IMAGE_IDS 선언이 없어 갱신을 건너뜀")
        return
    html = pat.sub(new_line, html, count=1)
    open(INDEX_HTML, "w", encoding="utf-8").write(html)
    print("  index.html ITEM_IMAGE_IDS 갱신 (%d개)" % len(ids))


def main():
    if not os.path.isdir(SRC_DIR):
        sys.exit("원본 폴더가 없습니다: " + SRC_DIR)
    os.makedirs(OUT_DIR, exist_ok=True)
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
        icon = to_icon(im)
        data = optimized_bytes(icon)
        out = os.path.join(OUT_DIR, "item_%d.png" % n)
        with open(out, "wb") as f:
            f.write(data)
        processed.append(iid)
        print("  %-22s -> itemImages/item_%d.png  (%.1f KB)" % (fn, n, len(data) / 1024))

    if not processed:
        print("처리된 이미지가 없습니다.")
        return

    # 기존 itemImages 폴더 내용까지 포함해 목록 구성
    existing = set()
    for fn in os.listdir(OUT_DIR):
        m = re.match(r"item_(\d+)\.png$", fn)
        if m:
            existing.add("item_" + str(int(m.group(1))))
    update_index_html(existing)
    print("완료: %d개 이미지 등록" % len(existing))


if __name__ == "__main__":
    main()
