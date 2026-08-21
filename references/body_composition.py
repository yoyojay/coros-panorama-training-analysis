#!/usr/bin/env python3
"""
身体成分与能量引擎（借鉴 R4F SDD §4.3，数据=用户体重/体脂）
================================================================
  - LBM 去脂体重     = 体重 × (1 - 体脂率)
  - BMR 基础代谢     = 370 + 21.6 × LBM（Katch-McArdle，基于 LBM 更准）
  - TDEE 总消耗      = BMR × 活动因子 + 跑步消耗
  - 跑步消耗估算     ≈ 1.0 kcal/kg/km（高驰 calorie 校验）
  - 宏量营养目标     = 蛋白质 g/kg / 碳水 g/kg / 脂肪 g/kg（耐力备赛口径）
"""


def lbm(weight_kg, bodyfat_pct):
    """去脂体重 LBM。"""
    return weight_kg * (1 - bodyfat_pct / 100)


def bmr_katch(lbm_kg):
    """Katch-McArdle 基础代谢（需要体脂率）。"""
    return 370 + 21.6 * lbm_kg


def bmr_mifflin(weight_kg, height_cm, age, is_male=True):
    """Mifflin-St Jeor 基础代谢（体脂未知时用）。"""
    s = 5 if is_male else -161
    return 10 * weight_kg + 6.25 * height_cm - 5 * age + s


def running_kcal(weight_kg, km):
    """跑步热量消耗估算 ≈ 1.0 kcal/kg/km。"""
    return weight_kg * km


def tdee(bmr, activity_factor=1.55):
    """总能量消耗 = BMR × 活动因子 + 额外运动消耗。
    活动因子：1.2 久坐 / 1.375 轻 / 1.55 中 / 1.725 高 / 1.9 极高。"""
    return bmr * activity_factor


def macro_targets(weight_kg, protein_g=2.0, carb_g=5.0, fat_g=1.0):
    """宏量营养目标（g）。耐力备赛默认：蛋白2.0 / 碳水5.0 / 脂肪1.0 g/kg。"""
    p = weight_kg * protein_g
    c = weight_kg * carb_g
    f = weight_kg * fat_g
    kcal = p * 4 + c * 4 + f * 9
    return {"protein_g": round(p), "carb_g": round(c), "fat_g": round(f),
            "protein_kcal": round(p * 4), "carb_kcal": round(c * 4), "fat_kcal": round(f * 9),
            "total_kcal": round(kcal),
            "pct_protein": round(p * 4 / kcal * 100), "pct_carb": round(c * 4 / kcal * 100),
            "pct_fat": round(f * 9 / kcal * 100)}


if __name__ == "__main__":
    # 自测：用户 71kg / 体脂 20%
    W, BF = 71.0, 20.0
    l = lbm(W, BF)
    bmr = bmr_katch(l)
    print(f"体重 {W}kg / 体脂 {BF}%")
    print(f"LBM 去脂体重     = {l:.1f} kg")
    print(f"BMR 基础代谢     = {bmr:.0f} kcal/天 (Katch-McArdle)")
    print(f"  (Mifflin 对比需身高，未给则不用)")
    for af, name in [(1.2, "久坐"), (1.375, "轻活动"), (1.55, "中活动"), (1.725, "高活动")]:
        print(f"TDEE({name})    = {tdee(bmr, af):.0f} kcal/天")
    print(f"\n跑步消耗估算 @71kg:")
    for km in [7, 12, 20, 22.5, 260]:
        print(f"  {km:>5} km/周 → {running_kcal(W, km):.0f} kcal")
    mt = macro_targets(W)
    print(f"\n宏量目标 (蛋白2.0/碳水5.0/脂肪1.0 g/kg):")
    print(f"  蛋白 {mt['protein_g']}g({mt['protein_kcal']}kcal) · 碳水 {mt['carb_g']}g({mt['carb_kcal']}kcal) · 脂肪 {mt['fat_g']}g({mt['fat_kcal']}kcal)")
    print(f"  合计 ≈{mt['total_kcal']} kcal · 比例 蛋白{mt['pct_protein']}%/碳水{mt['pct_carb']}%/脂肪{mt['pct_fat']}%")
