# -*- coding: utf-8 -*-
"""Matplotlib 中文字体：注册本地字体文件并写入 rcParams，避免中文与负号乱码。"""
import os
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import seaborn as sns

FP = None
FONT_PATH = None


def _init_font():
    global FP, FONT_PATH
    FP = None
    FONT_PATH = None
    candidates = [
        ("/System/Library/Fonts/PingFang.ttc", "PingFang SC"),
        ("/System/Library/Fonts/STHeiti Light.ttc", "Heiti SC"),
        ("/Library/Fonts/Arial Unicode.ttf", "Arial Unicode MS"),
        ("/System/Library/Fonts/Supplemental/Songti.ttc", "Songti SC"),
        ("/System/Library/Fonts/Supplemental/Microsoft YaHei.ttf", "Microsoft YaHei"),
    ]
    for path, name in candidates:
        if os.path.exists(path):
            try:
                fm.fontManager.addfont(path)
            except Exception:
                pass
            try:
                fp = fm.FontProperties(fname=path)
                plt.rcParams["font.family"] = [fp.get_name()]
                plt.rcParams["font.sans-serif"] = [fp.get_name(), "DejaVu Sans"]
                plt.rcParams["axes.unicode_minus"] = False
                FP = fp
                FONT_PATH = path
                return FP, fp.get_name()
            except Exception:
                continue
    avail = {f.name for f in fm.fontManager.ttflist}
    for _, name in candidates:
        if name in avail:
            plt.rcParams["font.sans-serif"] = [name, "DejaVu Sans"]
            plt.rcParams["axes.unicode_minus"] = False
            FP = fm.FontProperties(family=name)
            return FP, name
    plt.rcParams["axes.unicode_minus"] = False
    return None, None


sns.set_style("whitegrid")
FP, FONT_NAME = _init_font()


def fp():
    return FP


def apply_cn(ax, title=None, xlabel=None, ylabel=None):
    f = fp()
    if f is None:
        if title:
            ax.set_title(title)
        if xlabel:
            ax.set_xlabel(xlabel)
        if ylabel:
            ax.set_ylabel(ylabel)
        return
    if title:
        ax.set_title(title, fontproperties=f)
    if xlabel:
        ax.set_xlabel(xlabel, fontproperties=f)
    if ylabel:
        ax.set_ylabel(ylabel, fontproperties=f)


def legend_cn(ax, **kw):
    leg = ax.legend(**kw)
    f = fp()
    if f and leg:
        for t in leg.get_texts():
            t.set_fontproperties(f)
    return leg


def heatmap_annot_kw():
    """seaborn heatmap 数字用中文字体，避免方框。"""
    f = fp()
    if f:
        return {"fontproperties": f}
    return {}
