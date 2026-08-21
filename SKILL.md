---
name: coros-panorama-training-analysis
description: "基于高驰数据的全景训练分析。拉取 COROS 活动/逐公里明细/每日恢复/负荷平衡(ATI/CTI/ACWR)，融合 Open-Meteo 天气，输出 Ride Relief 风格 HTML 报告。能力：逐公里技术指标(步频/步幅/垂直振幅/功率)、心率6区训练比例、热适应评价(WBGT/体感温度)、负荷平衡与每日就绪度评分、身体成分与能量估算。触发词：跑步分析、训练报告、周报月报、热适应、LSD分析、负荷分析、就绪度。"
agent_created: true
---

# 基于高驰数据的全景训练分析（COROS Panorama Training Analysis）

拉取高驰（COROS）数据，融合天气与身体状态，产出多维度训练分析 HTML 报告。

## 能力全景（五大分析引擎）

| 引擎 | 模块 | 核心产出 |
|------|------|----------|
| 逐公里技术分解 | `activity/detail/query` 明细 | 每公里配速/心率/步频/步幅/垂直振幅/功率 |
| 心率 6 区比例 | `frequencyList` 逐秒统计 | 恢复/有氧耐力/有氧动力/乳酸阈/速度耐力/无氧动力 占比 |
| 热适应评价 | `references/heat_metrics.py` | 露点/湿球/澳式体感/酷热指数/估算WBGT + 跨日适应信号 |
| 负荷平衡与就绪度 | `references/load_balance.py` | ACWR/Form/每日就绪度 0-100 + 分档建议 |
| 身体成分与能量 | `references/body_composition.py` | LBM/BMR/TDEE/跑步消耗/宏量目标 |
| 天气（报告必含） | Open-Meteo 历史归档 | 训练当日 温度/湿度/风/降水 + WMO 天气代码 |
| 报告呈现 | `references/ride_relief_style.css` | Ride Relief 暗黑风格 + Chart.js 内联 + 双重质量门禁 |

## When to Use

- User wants to analyze COROS (高驰) training data
- Generating monthly/weekly training reports from COROS
- Visualizing running distance, strength training, HRV, RHR, sleep, training load
- Any request involving COROS data retrieval + chart-based visualization

## 核心铁律：COROS 数据读取必须准确

用户是严肃跑者，对配速、HR、距离数据极其敏感。**任何数据读取错误都是零容忍的。** 以下错误不可再犯：

1. **禁止猜测 API 参数名**——请求前必须确认正确的字段名（`labelId` 非 `activityId`，`dataList` 非 `activityList`，`pageNumber` 非 `page`）
2. **禁止猜测请求格式**——detail query 用 form data（`data=`），非 JSON（`json=`）
3. **禁止猜测数据单位**——`frequencyList` 的 `timestamp` 是厘秒（÷100=秒），`distance` 是厘米（÷100=米），使用前必须转换
4. **禁止自行检测分段边界**——用户明确告知训练结构时（如"30s×8"），必须用固定窗口提取，不用启发式算法
5. **输出前自检**——总里程、总时长、平均配速必须在合并后的完整数据集上计算，禁止写死到模板
6. **报告必含训练当日天气**——每次训练/周/月报必须附上**训练当日的真实天气**（温度、湿度、风、降水），按训练地点+日期+时段从 Open-Meteo 历史接口取数。天气是耐热/心率漂移/配速判读的关键变量，缺天气的跑评等于少了一半上下文。详见下方「天气数据」章节。

## Prerequisites

无需安装任何 MCP 服务器——所有数据通过 `scripts/fetch_data.py`（纯 Python：httpx + hashlib）直接调用 COROS 开放接口。

### 配置（一次）

```bash
export COROS_EMAIL=you@example.com
export COROS_PASSWORD=your_password
python3 scripts/fetch_data.py 20260801 20260818   # 开始日 结束日
```

- 依赖：Python >= 3.11 + `httpx`（`pip install httpx`）。
- Region：`asia`（中国区 teamcnapi.coros.com，默认）、`eu`、`us`（脚本顶部 COROS_REGION 修改）。
- 输出 `coros_20260801_20260818.json`（含 metrics/analyse/activities）。

