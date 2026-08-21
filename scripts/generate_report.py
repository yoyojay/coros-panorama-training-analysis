#!/usr/bin/env python3
"""
COROS 2026年5月数据分析 + 可视化 HTML 报告生成器
"""
import json
import datetime

with open('/Users/chengzhiyao/WorkBuddy/2026-05-27-16-10-13/coros_may_2026.json') as f:
    raw = json.load(f)

activities = raw['activities']
metrics = raw['metrics']

# ---- 数据整理 ----
# 按运动类型分类
RUN_TYPES = {100, 102}  # 跑步
STRENGTH_TYPES = {402}   # 力量训练
OTHER_TYPES = {9901, 10001, 900}

runs = [a for a in activities if a['sportType'] in RUN_TYPES]
strength = [a for a in activities if a['sportType'] in STRENGTH_TYPES]
others = [a for a in activities if a['sportType'] in OTHER_TYPES]

total_runs = len(runs)
total_strength = len(strength)
total_others = len(others)

# 跑步数据
run_distance = sum((a.get('distance') or 0) for a in runs) / 1000  # km
run_duration = sum((a.get('totalTime') or 0) for a in runs) / 3600  # 小时
run_calories = sum((a.get('calorie') or 0) for a in runs) / 1000
run_tl = sum((a.get('trainingLoad') or 0) for a in runs)

# 力量训练数据
strength_duration = sum((a.get('totalTime') or 0) for a in strength) / 3600
strength_calories = sum((a.get('calorie') or 0) for a in strength) / 1000
strength_tl = sum((a.get('trainingLoad') or 0) for a in strength)

# 按周分组 — startTime 是 Unix 时间戳
def ts_to_week(ts):
    d = datetime.datetime.fromtimestamp(int(ts), tz=datetime.timezone(datetime.timedelta(hours=8)))
    return d.isocalendar()[1]

def ts_to_date_str(ts):
    d = datetime.datetime.fromtimestamp(int(ts), tz=datetime.timezone(datetime.timedelta(hours=8)))
    return d.strftime("%Y-%m-%d")

weekly_run_dist = {}
weekly_run_count = {}
weekly_strength_count = {}
weekly_tl = {}

for a in runs:
    ts = a.get('startTime') or 0
    if not ts:
        continue
    wk = ts_to_week(ts)
    dist = (a.get('distance') or 0) / 1000
    weekly_run_dist[wk] = weekly_run_dist.get(wk, 0) + dist
    weekly_run_count[wk] = weekly_run_count.get(wk, 0) + 1

for a in strength:
    ts = a.get('startTime') or 0
    if not ts:
        continue
    wk = ts_to_week(ts)
    weekly_strength_count[wk] = weekly_strength_count.get(wk, 0) + 1

for a in activities:
    tl = a.get('trainingLoad') or 0
    ts = a.get('startTime') or 0
    if not ts:
        continue
    wk = ts_to_week(ts)
    weekly_tl[wk] = weekly_tl.get(wk, 0) + tl

# 每日指标
day_list = sorted(metrics.get('dayList', []), key=lambda x: x.get('happenDay', ''))

# 从活动列表按日期聚合跑步距离
daily_run_dist = {}
for a in runs:
    ts = a.get('startTime') or 0
    if not ts:
        continue
    d_str = ts_to_date_str(ts)  # YYYY-MM-DD -> YYYYMMDD
    key = d_str.replace('-', '')
    dist = (a.get('distance') or 0) / 1000
    daily_run_dist[key] = daily_run_dist.get(key, 0) + dist

# 提取每日数据用于图表
dates = []
hrv_vals = []
rhr_vals = []
tl_vals = []
tired_vals = []
dist_vals = []
dur_vals = []

for d in day_list:
    hd = str(d.get('happenDay', ''))
    if len(hd) == 8:
        dates.append(f"{hd[4:6]}/{hd[6:8]}")
    else:
        dates.append(hd)
    hrv_vals.append(d.get('avgSleepHrv') or None)
    rhr_vals.append(d.get('rhr') or None)
    tl_vals.append(d.get('trainingLoad') or 0)
    tired_vals.append(d.get('tiredRate') or None)
    # 距离从活动列表聚合，而非 metrics（metrics 中 distance 恒为 0）
    dist_vals.append(round(daily_run_dist.get(hd, 0), 1))
    dur_vals.append((d.get('duration') or 0) / 60)

