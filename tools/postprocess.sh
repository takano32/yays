#!/bin/bash
# Post-process the wget mirror for GitHub Pages:
# 1) detect & convert Shift_JIS(CP932) text files to UTF-8
# 2) rewrite <meta charset> declarations
# 3) report files with problematic names for GitHub Pages
set -u
SITE="$1"   # path to the ~yays directory root

echo "=== encoding census (nkf --guess) ==="
find "$SITE" -type f \( -name '*.html' -o -name '*.htm' -o -name '*.css' -o -name '*.js' -o -name '*.txt' \) -print0 |
  while IFS= read -r -d '' f; do
    enc=$(nkf --guess "$f" 2>/dev/null | head -1)
    echo "$enc|$f"
  done | tee /tmp/claude-1000/-home-takano32-GitHub-yays/c47f8e8d-a0a6-4acf-8cd7-b92ff5ea5b25/scratchpad/enc_census.txt | cut -d'|' -f1 | sort | uniq -c

echo
echo "=== converting Shift_JIS/CP932 files to UTF-8 ==="
count=0
while IFS='|' read -r enc f; do
  case "$enc" in
    Shift_JIS*|CP932*|Windows-31J*)
      nkf -w -Lu --overwrite "$f" && count=$((count+1)) ;;
    EUC-JP*)
      nkf -w -Lu --overwrite "$f" && count=$((count+1)) ;;
  esac
done < /tmp/claude-1000/-home-takano32-GitHub-yays/c47f8e8d-a0a6-4acf-8cd7-b92ff5ea5b25/scratchpad/enc_census.txt
echo "converted: $count files"

echo
echo "=== rewriting meta charset declarations ==="
grep -rlIiE 'charset=("?)(shift_jis|x-sjis|shift-jis|euc-jp)' "$SITE" --include='*.html' --include='*.htm' |
  while IFS= read -r f; do
    sed -i -E 's/charset=("?)(shift_jis|x-sjis|shift-jis|euc-jp)/charset=\1utf-8/Ig' "$f"
    echo "meta fixed: $f"
  done

echo
echo "=== files with names problematic for GitHub Pages (?, #, %, non-ascii, trailing space) ==="
find "$SITE" -name '*\?*' -o -name '*#*' -o -name '*%*' | head -50
find "$SITE" -type f | grep -P '[^\x00-\x7F]' | head -50
echo "(end)"

echo
echo "=== remaining non-UTF8 text files (should be none) ==="
find "$SITE" -type f \( -name '*.html' -o -name '*.htm' -o -name '*.css' -o -name '*.js' -o -name '*.txt' \) -print0 |
  while IFS= read -r -d '' f; do
    enc=$(nkf --guess "$f" 2>/dev/null | head -1)
    case "$enc" in
      UTF-8*|ASCII*|BINARY*) ;;
      *) echo "$enc|$f" ;;
    esac
  done
echo "(end)"