> 个性化参数（LT 心率、体重/体脂、常驻城市坐标）请在分析时替换为使用者自己的值：
> 示例值：LT=178bpm/277W、体重 71kg/体脂 20%、杭州 30.2741,120.1551。

## Managed Python / 运行环境说明

- 纯 Python 实现（httpx + hashlib），无原生 `.so` 依赖，托管 Python 与系统 Python 均可运行。
- 天气取数用 Open-Meteo（免 key），历史归档接口对「当天早些时候」可能有数小时延迟；取不到当日时降级 forecast 接口并注明。

## COROS API Reference

### Base URL by Region

| Region | Training Hub URL | Mobile API URL |
|--------|-----------------|----------------|
| asia/cn | `https://teamcnapi.coros.com` | `https://apicn.coros.com` |
| eu | `https://teameuapi.coros.com` | `https://apieu.coros.com` |
| us | `https://teamapi.coros.com` | `https://api.coros.com` |

### Endpoint Quick Reference

| Purpose | Endpoint | Method | Key Parameters |
|---------|----------|--------|---------------|
| Login | `/account/login` | POST | `account`, `accountType: 2`, `pwd` (MD5 hex) |
| Daily Metrics | `/analyse/dayDetail/query` | **GET** | `startDay`, `endDay` (YYYYMMDD) |
| VO2max/Fitness | `/analyse/query` | POST | `{}` (empty body) |
| Dashboard/HRV | `/dashboard/query` | POST | `{}` (empty body) |
| Activity List | `/activity/query` | **GET** | `startDay`, `endDay`, `pageNumber`, `size` |
| Activity Detail | `/activity/detail/query` | POST | **form-data**: `labelId`, `userId`, `sportType` |

### Critical API Details

1. **Login**: Password must be MD5 hashed (`hashlib.md5(pwd.encode()).hexdigest()`)
2. **Daily Metrics**: GET request with query params, NOT POST with JSON body
3. **Activity List**: GET request, parameter is `pageNumber` NOT `page`
4. **Activity `startTime`**: Unix timestamp (int), convert with `datetime.fromtimestamp(ts, tz=...)`
5. **Daily Metrics `distance` field**: Always 0 — aggregate from activities instead
6. **Activity Detail 正确 payload（8/12 修正）**：必须用 **form-data（`data=`）而非 JSON body**，字段为 `labelId`（即 activity/query 返回的 `labelId`，不是 activityId）、`userId`（login 返回的 `data.userId`）、`sportType`（字符串 "100"）。请求头需带 `yfheader: json.dumps({"userId": uid})`。用 `{activityId:...}` JSON 方式必返回 `1001 Service exceptions`。
7. **Detail summary/items 距离单位是厘米（cm）**：`summary.distance`、`lapItemList[].distance` 均需 ÷100000 得 km；`frequencyList[].timestamp` 单位是厘秒（÷100 得秒）。
8. **每公里技术指标提取**：从 `detail.lapList` 取第一个 `lapItemList` 长度 ≥ `floor(总km)` 的 lap（通常 type=2），取恰好 `floor(总km)` 条。每条含 `avgMoveSpeed`(s/km)、`avgHr`、`avgCadence`、`avgStrideLength`(cm)、`strideHeight`(mm)、`avgPower`(W)、`elevGain`(m)。summary 层 `maxHr`/`maxPower`/`bestKm` 可用，但 `avgStrideLength`/`strideHeight` 为 None，需从 per-km 平均。

### Authentication

All authenticated requests need header: `accessToken: <token>`.

Token comes from login response: `body["data"]["accessToken"]`.

### Sport Types

| Type | Category |
|------|----------|
| 100 | Running (跑步) |
| 102 | Trail Running |
| 103 | Track Running (运动场跑步) — 必须归入跑步类 |
| 402 | Strength Training (力量训练) |
| 904 | Yoga (瑜伽) |
| 9901, 10001, 900 | Other |

## Workflow

### Step 1: Fetch Data

