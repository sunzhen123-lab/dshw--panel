#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P03 主入口：AkShare 拉取真实财报 → 合并清洗 → 描述与面板回归 → 出图。
  python run_p03.py
  python run_p03.py --download
环境变量 P03_MAX_STOCKS：下载股票数上限（默认 100）。
原始数据目录：data/raw/（与 ex_P03 一致）；若仅有旧版 data_raw/ 会自动复制。
"""
import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
_mpl = ROOT / ".mpl"
_mpl.mkdir(exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(_mpl))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--download", action="store_true", help="强制重新下载 data/raw")
    args = ap.parse_args()

    from codes.paths import migrate_legacy_raw
    from codes.fetch_real import download_raw
    from codes.panel_build import build_panel
    from codes.analysis_run import run_all

    migrate_legacy_raw()
    download_raw(force=args.download)
    df = build_panel()
    run_all(df)
    print("\n全部完成。输出见 output/figures、output/tables 与 data/clean/。")


if __name__ == "__main__":
    main()
