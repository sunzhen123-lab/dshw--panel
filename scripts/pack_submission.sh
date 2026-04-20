#!/usr/bin/env bash
# 生成坚果云提交包：顶层目录 exP03_姬亚楠/，含 data/raw、output、Notebook、README 等。
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST_DIR="$(cd "$ROOT/.." && pwd)"
NAME="exP03_姬亚楠"
TMP="$(mktemp -d)"
cleanup() { rm -rf "$TMP"; }
trap cleanup EXIT
mkdir -p "$TMP/$NAME"
rsync -a \
  --exclude='.git' \
  --exclude='.venv' \
  --exclude='.mpl' \
  --exclude='_book' \
  --exclude='_site' \
  --exclude='.quarto' \
  --exclude='__pycache__' \
  --exclude='.ipynb_checkpoints' \
  --exclude='.DS_Store' \
  --exclude='data_raw' \
  --exclude='data_clean' \
  "$ROOT/" "$TMP/$NAME/"
tar czvf "$DEST_DIR/${NAME}.tar.gz" -C "$TMP" "$NAME"
( cd "$TMP" && zip -rq "$DEST_DIR/${NAME}.zip" "$NAME" )
echo "已生成: $DEST_DIR/${NAME}.tar.gz 与 $DEST_DIR/${NAME}.zip"