```bash
COROS_EMAIL=you@example.com COROS_PASSWORD=your_password \
  python3 scripts/fetch_data.py 20260801 20260818
```

This outputs `coros_20260801_20260818.json`（含 metrics / analyse(ati,cti) / activities）。

### Step 2: Generate Report

Use `scripts/generate_report.py`. It reads the JSON, processes data, and outputs
an interactive HTML file with:

- **Overview cards**: Monthly totals (distance, count, duration, calories)
- **Pie/Donut charts**: Training type distribution, run vs strength ratio
- **Bar charts**: Daily training load, daily running distance, weekly run volume
- **Line charts**: HRV trend, RHR + fatigue rate dual-axis
- **Horizontal bar**: Individual run distances, strength session durations
- **Radar chart**: Composite monthly score

### Step 3: Preview

Open the HTML file directly — it uses Chart.js CDN (no local dependencies).

## Data Processing Notes

### Daily Running Distance

The COROS `analyse/dayDetail/query` endpoint returns `distance: 0` for all days.
Compute daily distance by aggregating from the activity list:

### ⚠️ 配速计算规则（重要）

COROS 活动对象中包含两个关键的时间字段：
- `totalTime` — 总时间（秒），包含红灯、补给、休息等所有停顿
- `workoutTime` — 运动时间（秒），排除停顿
- `avgSpeed` — 运动配速（秒/km），等于 `workoutTime / distance * 1000`

**配速必须使用 `avgSpeed` 字段**（单位：秒/km），不可用 `totalTime / distance` 计算。因为：
- `totalTime/距离` 算出的配速包含休息时间，比实际运动配速慢 10-30%
- 例如周三间歇：totalTime=4296s→6:12/km，avgSpeed=324→**5:24/km**，高驰后台显示 5:24
- 周六LSD：totalTime=9270s→7:43/km，avgSpeed=356.9→**5:56/km**

转换方法：
```python
def format_pace(secs_per_km):
    m = int(secs_per_km // 60)
    s = int(secs_per_km % 60)
    return f"{m}:{s:02d}"
```

```python
daily_run_dist = {}
for a in runs:
    ts = a['startTime']  # Unix timestamp
    d_str = datetime.fromtimestamp(ts, tz=timezone(timedelta(hours=8))).strftime('%Y%m%d')
    dist = (a['distance'] or 0) / 1000
    daily_run_dist[d_str] = daily_run_dist.get(d_str, 0) + dist
```

### Date Handling

- `startTime` in activities: Unix timestamp (int), use `datetime.fromtimestamp()`
- `happenDay` in daily metrics: `YYYYMMDD` format (int), convert with `str()`
- Always use Asia/Shanghai timezone (+8) for correct date boundaries

### 报告视觉风格：Ride Relief 设计系统（默认）

