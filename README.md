# 基于高驰数据的全景训练分析（COROS Panorama Training Analysis）

> 一个可复用的 AI 技能包：拉取高驰（COROS）训练数据，融合真实天气与身体状态，输出多维度的训练分析 HTML 报告。

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Report](https://img.shields.io/badge/Report-HTML%20%2F%20Chart.js-FF6B5F)
![Data](https://img.shields.io/badge/Data-COROS%20%2B%20Open--Meteo-72E8FF)

---

## 一、这是什么

这是一个面向**严肃跑者 / 全马备赛人群**的训练数据分析工具，本质上是一个「AI 技能包（Skill）」：

- 通过高驰（COROS）开放接口，**拉取你的活动、逐公里明细、每日恢复与负荷平衡数据**；
- 融合 **Open-Meteo 真实历史天气**（温度 / 湿度 / 风 / 降水）与你的身体参数（体重 / 体脂 / 乳酸阈）；
- 输出一份**可离线打开、交互式、Ride Relief 暗黑风格**的 HTML 训练报告，涵盖配速、心率分区、热适应、负荷与就绪度、身体成分与能量等维度。

它既可以作为 WorkBuddy / 类似 Agent 的 Skill 直接调用，也可以当作纯 Python 脚本独立运行——**零 MCP 依赖，只要装一个 `httpx`**。

---

## 二、核心能力（五大分析引擎）

| 引擎 | 模块 | 核心产出 |
|------|------|----------|
| **逐公里技术分解** | `activity/detail/query` 明细 | 每公里 配速 / 心率 / 步频 / 步幅 / 垂直振幅 / 功率 |
| **心率 6 区比例** | `frequencyList` 逐秒统计 | 恢复(<142) / 有氧耐力(142-159) / 有氧动力(160-168) / 乳酸阈(169-181) / 速度耐力(182-188) / 无氧动力(>188) 占比 |
| **热适应评价** | `references/heat_metrics.py` | 露点 / 湿球 / 澳式体感 / 酷热指数 / 估算 WBGT + 跨日适应信号（同配速心率变化） |
| **负荷平衡与就绪度** | `references/load_balance.py` | ACWR(ATI/CTI) / Form(体能储备) / 每日就绪度 0-100 评分 + 分档建议 |
| **身体成分与能量** | `references/body_composition.py` | LBM / BMR / TDEE / 跑步消耗估算 / 宏量营养目标 |
| **天气（报告必含）** | Open-Meteo 历史归档 | 训练当日 温度 / 湿度 / 风 / 降水 + WMO 天气代码 |
| **报告呈现** | `references/ride_relief_style.css` | Ride Relief 暗黑风格 + Chart.js 内联（离线可用）+ 双重质量门禁 |

> **为什么强调「天气必含」？** 气温 33°C+ 时，同等配速下心率天然偏高、配速回退 10–25s 属正常，不应判为「退步」。缺天气的跑评等于少了一半判读上下文。

---

## 三、快速开始

### 1. 安装依赖

```bash
pip install httpx   # 唯一依赖，纯 Python
```

### 2. 配置高驰账号

凭据**只通过环境变量注入，脚本零存储**（详见隐私声明）：

```bash
export COROS_EMAIL=you@example.com
export COROS_PASSWORD=your_password
```

- 区域 `asia`（中国区 `teamcnapi.coros.com`，默认）/ `eu` / `us`，在 `scripts/fetch_data.py` 顶部 `COROS_REGION` 修改。
- 若登录失败，请确认账号密码正确；密码会以 MD5 哈希后传输。

### 3. 拉取数据

```bash
python3 scripts/fetch_data.py 20260801 20260818
#                                        ↑开始日   ↑结束日 (YYYYMMDD)
```

输出 `coros_20260801_20260818.json`（含 `metrics` / `analyse`(ati,cti) / `activities`）。

### 4. 生成报告

```bash
python3 scripts/generate_report.py
```

生成一份交互式 HTML 报告，**浏览器直接打开即可**（Chart.js 已内联，完全离线可用）。

---

## 四、目录结构

```
coros-panorama-training-analysis/
├── SKILL.md                    # 技能定义（API 参考、踩坑经验、质量门禁，给 Agent 读）
├── README.md                   # 你正在看的这份详细说明
├── LICENSE                     # MIT
├── references/
│   ├── ride_relief_style.css   # Ride Relief 设计系统（自包含可内联）
│   ├── heat_metrics.py         # 热适应：WBGT / 体感 / 露点 / 跨日适应
│   ├── load_balance.py         # ACWR / Form / 就绪度
│   └── body_composition.py     # LBM / BMR / 能量
└── scripts/
    ├── fetch_data.py           # COROS API 数据拉取（环境变量鉴权）
    └── generate_report.py      # 报告生成（周报 / 月报模板）
```

---

## 五、个性化配置

分析前请将示例参数替换为你自己的值（示例仅供参考）：

| 参数 | 示例值 | 位置 |
|------|--------|------|
| 乳酸阈心率 / 功率 | 178 bpm / 277 W | `references/heat_metrics.py` 顶部 `LT_HR` |
| 体重 / 体脂 | 71 kg / 20% | `references/body_composition.py` |
| 常驻城市坐标 | 杭州 30.2741, 120.1551 | `fetch_data.py` 天气接口参数 |

> 注意：报告里的心率 6 区阈值、乳酸阈等是**个人化指标**，务必换成自己的真实数据，结论才有意义。

---

## 六、报告设计系统：Ride Relief

报告采用用户指定的 **Ride Relief / Route Relief** 暗黑风格（改编自 [op7418/guizang-sports-skill](https://github.com/op7418/guizang-sports-skill)），取代旧版深蓝紫主题。

**设计令牌（Design Tokens）**

| Token | 值 | 用途 |
|-------|-----|------|
| `--background` | `#0b0d0c` | 近黑墨绿底色 |
| `--panel` | `#111411` | 卡片 / 面板底 |
| `--ink` | `#f1f3e9` | 暖白正文 |
| `--muted` | `#8b938a` | 次要文字（鼠尾草灰） |
| `--accent` | `#d6ff64` | **招牌青柠**——主色、强调、正数据 |
| `--danger` | `#ff6b5f` | 警示 / 过度负荷 |
| `--warn` | `#ffc857` | 提示 / 爬坡 |
| `--cool` | `#72e8ff` | 恢复 / 低温 |

**版式规则**：顶栏 brand-mark + privacy-pill「仅本地 · 数据来自高驰」；Hero 超大数字展示核心指标；4 列描边指标网格；青柠渐变分析卡；圆形编号教练建议列表；Chart.js 折线 / 柱用 `--accent`，对比序列用 `--cool/--warn/--danger`。

---

## 七、天气与热适应

**数据源**：Open-Meteo 历史归档接口（**免 key**），按训练地点坐标 + 日期 + 时段取数。

```
https://archive-api.open-meteo.com/v1/archive
  ?latitude=30.2741&longitude=120.1551   # 杭州（或活动 name 所含城市坐标）
  &start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
  &hourly=temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation,weather_code
  &timezone=Asia/Shanghai
```

取训练开始时刻所在小时及其前后 1 小时作代表。归档接口对「当天早些时候」可能有数小时延迟，取不到时降级 forecast 接口并在报告注明「天气为估算 / 邻近日」。

**热适应关键纪律**：
- 湿度 ≥95% 时鞋袜湿透是物理必然，**绝不可据此判体能 / 跑姿变差**；看心率与配速效率。
- 风速是蒸发救星：大风日即便高湿也不闷，HR 偏低是「风假象凉快」，非纯适应。
- 同配速 HR 随热季下降、或同 HR 配速变快 = 热适应正向信号。

---

## 八、报告内容一览

报告包含（节选自 `generate_report.py`）：
- **总览卡片**：月度总距离 / 次数 / 时长 / 卡路里
- **饼 / 环图**：训练类型分布、跑步 vs 力量占比
- **柱图**：每日训练负荷、每日跑步距离、周跑量
- **折线**：HRV 趋势、RHR + 疲劳率双轴
- **横向柱**：单跑距离、力量训练时长
- **雷达图**：月度综合评分
- **热适应模块**：WBGT / 体感 / 跨日对照表 / 适应信号
- **负荷与就绪度**：ACWR + 就绪度 0-100 + 分档建议

---

## 九、隐私与数据

- 包内**不含任何真实账号、密码或训练数据**——凭据仅通过环境变量注入，脚本零存储。
- 所有数据仅用于本地分析，报告内联呈现，**不上传第三方**。
- 高驰数据来自非官方开放接口，仅供个人训练分析使用。

---

## 十、踩坑经验（精选）

这些是从真实使用里总结的血泪教训，已固化进 `SKILL.md`，此处摘要点：

1. **全马训练禁止短跑极速冲刺**：50m/100m 极速冲刺对马拉松零价值，且极易拉伤梨状肌 / 腘绳肌。想试速度请用 10-15s strides @80-90% 最大速度。
2. **配速必须用 `avgSpeed`（运动配速）**，不可用 `totalTime/距离`（含休息，慢 10-30%）。
3. **单位陷阱**：`frequencyList.timestamp` 是厘秒（÷100=秒）、`distance` 是厘米（÷100=米）；`strideHeight` 是 mm（÷10=cm）；逐公里圈距离字段需 ÷100000 得 km。
4. **分段查询必须合并数据**：多段 JSON 必须 `activities = d1["activities"] + d2["activities"]`，所有统计在合并后的完整数据集上计算，禁止写死到模板。
5. **多源数据混用要谨慎**：COROS 与 Apple Watch 的 HRV/RHR 基线不同，严禁画在同一条线；需双序列 + 显眼数据源说明。
6. **HTML 数组拼接陷阱**：字符串列表必须用 `json.dumps(...)` 生成 JS 数组，禁止在外层 f-string 内再写嵌套 f-string 字面量（会导致所有图表阵亡）。
7. **双重质量门禁**：JS 语法检查 + 图表数据完整性自检（日期 key 格式、同日多活动合并、数组非空非全 0）→ 缺一不可，FAIL 禁止交付。

---

## 十一、参考与致谢

- **报告视觉**：Ride Relief 风格，改编自 [op7418/guizang-sports-skill](https://github.com/op7418/guizang-sports-skill)
- **负荷模型**：借鉴 R4F (Run4Fun) 看板 SDD 的 EvoLab+ 思路，落地为高驰官方 `ati/cti` 字段的 ACWR / Form 计算
- **热适应理论**：WBGT（美军 / ACSM 分级）、Stull 湿球、Steadman 澳式体感
- **天气数据**：[Open-Meteo](https://open-meteo.com/)（免 key 历史归档接口）
- **图表**：[Chart.js](https://www.chartjs.org/) v4（内联离线）

---

## 十二、License

本项目以 **MIT License** 开源，可自由使用、修改与分发。高驰数据接口为非官方来源，请仅用于个人训练分析，并遵守高驰的服务条款。

---

> 提示：本仓库主要作为「技能包」沉淀。若你用 WorkBuddy 等 Agent，可直接把整个目录作为 Skill 加载，`SKILL.md` 已包含完整的 API 参考、铁律与踩坑经验。