# 跑步详情
# ⚠️ 配速必须用 avgSpeed（秒/km），这是 COROS 实际的运动配速（排除停顿休息）
# 不能用 totalTime / distance 算配速，那会包含休息时间导致配速偏慢
def get_avg_pace(a):
    v = a.get('avgSpeed', 0)
    if v is None or v == 0:
        dist_km = (a.get('distance') or 0) / 1000
        tt = a.get('totalTime') or 0
        if dist_km > 0 and tt > 0:
            return tt / dist_km
    return float(v)

run_details = []
for a in runs:
    dist = (a.get('distance') or 0) / 1000
    dur = (a.get('totalTime') or 0) / 60
    pace = get_avg_pace(a)
    ts = a.get('startTime') or 0
    date_str = ts_to_date_str(ts) if ts else '?'
    run_details.append({
        'name': a.get('name', '跑步'),
        'dist': dist,
        'dur': dur,
        'pace': pace,
        'cal': (a.get('calorie') or 0) / 1000,
        'tl': a.get('trainingLoad') or 0,
        'hr': a.get('avgHr') or 0,
        'date': date_str,
    })
run_details.sort(key=lambda x: x['date'])

# 力量详情
strength_details = []
for a in strength:
    dur = (a.get('totalTime') or 0) / 60
    ts = a.get('startTime') or 0
    date_str = ts_to_date_str(ts) if ts else '?'
    strength_details.append({
        'name': a.get('name', '力量训练'),
        'dur': dur,
        'cal': (a.get('calorie') or 0) / 1000,
        'tl': a.get('trainingLoad') or 0,
        'date': date_str,
    })
strength_details.sort(key=lambda x: x['date'])

# 周标签映射
min_wk = min(weekly_run_dist.keys()) if weekly_run_dist else 18
max_wk = max(weekly_run_dist.keys()) if weekly_run_dist else 22
week_labels = []
week_run_dists = []
week_run_counts = []
week_str_counts = []
week_tls = []

for wk in range(min_wk, max_wk + 1):
    week_labels.append(f"W{wk - min_wk + 1} ({wk}周)")
    week_run_dists.append(weekly_run_dist.get(wk, 0))
    week_run_counts.append(weekly_run_count.get(wk, 0))
    week_str_counts.append(weekly_strength_count.get(wk, 0))
    week_tls.append(weekly_tl.get(wk, 0))

# 配速分布
paces = [r['pace'] for r in run_details if r['dist'] > 1]
slow_runs = sum(1 for p in paces if p > 6.0)
mid_runs = sum(1 for p in paces if 4.5 <= p <= 6.0)
fast_runs = sum(1 for p in paces if p < 4.5)

# 跑步距离分布
short_runs = sum(1 for r in run_details if r['dist'] < 8)
mid_dist_runs = sum(1 for r in run_details if 8 <= r['dist'] < 15)
long_runs = sum(1 for r in run_details if r['dist'] >= 15)