用户明确喜欢 [op7418/guizang-sports-skill](https://github.com/op7418/guizang-sports-skill) 的 **Ride Relief / Route Relief** 报告风格。
**所有新生成的 COROS 报告必须采用这套设计语言**（取代旧的深蓝紫主题）。

完整、可直接内联的 CSS 见 `references/ride_relief_style.css`（复制到 HTML `<style>` 即可）。

**设计令牌（Design Tokens）**
| Token | 值 | 用途 |
|-------|-----|------|
| `--background` | `#0b0d0c` | 近黑墨绿底色 |
| `--panel` | `#111411` | 卡片/面板底 |
| `--ink` | `#f1f3e9` | 暖白正文 |
| `--muted` | `#8b938a` | 次要文字（鼠尾草灰） |
| `--line` | `rgba(235,240,225,.13)` | 描边/分割线 |
| `--accent` | `#d6ff64` | **招牌青柠**——主色、强调、正数据 |
| `--danger` | `#ff6b5f` | 警示/过度负荷 |
| `--warn` | `#ffc857` | 提示/爬坡 |
| `--cool` | `#72e8ff` | 恢复/低温 |

**版式与组件规则（必须遵循）**
1. **顶栏 topbar**：左侧圆形 brand-mark（青柠描边 + 图标）+ 品牌名 + eyebrow；右侧 privacy-pill「仅本地 · 数据来自高驰」。
2. **Hero metric**：超大数字（`font-size:56px`，`letter-spacing:-.065em`，`tabular-nums`），展示本次核心指标（距离或配速）。
3. **Metric grid**：4 列带描边网格，每格 `span`(标签) + `strong`(数值) + `small`(单位/注释)，关键值用 `.accent-val` 上青柠色。
4. **Section**：编号小标 `.section-number`(青柠) + `.section-icon` + 标题；分块清晰。
5. **Analysis card**：青柠渐变描边卡片（`.analysis-card`），用于单点结论/有氧质量评估。
6. **Recommendation list**：圆形编号徽章 `.recommendation-number` + 标题 + 说明，教练建议逐条列出。
7. **Deep analysis**：`.deep-analysis-card` 青柠渐变卡，放 2–6 个深潜洞见。
8. **图表**：Chart.js 内联；折线/柱用 `--accent`(#d6ff64)，对比序列用 `--cool`/`--warn`/`--danger`；网格线 `#2a2a45`→改用 `rgba(235,240,225,.08)`，文字 `--muted`。

**Chart.js 全局默认（写入报告脚本）**
```python
CHART_COLORS = {
  "accent": "#d6ff64", "cool": "#72e8ff", "warn": "#ffc857",
  "danger": "#ff6b5f", "muted": "#8b938a", "ink": "#f1f3e9",
  "grid": "rgba(235,240,225,0.08)", "bg": "#0b0d0c",
}
```

**旧配色（已弃用，仅作对照）**：深蓝紫 `#0f0f1a` 底 + 绿 `#7cff6b`/橙 `#ff9f43`/红 `#ff6b6b`/蓝 `#54a0ff`。
生成新报告时一律使用上面的 Ride Relief 调色板，不要混用旧色。

## 天气数据（报告必含模块）

每次训练分析、周报、月报都必须在报告里呈现**训练当日的真实天气**。用途：耐热评估、心率漂移归因、配速判读基准（气温 33°C+ 时配速回退 10–25s 属正常，不应判为退步）。

### 数据源：Open-Meteo 历史归档接口（免 key）

```
https://archive-api.open-meteo.com/v1/archive
  ?latitude=30.2741&longitude=120.1551   # 杭州（用户常驻地；若活动 name 含其他城市则按该城市坐标）
  &start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
  &hourly=temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation,weather_code
  &timezone=Asia/Shanghai
```

- 返回逐小时数据；取**训练开始时刻所在小时**及其前后 1 小时作代表（如 17:45 跑 → 取 17:00/18:00）。
- 字段：`temperature_2m`(°C)、`relative_humidity_2m`(%)、`wind_speed_10m`(km/h)、`precipitation`(mm)、`weather_code`(WMO 天气代码)。
- 调用方式：`httpx` GET，纯 Python 无原生依赖，走 WorkBuddy 托管 Python 即可。
- 归档接口对「当天早些时候」可能有数小时延迟；若取不到当日，降级用 forecast 接口或就近日，并在报告注明「天气为估算/邻近日」。

### 天气代码 → 中文描述（WMO，部分常用）

| code | 含义 |
|------|------|
| 0 | 晴 |
| 1-3 | 大致晴朗 / 局部多云 / 阴 |
| 45,48 | 雾 |
| 51-57 | 毛毛雨 |
| 61-67 | 雨 |
| 71-77 | 雪 |
| 80-82 | 阵雨 |
| 95-99 | 雷暴 |

### 报告呈现方式（Ride Relief 风格）

在 hero 副标题或独立 `.analysis-card` 中展示一行天气徽章：
`🌡 28°C · 💧 65% · 💨 3km/h · 🌧 小雨`，并纳入有氧质量评估文字（如「闷热潮湿 → 同配速心率偏高，正常」）。

## 热适应评价机制（heat_metrics.py）

用户要求建设**热适应评价**：气温 + 湿度 + 叠加体感温度，并据此评价耐热训练效果。
可复用模块：`references/heat_metrics.py`（纯 Python，无原生依赖，直接 `import`）。

### 理论依据（参考科普《体感温度都是怎么算出来的？》微信 mp.weixin.qq.com/s/WqEdhH4GMZ_D4dpFDnKskg）
- 室温远低于体温：散热靠热传导，湿度影响小。
- 室温接近/高于体温：散热几乎全靠排汗蒸发，湿度越高体感越热；且汗难蒸发 → 衣服湿透是物理必然，**非退步信号**。
- 对高温运动人群，应认准 **WBGT（湿球黑球温度）**= 0.7·湿球 + 0.2·黑球 + 0.1·干球，而非普通 App 体感温度。

### 模块提供的量（全部用 Open-Meteo 实测 T/RH/风 计算）
1. `dew_point(T,RH)` 露点（Magnus）；RH=100% 时露点≈气温。
2. `wet_bulb_stull(T,RH)` 湿球温度（Stull 2011，±0.3°C）。
3. `apparent_temp_au(T,RH,wind)` **澳式体感温度** AT（Steadman 1994，T+RH+风）。
4. `heat_index(T,RH)` **酷热指数** HI（Rothfusz/NOAA）。
5. `est_wbgt(T,RH)` = 0.7·Twb + 0.3·T —— **无日照/遮阴近似 WBGT**（清晨低日照跑步适用，是热应激保守基线）。
6. `heat_category(wbgt)` → (等级, 颜色键, 训练建议)，阈值：<18 低 / <23 注意 / <28 中度(强度降5–10%) / <33 高度(降10–20%) / ≥33 极高(取消高强度)。
7. `evaluate_run(...)` 单跑评价；`acclimation_table(runs)` 跨日对比，输出每跑「效率=配速÷%LT」与「热折损」，并自动生成适应信号（同配速 HR 变化）。

### 报告呈现（Ride Relief 风格，参考 coros_aug12_heat.html）
- `weather-badge` 已含体感温度。
- 新增 `.heat-metrics` 6 格卡：干球/湿度/风速/澳式体感/酷热指数/估算WBGT（WBGT 卡用 `--warn` 高亮）。
- `.data-table` 跨日对照表：日期/km/T/RH/风/WBGT/体感/配速/HR/%LT/效率/热折损；高亮当前跑。
- 适应信号文字 + 建议卡（"湿透≠退步"、"同配速 HR 下降=适应"、"风是蒸发救星"、"WBGT≥28 强度降 10–20%"）。
- 图表：WBGT 柱 + 平均心率 线双轴。

### 关键解读纪律
- **湿度≥95% 时鞋袜湿透是物理必然**，绝不可据此判体能/跑姿变差；看心率与配速效率。
- 风速是蒸发救星：大风日（如台风 29km/h）即便高湿也不闷，HR 偏低是"风假象凉快"，非纯适应。
- 同配速 HR 随热季下降、或同 HR 配速变快 = 热适应正向信号（血浆容量↑、排汗效率↑）。

## 负荷平衡与就绪度（load_balance.py）

借鉴 R4F SDD 的 EvoLab+ 模型，基于高驰官方字段计算（`/analyse/query` 的 `t7dayList`）：

| 量 | 公式 | 高驰字段 |
|---|---|---|
| ACWR 负荷比 | ATI / CTI | `ati`(7天EWMA) / `cti`(42天EWMA) |
| Form 体能储备 | CTI - ATI | `performance` 辅助 |
| HRV 偏移 | (hrv-hrv_base)/hrv_base | `avgSleepHrv` / `sleepHrvBase` |
| 就绪度 0-100 | 睡眠30%+HRV25%+RHR15%+ACWR15%+疲劳15% | 缺失维度自动归一化 |

ACWR 分档：<0.8 减量过度 / 0.8-1.3 平衡 / 1.3-1.5 快速上升 / >1.5 过高（Tim Gabbett 急性:慢性负荷比）。

用法：`from load_balance import acwr, classify_acwr, form, readiness, readiness_label`。
- 报告"恢复背景"章节应包含 ACWR + 就绪度 + 分档建议（高 ACWR 且就绪度低 = 强制减量）。
- 就绪度 ≥80 可上强度 / 65-79 正常 / 50-64 保守 / <50 降档休息。

## 身体成分与能量（body_composition.py）

借鉴 R4F SDD §4.3，基于体重/体脂计算：
- LBM = 体重×(1-体脂%)；BMR = 370+21.6×LBM（Katch-McArdle，有体脂时优先）；
- 跑步消耗 ≈ 1.0 kcal/kg/km（可用高驰 calorie 校验：8/13 12.34K=869kcal≈70kcal/km）；
- 宏量目标：耐力备赛 蛋白2.0/碳水5.0/脂肪1.0 g/kg（碳水占比应≥55%）。
- 用户当前：71kg/20% → LBM 56.8kg、BMR≈1597 kcal、TDEE(中活动)≈2475 kcal、跑步 22.5K≈1600 kcal。
- 报告适用：减脂/增肌监控、LSD 补给策略（消耗大时碳水补足）、周跑量能量缺口估算。

## Sleep Data

Sleep stage data (deep/light/REM) requires the mobile API which needs AES encryption
(pycryptodome). If unavailable, use `avgSleepHrv` and `rhr` from daily metrics as
sleep quality proxies. Inform the user that full sleep stage data requires running
`coros-mcp auth-web` in a local terminal.

## Report Customization

### ⚠️ Chart.js 加载策略（重要）

HTML 报告默认**内联 Chart.js**（~205KB），不使用 CDN。原因：
- 本地 `file://` 协议打开时，CDN 可能被浏览器安全策略阻止
- 分享给他人时，对方网络可能无法访问 CDN
- 内联后完全离线可用，100% 渲染成功

生成流程：
1. Python 生成时读取 Chart.js 文件内容
2. 直接写入 HTML 的 `<script>` 标签
3. 无需任何外部依赖

To modify the report:
1. Edit `scripts/generate_report.py`
2. Modify the data processing section (weeks, metrics, aggregations)
3. Add/remove chart sections in the HTML template
4. Re-run to regenerate

Chart.js v4 is used via CDN — supports bar, line, pie, doughnut, radar, and more.

### ✅ HTML 出厂质量门禁（双重检查，缺一不可）

**第一重：JS 语法检查**——生成后用 Node 解析所有内联 `<script>`：
```bash
node /dev/stdin <<'EOF'
const fs=require("fs");
const h=fs.readFileSync("out.html","utf8");
const re=/<script>([\s\S]*?)<\/script>/g; let m,i=0,bad=0;
while((m=re.exec(h))){ i++; try{ new Function(m[1]); }catch(e){ bad++; console.log("SCRIPT "+i+" ERROR:",e.message);} }
console.log("scripts:",i,"errors:",bad);
EOF
```

**第二重：图表数据完整性自检**（8/18 用户反馈"缺失图文"后新增）——生成脚本末尾必须断言：
1. **日期 key 格式**：`20260801 → "08/01"`（`f"{day//100%100:02d}/{day%100:02d}"`，月/日不可颠倒；写反会导致跑量图全 0，只有 8/8 对称日碰巧匹配）；
2. **同日多活动必须合并**（如 8/1 三次跑 → 一条），否则堆叠图 x 轴出现重复标签；
3. **每个图表数据数组**：非空、非全 0、标签数与数据数一致（`ast.literal_eval` 解析后断言，sum>0 且 len 匹配）；
4. 自检 FAIL 时禁止交付，先修再出。

**教训（8/18）**：`f"{d['day']%100:02d}/{d['day']//100%100:02d}"` 生成 `"01/08"`（反了），导致 volChart 跑量柱全部为 0——JS 语法检查通过但图是空的。语法对 ≠ 数据对，必须双层门禁。

## 踩坑经验

- **全马训练禁止短跑极速冲刺（7/19发现）**：用户（全马备赛期）容易在好奇或冲动下尝试 50m/100m 极速冲刺。**这类冲刺对马拉松没有任何训练价值，且极易拉伤梨状肌/腘绳肌等深层肌群**（50m/7s = 远超训练覆盖的速度域，零热身状态下的极限爆发力输出必然导致肌纤维撕裂）。当用户提到"想试试速度""测一下50米""跑个百米"等意图时，必须主动提醒风险并建议替代方案：10-15秒 strides @80-90% 最大速度。本次梨状肌拉伤（7/18）就是 50m 极速冲刺的后果。
- **多跑日配速核对（6/7发现）**：当同一天有多次跑步时，必须逐一核对每次的 `avgSpeed`，禁止因为"同一天"就复制上一次的配速值。例如 6/6 早上 16.7K (366s/km=6:06) 和下午 10.2K (341s/km=5:41)，两者配速完全不同。每次跑步都需要独立计算 `int(avgSpeed)//60:{int(avgSpeed)%60:02d}`。
- **日期边界（6/7发现）**：查询周报时必须确认当天是周几，起始日期必须是本周一。API 参数 `startDay` 一旦写错一天（如 6/2 而不是 6/1），就会漏掉周一的数据。
- **多设备数据源混用（6/14发现）**：用户可能手动提供 Apple Watch AutoSleep 睡眠数据来补全 COROS 缺失的睡眠。严禁将 AW 和 COROS 的 HRV/RHR 直接画在同一条线上（基线不同：COROS HRV ~40ms，AW ~60+ms）。正确做法：(a) 使用两套独立数据序列，COROS 用实线、AW 用虚线；(b) AW 数据点使用白色边框突出标识；(c) 报告顶部加显眼的「数据源说明」黄色警告框；(d) 文字分析中不跨设备比较数值，分开描述趋势。
- **分段查询必须合并数据（6/14发现）**：当周报数据分两段查询时（如周一到周四用一个 JSON，周末用另一个 JSON），报告脚本**必须同时加载并合并两个 JSON 文件**的 `activities` 和 `metrics`。否则只会渲染后加载的文件数据，导致总里程、训练次数、负荷等全部严重偏低。正确做法：`activities = data1["activities"] + data2["activities"]`，metrics 用 `happenDay` 去重后合并。所有统计数字（total_dist、len(runs)、total_tl）必须在合并后的数据上计算，严禁写死到 HTML 模板。
- **GPS频率数据单位（6/25发现）**：`activity/detail/query` 返回的 `frequencyList` 中：`timestamp` 单位为**厘秒（centiseconds，÷100得秒）**，`distance` 单位为**厘米（centimeters，÷100得米）**。计算配速时务必先转换单位。
- **间歇/短冲分段——严禁自作主张检测边界（6/25发现）**：当用户明确告知训练结构（如"30秒快跑+1分钟休息×8"、"5组800米"），**必须使用固定时间/距离窗口提取数据，禁止使用启发式算法（如pace阈值、功率突变等）自行检测分段边界**。启发式检测会把一段完整30秒切成多个碎片（如19s+12s），导致数据失真。正确做法：从 `frequencyList` 第一个有效GPS点开始，按用户描述的时间结构（如90秒一个block：30s快+60s休），提取固定窗口内的全程数据。
- **周报数据完整性——严禁漏掉任何一天（7/5发现）**：连续多次漏掉用户已经告知的训练记录（6/30 10K渐加速、7/4 12K热适应）。**根本原因是：每次查询只关注"最新一天"的数据，没有回溯到本周一构建完整时间线**。正确做法：(a) 收到用户训练汇报时，必须先列出"本周一到今天"每一天的训练记录，逐天确认；(b) 不能只在最后分析时才查时间线，每收到一次训练信息就更新一次完整周时间线；(c) 用户说过的训练数据（即使不在当前查询日期范围内）必须纳入本周统计，禁止因为"之前说过了"就忽略；(d) 每周复盘时，从周一到周日逐日检查，确保没有空档。总跑量、总负荷必须在合并后的完整7天数据上计算。
- **每公里技术指标提取（7/29发现）**：用户要"每公里 心率/步频/步幅/垂直振幅"时，从 `activity/detail/query` 的 `lapList` 里取 **`type=10`** 的分段（COROS 每公里自动圈，10.2K 会返回 10×1km + 1×0.20km 收尾）。每个 `lapItemList` 项的字段：`avgHr`(心率)、`avgCadence`(步频spm)、`avgStrideLength`(**cm**)、`strideHeight`(**mm，÷10=cm**才是垂直振幅)、`avgPace`(s/km)、`maxHr/minHr`。**单位陷阱**：`strideHeight` 是 mm 不是 cm（86→8.6cm 才合理，垂直比≈10%属高效）；`avgStrideLength` 直接是 cm。提取后用这些值对照 `summary` 的 avgHr/avgCadence/avgStepLen 做一致性自检。
- **HTML 生成数组陷阱（7/29发现）**：在 Python f-string 里拼 JS 数组时，字符串列表（如公里标签 `['1.00','2.00']`）若写成 `const L=['{labels}']` 会被双重包裹成 `const L=['['1.00',...]']` 导致 JS 语法错误。正确做法：数值列表用 `const hr={hr}`（Python 整型列表 repr 恰好是合法 JS 数组），**字符串列表必须用 `const L={json.dumps(labels)}`**（生成带双引号的合法 JS 数组）。
- **跑步分析默认纳入技术指标（7/29用户明确要求）**：用户要求做"跑步训练分析/月报/复盘"时，**除配速、心率、距离、负荷外，必须一并分析技术指标**——步频(cadence)、步幅(avgStepLen)、垂直振幅(strideHeight÷10)、垂直比、触地时间等跑姿经济性指标，并结合气温做热适应评估。每公里或每次跑都要给这些指标，并在教练评估里解读其稳定性/趋势。垂直振幅的稳定度（跨强度、跨温度、跨距离）是评估跑姿经济性与抗疲劳能力的核心信号。
- **Per-km 跨 lap 类型去重（7/30发现）**：`activity/detail/query` 的 `lapList` 中，不同 lap type（2、10、11、12）可能各自包含一组重叠的 1km 自动圈（type=2 有 12 个 1km 分段，type=11 也有 12 个），导致全局收集时 per-km 条目翻倍（12km 跑出 23 条）。**正确做法**：找到第一个 lapItemList 中有 `floor(dist_km)` 个符合 1km 距离（90k–110k cm）的 lap，取恰好 `floor(dist_km)` 条。不可贪多全取。
- **嵌套 f-string 漏解析坑（7/31发现）**：在 Python 三引号 f-string 模板 `html=f"""..."""` 里直接写 `f"D1 {days[0]['date']}"` 这种**嵌套 f-string 字面量**时，外层 f-string 的 `{...}` 表达式插槽会先把内层字面量当成普通字符串原样塞进 HTML，最终页面里出现字面量 `f"D1 07/28"`——直接破坏 JS 语法，导致所有 Chart.js 一齐阵亡（症状：标题/表格渲染、画布全空）。**正确做法**：所有 JS 字符串数组先在 f-string 外用 `json.dumps(...)` 算好（如 `bar_lbls = json.dumps([f"D{i+1} {d['date']}" for i,d in enumerate(days))]`），再以 `{bar_lbls}` 占位符塞进 HTML。**禁止在外层 f-string 内部再写 f-string 字面量**。
- **多源数据合并——按 date 去重而非硬补（7/31发现）**：当月报/汇总数据来自多个分批获取的 JSON（如 `july_tech.json` + `heat_3day.json`），**必须先按 date 字段合并去重，再生成报告**，禁止在生成脚本里"硬补"特定日期。错误做法：`for d in heat3 if d["date"]=="07/30": runs.append(...)` —— 一旦数据源已合并就会重复；并且如果遗漏某个日期，append 代码不会触发（导致 7/29 漏行）。**正确做法**：(1) 在数据准备阶段一次性合并去重到主 JSON；(2) 生成脚本只读一个干净主数据源，不要再硬补单日。**自检**：`grep -oE "MM/DD" report.html | sort | uniq -c` 检查每个日期出现次数是否一致，遗漏/重复立即浮现。
