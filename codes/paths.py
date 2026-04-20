# -*- coding: utf-8 -*-
"""项目根目录与数据路径（与作业 ex_P03 的 data/raw、data/clean 对齐）。"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
CLEAN = ROOT / "data" / "clean"
FIG = ROOT / "output" / "figures"
TAB = ROOT / "output" / "tables"


def migrate_legacy_raw() -> None:
    """若存在旧版 data_raw/，一次性复制到 data/raw/。"""
    import shutil

    legacy = ROOT / "data_raw"
    if not legacy.exists():
        return
    RAW.mkdir(parents=True, exist_ok=True)
    for name in [
        "balance_sheet.csv",
        "income_stmt.csv",
        "cashflow.csv",
        "ownership.csv",
        "industry.csv",
        "st_flag.csv",
        "m2.csv",
        ".download_complete",
    ]:
        src, dst = legacy / name, RAW / name
        if src.exists() and not dst.exists():
            shutil.copy2(src, dst)
