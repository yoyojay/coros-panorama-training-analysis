#!/usr/bin/env python3
"""
热适应评价机制 (Heat Acclimation Evaluation)
=============================================
把 COROS 训练 + Open-Meteo 天气，转成可量化、可跨日比较的「热应激 / 热适应」指标。

背景与公式来源
--------------
参考科普《体感温度都是怎么算出来的？》(微信 mp.weixin.qq.com/s/WqEdhH4GMZ_D4dpFDnKskg)：
  - 室温远低于体温时，散热靠热传导，湿度影响小；
  - 室温接近/高于体温时，散热几乎全靠排汗蒸发，此时相对湿度越高体感越热；
  - 对「在高温环境运动的人群」，应认准 **湿球黑球温度 WBGT**（湿球+黑球+干球），
    而非普通天气 App 的「体感温度」。

本模块给出三档"体感/热负荷"量：
  1) 澳式体感温度 AT  (Steadman 1994)        —— T + RH + 风 叠加的"feels like"
  2) 酷热指数 HI      (Rothfusz/NOAA)         —— 高温高湿的"feels like"（美国气象标准）
  3) 估算 WBGT        (0.7·Twb + 0.3·T)        —— 运动热应激金标准（无日照近似）

并给出：热应激分级（ACSM/美军 WBGT 阈值）→ 训练强度调整建议，
以及跨日**热适应追踪**信号（同配速 HR、心率漂移、饱和湿度下"湿透"非负面信号）。

所有函数纯 Python（math），无原生依赖，可在 WorkBuddy 托管 Python 直接 import。
"""

import math

# 乳酸阈心率（用户，来自训练档案）；用于把 avgHR 换算成 %LT 强度
LT_HR = 178.0


# --------------------------------------------------------------------------- #
# 基础物理量
# --------------------------------------------------------------------------- #
def dew_point(T: float, RH: float) -> float:
    """露点温度 (°C)，Magnus 公式。RH=100% 时露点≈气温。"""
    a, b = 17.625, 243.04
    g = math.log(max(RH, 1e-6) / 100.0) + (a * T) / (b + T)
    return (b * g) / (a - g)


def wet_bulb_stull(T: float, RH: float) -> float:
    """湿球温度 (°C)，Stull 2011 经验式。0–40°C、RH 5–99% 内误差 ≈ ±0.3°C。
    atan 用弧度。"""
    return (T * math.atan(0.151977 * math.sqrt(RH + 8.313659))
            + math.atan(T + RH) - math.atan(RH - 1.676331)
            + 0.00391838 * math.pow(RH, 1.5) * math.atan(0.023101 * RH)
            - 4.686035)


def vapor_pressure(T: float, RH: float) -> float:
    """水汽压 e (hPa)。"""
    return (RH / 100.0) * 6.105 * math.exp(17.27 * T / (237.7 + T))


# --------------------------------------------------------------------------- #
# 三档"体感 / 热负荷"
# --------------------------------------------------------------------------- #
def apparent_temp_au(T: float, RH: float, wind_kmh: float) -> float:
    """澳式体感温度 AT (Steadman 1994)，°C。
    AT = T + 0.33·e − 0.70·ws − 4.00，ws 为 m/s。"""
    ws = wind_kmh / 3.6
    e = vapor_pressure(T, RH)
    return T + 0.33 * e - 0.70 * ws - 4.00


def heat_index(T: float, RH: float) -> float:
    """酷热指数 HI (Rothfusz/NOAA)，°C。基于华氏回归再转回摄氏。
    适用于暖环境；T<26.7°C 时偏保守（可能低于实际体感），仅作参考。"""
    Tf = T * 9.0 / 5.0 + 32.0
    Rh = RH
    HI = (-42.379 + 2.04901523 * Tf + 10.14333127 * Rh
          - 0.22475541 * Tf * Rh - 0.00683783 * Tf * Tf - 0.05481717 * Rh * Rh
          + 0.00122874 * Tf * Tf * Rh + 0.00085282 * Tf * Rh * Rh
          - 0.00000199 * Tf * Tf * Rh * Rh)
    # 高/低湿度的微调（NOAA）
    if Rh < 13 and 80 <= Tf <= 112:
        HI -= ((13 - Rh) / 4.0) * math.sqrt((17 - abs(Tf - 95.0)) / 17.0)
    elif Rh > 85 and 80 <= Tf <= 87:
        HI += ((Rh - 85) / 10.0) * ((87 - Tf) / 5.0)
    return (HI - 32.0) * 5.0 / 9.0


def est_wbgt(T: float, RH: float) -> float:
    """估算 WBGT（无日照 / 遮阴近似）= 0.7·Twb + 0.3·T。
    完整户外 WBGT = 0.7·Twb + 0.2·Tg(黑球) + 0.1·T。清晨/低日照跑步用无日照近似即可，
    是运动热应激的保守基线（不含太阳辐射加热）。"""
    return 0.7 * wet_bulb_stull(T, RH) + 0.3 * T


