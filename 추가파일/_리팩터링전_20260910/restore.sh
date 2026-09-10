#!/usr/bin/env bash
# 반응형 리팩터링(2026-09-10) 직전 상태로 되돌린다.
# 이 폴더는 프로젝트 루트의 추가파일/_리팩터링전_20260910/ 에 보관돼 있다.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root="$(cd "$here/../.." && pwd)"   # 추가파일/_리팩터링전_20260910 → 프로젝트 루트
cd "$root"
echo "복원 대상 루트: $root"

echo "== 리팩터링 직전 상태로 복원 =="
find "$here" -type f ! -name 'RESTORE.md' ! -name 'restore.sh' ! -name 'CHANGES.tsv' -print0 |
while IFS= read -r -d '' f; do
    rel="${f#"$here"/}"
    mkdir -p "$(dirname "$rel")"
    cp -a "$f" "$rel"
    echo "  복원  $rel"
done

if [ -d itemImages/thumb ]; then
    rm -rf itemImages/thumb
    echo "  삭제  itemImages/thumb/  (리팩터링에서 추가된 폴더)"
fi

echo "완료. _리팩터링전/ 폴더는 필요 없으면 지워도 된다."