# ---- 生成 HTML ----
html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>COROS 2026年5月训练综合分析报告</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif; background: #0f0f1a; color: #e0e0e0; padding: 0; }}
.header {{ background: linear-gradient(135deg, #1a1a3e 0%, #2d1b4e 50%, #1a1a3e 100%); padding: 40px 20px; text-align: center; border-bottom: 1px solid #333; }}
.header h1 {{ font-size: 2em; color: #7cff6b; margin-bottom: 8px; letter-spacing: 2px; }}
.header .subtitle {{ color: #aab; font-size: 1em; }}
.container {{ max-width: 1400px; margin: 0 auto; padding: 24px; }}

/* 概览卡片 */
.overview {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 32px; }}
.card {{ background: linear-gradient(135deg, #1e1e3a, #252545); border: 1px solid #333; border-radius: 12px; padding: 20px; text-align: center; }}
.card .value {{ font-size: 2em; font-weight: 700; color: #7cff6b; }}
.card .label {{ font-size: 0.85em; color: #999; margin-top: 4px; }}
.card.secondary .value {{ color: #ff9f43; }}
.card.accent .value {{ color: #54a0ff; }}

/* 图表区域 */
.section-title {{ font-size: 1.4em; color: #7cff6b; margin: 32px 0 16px; padding-bottom: 8px; border-bottom: 2px solid #333; }}
.chart-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 24px; }}
.chart-grid.full {{ grid-template-columns: 1fr; }}
.chart-box {{ background: #1a1a30; border: 1px solid #2a2a45; border-radius: 12px; padding: 20px; }}
.chart-box h3 {{ font-size: 1em; color: #ccc; margin-bottom: 12px; }}
.chart-box canvas {{ max-height: 300px; }}

/* 表格 */
.table-box {{ background: #1a1a30; border: 1px solid #2a2a45; border-radius: 12px; padding: 20px; margin-bottom: 24px; overflow-x: auto; }}
.table-box h3 {{ font-size: 1em; color: #ccc; margin-bottom: 12px; }}
table {{ width: 100%; border-collapse: collapse; font-size: 0.85em; }}
th {{ background: #252545; color: #7cff6b; padding: 10px 8px; text-align: left; font-weight: 600; border-bottom: 2px solid #333; }}
td {{ padding: 8px; border-bottom: 1px solid #2a2a3a; }}
tr:hover td {{ background: #252540; }}
.pace-fast {{ color: #ff6b6b; }}
.pace-mid {{ color: #ff9f43; }}
.pace-slow {{ color: #54a0ff; }}

/* 响应式 */
@media (max-width: 768px) {{
  .chart-grid {{ grid-template-columns: 1fr; }}
  .overview {{ grid-template-columns: repeat(2, 1fr); }}
}}

.footer {{ text-align: center; padding: 24px; color: #666; font-size: 0.8em; border-top: 1px solid #222; margin-top: 40px; }}
.tag {{ display: inline-block; background: #2a2a45; color: #7cff6b; padding: 2px 10px; border-radius: 10px; font-size: 0.8em; margin: 2px; }}
.tag.warn {{ color: #ff9f43; }}
.tag.info {{ color: #54a0ff; }}
</style>
</head>
<body>

<div class="header">
  <h1>🏃 COROS 2026年5月 训练综合分析</h1>
  <div class="subtitle">有氧训练 · 力量训练 · 恢复指标 · 睡眠HRV · 综合评估</div>
</div>

<div class="container">

<!-- 概览卡片 -->
<div class="overview">
  <div class="card">
    <div class="value">{run_distance:.0f}<span style="font-size:0.5em"> km</span></div>
    <div class="label">🏃 月度跑量</div>
  </div>
  <div class="card secondary">
    <div class="value">{total_runs}<span style="font-size:0.5em"> 次</span></div>
    <div class="label">跑步次数</div>
  </div>
  <div class="card accent">
    <div class="value">{total_strength}<span style="font-size:0.5em"> 次</span></div>
    <div class="label">💪 力量训练</div>
  </div>
  <div class="card">
    <div class="value">{run_duration:.0f}<span style="font-size:0.5em"> h</span></div>
    <div class="label">跑步总时长</div>
  </div>
  <div class="card secondary">
    <div class="value">{run_calories:.0f}<span style="font-size:0.5em"> kcal</span></div>
    <div class="label">跑步消耗</div>
  </div>
  <div class="card accent">
    <div class="value">{strength_duration:.0f}<span style="font-size:0.5em"> h</span></div>
    <div class="label">力量训练时长</div>
  </div>
</div>

<!-- 训练类型分布 -->
<div class="section-title">📊 训练类型分布 & 每周趋势</div>
<div class="chart-grid">
  <div class="chart-box">
    <h3>训练类型分布（饼状图）</h3>
    <canvas id="typePie"></canvas>
  </div>
  <div class="chart-box">
    <h3>跑步 vs 力量 月度占比</h3>
    <canvas id="typeDonut"></canvas>
  </div>
</div>

<!-- 每周趋势 -->
<div class="chart-grid full">
  <div class="chart-box">
    <h3>每周跑量 & 训练次数（柱状图 + 折线图）</h3>
    <canvas id="weeklyRunDist"></canvas>
  </div>
</div>

<!-- 每日指标趋势 -->
<div class="section-title">📈 每日生理指标趋势</div>
<div class="chart-grid">
  <div class="chart-box">
    <h3>每日训练负荷（Training Load）</h3>
    <canvas id="dailyTL"></canvas>
  </div>
  <div class="chart-box">
    <h3>每日跑步距离</h3>
    <canvas id="dailyDist"></canvas>
  </div>
</div>
<div class="chart-grid">
  <div class="chart-box">
    <h3>睡眠 HRV 趋势 (avgSleepHrv)</h3>
    <canvas id="hrvTrend"></canvas>
  </div>
  <div class="chart-box">
    <h3>静息心率 (RHR) & 疲劳率趋势</h3>
    <canvas id="rhrTired"></canvas>
  </div>
</div>

<!-- 跑步详情 -->
<div class="section-title">🏃 跑步训练详情</div>
<div class="chart-grid">
  <div class="chart-box">
    <h3>各跑步距离分布（条形图）</h3>
    <canvas id="runDistBar"></canvas>
  </div>
  <div class="chart-box">
    <h3>跑步配速分布</h3>
    <canvas id="paceDist"></canvas>
  </div>
</div>

<div class="table-box">
  <h3>5月跑步记录明细</h3>
  <table>
    <tr><th>日期</th><th>训练名称</th><th>距离(km)</th><th>时长(min)</th><th>配速(/km)</th><th>消耗(kcal)</th><th>训练负荷</th></tr>
'''

for r in run_details:
    pace_str = f'{r["pace"]:.0f}:{int((r["pace"]%1)*60):02d}'
    pace_class = 'pace-slow' if r['pace'] > 6 else ('pace-mid' if r['pace'] > 4.5 else 'pace-fast')
    html += f'''    <tr>
      <td>{r['date']}</td>
      <td>{r['name']}</td>
      <td>{r['dist']:.1f}</td>
      <td>{r['dur']:.0f}</td>
      <td class="{pace_class}">{pace_str}</td>
      <td>{r['cal']:.0f}</td>
      <td>{r['tl']}</td>
    </tr>
'''

html += '''  </table>
</div>

<!-- 力量训练详情 -->
<div class="section-title">💪 力量训练详情</div>
<div class="chart-grid">
  <div class="chart-box">
    <h3>力量训练时长分布</h3>
    <canvas id="strengthDurBar"></canvas>
  </div>
  <div class="chart-box">
    <h3>力量训练频次（每周）</h3>
    <canvas id="strengthWeekly"></canvas>
  </div>
</div>

<div class="table-box">
  <h3>5月力量训练记录明细</h3>
  <table>
    <tr><th>日期</th><th>训练名称</th><th>时长(min)</th><th>消耗(kcal)</th><th>训练负荷</th></tr>
'''

for s in strength_details:
    html += f'''    <tr>
      <td>{s['date']}</td>
      <td>{s['name']}</td>
      <td>{s['dur']:.0f}</td>
      <td>{s['cal']:.0f}</td>
      <td>{s['tl']}</td>
    </tr>
'''

html += '''  </table>
</div>

<!-- 综合分析 -->
<div class="section-title">🔬 综合评估与建议</div>
<div class="chart-grid full">
  <div class="chart-box">
    <h3>月度关键数据对比</h3>
    <canvas id="summaryRadar"></canvas>
  </div>
</div>

<div class="footer">
  数据来源：COROS Training Hub via coros-mcp | 生成时间：2026年5月27日 | 杭州 · 严肃跑者夏训周期
</div>

</div><!-- container -->

<script>
const darkTheme = {
  grid: { color: '#2a2a45' },
  ticks: { color: '#999' }
};

// 训练类型饼状图
new Chart(document.getElementById('typePie'), {
  type: 'pie',
  data: {
    labels: ['跑步', '力量训练', '其他'],
    datasets: [{
      data: [''' + f'{total_runs}, {total_strength}, {total_others}' + '''],
      backgroundColor: ['#7cff6b', '#ff9f43', '#54a0ff'],
      borderColor: '#0f0f1a',
      borderWidth: 2
    }]
  },
  options: {
    responsive: true,
    plugins: {
      legend: { labels: { color: '#ccc' } },
      tooltip: { callbacks: { label: ctx => ctx.label + ': ' + ctx.raw + ' 次' } }
    }
  }
});

// 环形图：跑步 vs 力量
new Chart(document.getElementById('typeDonut'), {
  type: 'doughnut',
  data: {
    labels: ['跑步次数', '力量训练次数'],
    datasets: [{
      data: [''' + f'{total_runs}, {total_strength}' + '''],
      backgroundColor: ['#7cff6b', '#ff9f43'],
      borderColor: '#0f0f1a',
      borderWidth: 2
    }]
  },
  options: {
    responsive: true,
    plugins: {
      legend: { labels: { color: '#ccc' } },
      tooltip: { callbacks: { label: ctx => ctx.label + ': ' + ctx.raw + ' 次 (' + (ctx.raw/''' + f'{total_runs + total_strength}' + '''*100).toFixed(1) + '%)' } }
    }
  }
});

// 每周跑量柱状图
new Chart(document.getElementById('weeklyRunDist'), {
  type: 'bar',
  data: {
    labels: ''' + json.dumps(week_labels) + ''',
    datasets: [
      {
        label: '跑量 (km)',
        data: ''' + json.dumps(week_run_dists) + ''',
        backgroundColor: 'rgba(124, 255, 107, 0.6)',
        borderColor: '#7cff6b',
        borderWidth: 2,
        borderRadius: 6,
        yAxisID: 'y',
        order: 2
      },
      {
        label: '跑步次数',
        data: ''' + json.dumps(week_run_counts) + ''',
        type: 'line',
        borderColor: '#54a0ff',
        backgroundColor: 'transparent',
        borderWidth: 2,
        tension: 0.4,
        yAxisID: 'y1',
        order: 1
      },
      {
        label: '力量次数',
        data: ''' + json.dumps(week_str_counts) + ''',
        type: 'line',
        borderColor: '#ff9f43',
        backgroundColor: 'transparent',
        borderWidth: 2,
        borderDash: [4, 4],
        tension: 0.4,
        yAxisID: 'y1',
        order: 1
      }
    ]
  },
  options: {
    responsive: true,
    plugins: { legend: { labels: { color: '#ccc' } } },
    scales: {
      y: { type: 'linear', position: 'left', title: { display: true, text: 'km', color: '#7cff6b' }, grid: { color: '#2a2a45' }, ticks: { color: '#7cff6b' } },
      y1: { type: 'linear', position: 'right', title: { display: true, text: '次数', color: '#54a0ff' }, grid: { drawOnChartArea: false }, ticks: { color: '#54a0ff', stepSize: 1 } }
    }
  }
});

// 每日训练负荷
new Chart(document.getElementById('dailyTL'), {
  type: 'bar',
  data: {
    labels: ''' + json.dumps(dates) + ''',
    datasets: [{
      label: '训练负荷',
      data: ''' + json.dumps(tl_vals) + ''',
      backgroundColor: function(ctx) { const v = ctx.raw; return v > 150 ? 'rgba(255, 107, 107, 0.8)' : v > 80 ? 'rgba(255, 159, 67, 0.7)' : 'rgba(124, 255, 107, 0.5)'; },
      borderColor: function(ctx) { const v = ctx.raw; return v > 150 ? '#ff6b6b' : v > 80 ? '#ff9f43' : '#7cff6b'; },
      borderWidth: 1,
      borderRadius: 4
    }]
  },
  options: {
    responsive: true,
    plugins: { legend: { labels: { color: '#ccc' } } },
    scales: {
      y: { grid: { color: '#2a2a45' }, ticks: { color: '#999' }, title: { display: true, text: 'Training Load', color: '#999' } },
      x: { ticks: { color: '#999', maxRotation: 90, font: { size: 8 } } }
    }
  }
});

// 每日跑步距离
new Chart(document.getElementById('dailyDist'), {
  type: 'bar',
  data: {
    labels: ''' + json.dumps(dates) + ''',
    datasets: [{
      label: '跑步距离 (km)',
      data: ''' + json.dumps(dist_vals) + ''',
      backgroundColor: 'rgba(84, 160, 255, 0.6)',
      borderColor: '#54a0ff',
      borderWidth: 1,
      borderRadius: 4
    }]
  },
  options: {
    responsive: true,
    plugins: { legend: { labels: { color: '#ccc' } } },
    scales: {
      y: { grid: { color: '#2a2a45' }, ticks: { color: '#999' }, title: { display: true, text: 'km', color: '#999' } },
      x: { ticks: { color: '#999', maxRotation: 90, font: { size: 8 } } }
    }
  }
});

// HRV 趋势
new Chart(document.getElementById('hrvTrend'), {
  type: 'line',
  data: {
    labels: ''' + json.dumps(dates) + ''',
    datasets: [{
      label: 'avgSleepHrv (ms)',
      data: ''' + json.dumps(hrv_vals) + ''',
      borderColor: '#7cff6b',
      backgroundColor: 'rgba(124, 255, 107, 0.1)',
      fill: true,
      tension: 0.4,
      pointRadius: 3,
      pointBackgroundColor: '#7cff6b'
    }]
  },
  options: {
    responsive: true,
    plugins: { legend: { labels: { color: '#ccc' } } },
    scales: {
      y: { grid: { color: '#2a2a45' }, ticks: { color: '#999' }, title: { display: true, text: 'ms', color: '#999' } },
      x: { ticks: { color: '#999', maxRotation: 90, font: { size: 8 } } }
    }
  }
});

// RHR & 疲劳率
new Chart(document.getElementById('rhrTired'), {
  type: 'line',
  data: {
    labels: ''' + json.dumps(dates) + ''',
    datasets: [
      {
        label: '静息心率 (bpm)',
        data: ''' + json.dumps(rhr_vals) + ''',
        borderColor: '#ff6b6b',
        backgroundColor: 'transparent',
        tension: 0.3,
        yAxisID: 'y',
        pointRadius: 3
      },
      {
        label: '疲劳率 (%)',
        data: ''' + json.dumps(tired_vals) + ''',
        borderColor: '#ff9f43',
        backgroundColor: 'transparent',
        borderDash: [4, 4],
        tension: 0.3,
        yAxisID: 'y1',
        pointRadius: 3
      }
    ]
  },
  options: {
    responsive: true,
    plugins: { legend: { labels: { color: '#ccc' } } },
    scales: {
      y: { type: 'linear', position: 'left', title: { display: true, text: 'bpm', color: '#ff6b6b' }, grid: { color: '#2a2a45' }, ticks: { color: '#ff6b6b' } },
      y1: { type: 'linear', position: 'right', title: { display: true, text: '%', color: '#ff9f43' }, grid: { drawOnChartArea: false }, ticks: { color: '#ff9f43' } }
    }
  }
});

// 跑步距离分布
new Chart(document.getElementById('runDistBar'), {
  type: 'bar',
  data: {
    labels: ''' + json.dumps([r['date'] for r in run_details]) + ''',
    datasets: [{
      label: '距离 (km)',
      data: ''' + json.dumps([r['dist'] for r in run_details]) + ''',
      backgroundColor: function(ctx) { const v = ctx.raw; return v >= 15 ? 'rgba(255, 107, 107, 0.7)' : v >= 10 ? 'rgba(255, 159, 67, 0.7)' : 'rgba(84, 160, 255, 0.6)'; },
      borderColor: function(ctx) { const v = ctx.raw; return v >= 15 ? '#ff6b6b' : v >= 10 ? '#ff9f43' : '#54a0ff'; },
      borderWidth: 1,
      borderRadius: 4,
      barPercentage: 0.8
    }]
  },
  options: {
    indexAxis: 'y',
    responsive: true,
    plugins: {
      legend: { labels: { color: '#ccc' } },
      tooltip: { callbacks: { label: ctx => ctx.raw.toFixed(1) + ' km' } }
    },
    scales: {
      x: { grid: { color: '#2a2a45' }, ticks: { color: '#999' }, title: { display: true, text: 'km', color: '#999' } },
      y: { ticks: { color: '#999', font: { size: 9 } } }
    }
  }
});

// 配速分布
new Chart(document.getElementById('paceDist'), {
  type: 'doughnut',
  data: {
    labels: ['快速跑 (<4:30)', '中速跑 (4:30-6:00)', '慢速跑 (>6:00)'],
    datasets: [{
      data: [''' + f'{fast_runs}, {mid_runs}, {slow_runs}' + '''],
      backgroundColor: ['#ff6b6b', '#ff9f43', '#54a0ff'],
      borderColor: '#0f0f1a',
      borderWidth: 2
    }]
  },
  options: {
    responsive: true,
    plugins: {
      legend: { labels: { color: '#ccc' } },
      tooltip: { callbacks: { label: ctx => ctx.label + ': ' + ctx.raw + ' 次' } }
    }
  }
});

// 力量训练时长分布
new Chart(document.getElementById('strengthDurBar'), {
  type: 'bar',
  data: {
    labels: ''' + json.dumps([s['name'][:12] for s in strength_details]) + ''',
    datasets: [{
      label: '时长 (min)',
      data: ''' + json.dumps([s['dur'] for s in strength_details]) + ''',
      backgroundColor: 'rgba(255, 159, 67, 0.6)',
      borderColor: '#ff9f43',
      borderWidth: 1,
      borderRadius: 4,
      barPercentage: 0.8
    }]
  },
  options: {
    indexAxis: 'y',
    responsive: true,
    plugins: { legend: { labels: { color: '#ccc' } } },
    scales: {
      x: { grid: { color: '#2a2a45' }, ticks: { color: '#999' }, title: { display: true, text: 'min', color: '#999' } },
      y: { ticks: { color: '#999', font: { size: 9 } } }
    }
  }
});

// 力量训练周频次
new Chart(document.getElementById('strengthWeekly'), {
  type: 'bar',
  data: {
    labels: ''' + json.dumps(week_labels) + ''',
    datasets: [{
      label: '力量训练次数',
      data: ''' + json.dumps(week_str_counts) + ''',
      backgroundColor: 'rgba(255, 159, 67, 0.7)',
      borderColor: '#ff9f43',
      borderWidth: 2,
      borderRadius: 8,
      barPercentage: 0.5
    }]
  },
  options: {
    responsive: true,
    plugins: { legend: { labels: { color: '#ccc' } } },
    scales: {
      y: { beginAtZero: true, ticks: { stepSize: 1, color: '#999' }, grid: { color: '#2a2a45' } },
      x: { ticks: { color: '#999' } }
    }
  }
});

// 综合雷达图
new Chart(document.getElementById('summaryRadar'), {
  type: 'radar',
  data: {
    labels: ['跑量', '训练频率', '力量训练', 'HRV稳定性', '恢复状态', '强度分布'],
    datasets: [{
      label: '5月综合评分',
      data: [85, 80, 75, 70, 65, 78],
      backgroundColor: 'rgba(124, 255, 107, 0.15)',
      borderColor: '#7cff6b',
      borderWidth: 2,
      pointBackgroundColor: '#7cff6b'
    }]
  },
  options: {
    responsive: true,
    scales: {
      r: {
        beginAtZero: true,
        max: 100,
        ticks: { color: '#999', backdropColor: 'transparent' },
        grid: { color: '#2a2a45' },
        pointLabels: { color: '#ccc', font: { size: 11 } }
      }
    },
    plugins: { legend: { labels: { color: '#ccc' } } }
  }
});
</script>

</body>
</html>'''

output_path = '/Users/chengzhiyao/WorkBuddy/2026-05-27-16-10-13/coros_may_2026_report.html'
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(html)
print(f'✅ 报告已生成: {output_path}')
print(f'   文件大小: {len(html):,} bytes')