# --------------------------------------------------------------------------- #
# 热应激分级 → 训练强度调整（ACSM / 美军 WBGT 阈值）
# --------------------------------------------------------------------------- #
def heat_category(wbgt: float):
    """返回 (等级, 颜色键, 训练建议)。颜色键对应 Ride Relief 调色板：
    ok / warn / hot / danger / extreme。"""
    if wbgt < 18:
        return ("低风险", "ok", "正常训练，充分补水")
    if wbgt < 23:
        return ("注意", "ok", "正常训练，增加电解质补给")
    if wbgt < 28:
        return ("中度风险", "warn", "强度降 5–10%，延长补给，监控 HR")
    if wbgt < 33:
        return ("高度风险", "hot", "强度降 10–20%，缩短时长，严控 HR 上限")
    return ("极高风险", "danger", "取消高强度，仅轻松有氧或改室内")


# --------------------------------------------------------------------------- #
# 单跑热适应评价
# --------------------------------------------------------------------------- #
def evaluate_run(T, RH, wind_kmh, avg_hr, pace_s, label="", note=""):
    """对单次跑步做热适应评价，返回字典。
    pace_s: 平均配速（秒/km）。avg_hr: 平均心率。"""
    at = apparent_temp_au(T, RH, wind_kmh)
    hi = heat_index(T, RH)
    wbgt = est_wbgt(T, RH)
    tdp = dew_point(T, RH)
    pct_lt = avg_hr / LT_HR * 100.0
    grade, color, advice = heat_category(wbgt)
    # 饱和判定：湿度≥95% 时汗液几乎无法蒸发，"湿透"是物理必然而非退步信号
    saturated = RH >= 95
    return {
        "label": label, "T": T, "RH": RH, "wind": wind_kmh,
        "dew": tdp, "apparent": at, "heat_index": hi, "wbgt": wbgt,
        "pct_lt": pct_lt, "pace_s": pace_s, "avg_hr": avg_hr,
        "grade": grade, "color": color, "advice": advice,
        "saturated": saturated, "note": note,
    }


# --------------------------------------------------------------------------- #
# 跨日热适应追踪
# --------------------------------------------------------------------------- #
def acclimation_table(runs):
    """runs: evaluate_run 结果列表（按日期升序）。
    计算每跑「同强度配速效率」= pace_s / pct_lt（数值越小=同样强度下配速越快），
    并标注与"最低 WBGT 参考跑"相比的热折损（heat penalty）。
    返回带衍生字段的列表 + 文字信号。"""
    if not runs:
        return [], ""
    ref = min(runs, key=lambda r: r["wbgt"])  # 最凉参考
    out = []
    for r in runs:
        pace_per_lt = r["pace_s"] / r["pct_lt"]  # s/km per %LT
        # 热折损：在同样 %LT 下，若与最凉参考跑效率相同，预期配速；实际更慢=被热拖累
        expected_pace = ref["pace_s"] / ref["pct_lt"] * r["pct_lt"]
        penalty = r["pace_s"] - expected_pace  # 秒/km，正值=热致变慢
        out.append({**r, "pace_per_lt": pace_per_lt,
                    "expected_pace": expected_pace, "heat_penalty": penalty})
    # 信号：在相同/相近 WBGT 下，pace_per_lt 是否随日期改善（变小）
    signals = []
    # 找同样配速、HR 下降的相邻对比（核心适应信号）
    by_pace = sorted(out, key=lambda r: r["pace_s"])
    # 同配速(±3s) 不同日 → HR 变化
    for i in range(len(by_pace)):
        for j in range(i + 1, len(by_pace)):
            a, b = by_pace[i], by_pace[j]
            if abs(a["pace_s"] - b["pace_s"]) <= 3 and a["label"] != b["label"]:
                dh = b["avg_hr"] - a["avg_hr"]
                if dh < -3:
                    signals.append(
                        f"{b['label']} 与 {a['label']} 同配速 {fmt_pace(b['pace_s'])}，"
                        f"HR 由 {a['avg_hr']} 降到 {b['avg_hr']}（{dh}bpm），"
                        f"热适应正向信号")
                elif dh > 3:
                    signals.append(
                        f"{b['label']} 与 {a['label']} 同配速 {fmt_pace(b['pace_s'])}，"
                        f"HR 升高 {dh}bpm，注意是否疲劳累积或热负荷更高")
    if not signals:
        signals.append("暂无同配速跨日样本，继续累积热季数据以观察适应趋势")
    return out, signals


def fmt_pace(s):
    s = float(s)
    return f"{int(s // 60)}:{int(s % 60):02d}"


if __name__ == "__main__":
    # 快速自检：4 次热季跑
    demo = [
        evaluate_run(28.9, 77, 14.9, 146, 371, "8/8"),
        evaluate_run(25.6, 94, 29.2, 148, 357, "8/9"),
        evaluate_run(28.1, 84, 15.9, 154, 343, "8/11"),
        evaluate_run(25.9, 94, 5.1, 149, 343, "8/12"),
    ]
    for r in demo:
        print(f"{r['label']}: T{r['T']} RH{r['RH']}% wbgt={r['wbgt']:.1f} "
              f"AT={r['apparent']:.1f} HI={r['heat_index']:.1f} "
              f"{r['grade']} pace/fLT={r['pace_s']/r['pct_lt']:.2f}")
