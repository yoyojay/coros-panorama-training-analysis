#!/usr/bin/env python3
"""
负荷平衡与就绪度评估模块（借鉴 R4F SDD 的 EvoLab+ 模型，数据源=高驰官方字段）
================================================================================
高驰 /analyse/query 的 t7dayList 已内置 EWMA 负荷模型：
  - ati = ATL 短期负荷（7 天 EWMA 疲劳）
  - cti = CTL 长期负荷（42 天 EWMA 基础体能）
  - performance / tiredRateNew / trainingLoadRatio 等为高驰官方衍生指标

本模块提供：
  1. acwr()          -> ACWR = ATI / CTI（急性:慢性负荷比）
  2. classify_acwr() -> 负荷平衡状态机（detraining/balanced/rising/excessive）
  3. form()          -> Form = CTI - ATI（体能储备，正=状态好）
  4. readiness()     -> 每日 0-100 就绪度评分（加权：HRV/RHR/疲劳/ACWR）
"""

# ACWR 分档阈值（参考 Tim Gabbett 急性:慢性负荷比研究 + 高驰 EvoLab 口径）
ACWR_BANDS = [
    (0.0, 0.8, "detraining", "减量过度", "刺激不足，体能流失，可上强度"),
    (0.8, 1.3, "balanced", "平衡", "负荷合理，可正常执行课表"),
    (1.3, 1.5, "rising", "快速上升", "负荷陡增，警惕过度训练，强度降档"),
    (1.5, 99.0, "excessive", "过高", "过度训练风险高，强制减量或休息"),
]


def acwr(ati, cti):
    """ACWR = 短期负荷 / 长期负荷。任一缺失返回 None。"""
    if not ati or not cti or cti == 0:
        return None
    return ati / cti


def classify_acwr(ratio):
    """按 ACWR 分档返回 (状态, 中文名, 建议)。ratio=None 时返回未知。"""
    if ratio is None:
        return ("unknown", "未知", "缺少负荷数据")
    for lo, hi, key, name, advice in ACWR_BANDS:
        if lo <= ratio < hi:
            return (key, name, advice)
    return ("unknown", "未知", "超出常规区间")


def form(cti, ati):
    """Form = 长期负荷 - 短期负荷（体能储备，正数=身体处于盈余）。"""
    if cti is None or ati is None:
        return None
    return round(cti - ati, 1)


def hrv_offset(hrv, hrv_base):
    """夜间 HRV 相对基线的偏移比例（%）。正值=恢复盈余。"""
    if not hrv or not hrv_base:
        return None
    return round((hrv - hrv_base) / hrv_base * 100, 1)


def readiness(hrv=None, hrv_base=None, rhr=None, rhr_baseline=50,
              tired=None, ati=None, cti=None, sleep_score=None,
              w_sleep=0.30, w_hrv=0.25, w_rhr=0.15, w_load=0.15, w_tired=0.15):
    """
    每日就绪度评分（0-100）。借鉴 R4F SDD §4.4 加权模型，基于高驰可得字段。
    权重默认：睡眠30% / HRV偏移25% / RHR偏移15% / 负荷平衡15% / 疲劳15%。
    缺失维度自动按剩余权重归一化（不臆造分数）。
    返回 (score, breakdown)。
    """
    parts = {}

    # 睡眠（高驰 sleepScore 未取到时跳过）
    if sleep_score is not None:
        parts["睡眠"] = (w_sleep, max(0, min(100, sleep_score)))

    # HRV 偏移：高于基线越多越好，±30% 封顶
    if hrv is not None and hrv_base:
        off = hrv_offset(hrv, hrv_base)
        score = 50 + off * 1.5          # +10% → 65 分，-10% → 35 分
        parts["HRV偏移"] = (w_hrv, max(0, min(100, round(score))))

    # RHR 偏移：高于基线越少越好（高=疲劳）
    if rhr is not None:
        diff = rhr - rhr_baseline       # +10 → 20 分
        score = 70 - diff * 5
        parts["RHR偏移"] = (w_rhr, max(0, min(100, round(score))))

    # 负荷平衡 ACWR
    ratio = acwr(ati, cti)
    if ratio is not None:
        if ratio < 0.8:
            score = 60
        elif ratio < 1.3:
            score = 85
        elif ratio < 1.5:
            score = 50
        else:
            score = 20
        parts["负荷平衡"] = (w_load, score)

    # 疲劳值 tiredRateNew（低=好，转负=恢复盈余）
    if tired is not None:
        score = 80 - tired * 2.5        # 0→80, 10→55, 27→12
        parts["疲劳"] = (w_tired, max(0, min(100, round(score))))

    if not parts:
        return None, {}

    total_w = sum(w for w, _ in parts.values())
    score = sum(w * s for w, s in parts.values()) / total_w
    return round(score), parts


def readiness_label(score):
    if score is None:
        return "未知"
    if score >= 80:
        return "就绪 · 可上强度"
    if score >= 65:
        return "良好 · 正常训练"
    if score >= 50:
        return "一般 · 保守执行"
    return "需恢复 · 降档或休息"


if __name__ == "__main__":
    # 自测：用 8/16-8/18 真实高驰数据验证
    cases = [
        ("8/12", dict(ati=120, cti=114, hrv=36, hrv_base=45, rhr=49, tired=6)),
        ("8/13", dict(ati=131, cti=116, hrv=37, hrv_base=45, rhr=60, tired=15)),
        ("8/16", dict(ati=146, cti=119, hrv=41, hrv_base=45, rhr=56, tired=27)),
        ("8/17", dict(ati=127, cti=116, hrv=58, hrv_base=45, rhr=47, tired=9)),
        ("8/18", dict(ati=109, cti=114, hrv=None, hrv_base=45, rhr=47, tired=None)),
    ]
    print("日期    ACWR   状态     Form   就绪度  解读")
    for label, c in cases:
        r = acwr(c["ati"], c["cti"])
        key, name, advice = classify_acwr(r)
        f = form(c["cti"], c["ati"])
        sc, parts = readiness(**c)
        lbl = readiness_label(sc)
        print(f"{label}  {r:.2f}  {name}({key})  {f:+5.1f}  {sc if sc is not None else '--':>3}  {lbl}")
        if parts:
            detail = " | ".join(f"{k}:{s:.0f}分(权重{w*100:.0f}%)" for k, (w, s) in parts.items())
            print(f"        {detail}")
