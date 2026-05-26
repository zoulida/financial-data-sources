"""
Wind 全A估值 Web 展示
通过 Wind Excel 插件获取 PE 数据，并在网页中展示统计与图表。
"""

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from flask import Flask, jsonify, render_template_string, request


CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from md.winds.通过excel插件.wind_client import fetch_wind_formula, is_wind_available
from 测试Wind估值 import _build_wind_valuation_formula, _parse_wind_excel_valuation


app = Flask(__name__)

HTML = """
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Wind 全A估值监控</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    :root {
      color-scheme: light;
      --bg: #f4f7fb;
      --card: #ffffff;
      --text: #1f2937;
      --muted: #64748b;
      --blue: #2563eb;
      --red: #dc2626;
      --green: #16a34a;
      --amber: #d97706;
      --border: #e5e7eb;
      --shadow: 0 18px 45px rgba(15, 23, 42, 0.08);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Microsoft YaHei", "Segoe UI", Arial, sans-serif;
      background: radial-gradient(circle at top left, #dbeafe 0, transparent 34%), var(--bg);
      color: var(--text);
    }
    .page { max-width: 1180px; margin: 0 auto; padding: 28px 18px 46px; }
    .hero {
      display: flex;
      justify-content: space-between;
      gap: 18px;
      align-items: center;
      margin-bottom: 20px;
    }
    .title { font-size: 30px; font-weight: 800; margin: 0 0 8px; letter-spacing: -0.03em; }
    .subtitle { color: var(--muted); margin: 0; line-height: 1.7; }
    .toolbar {
      display: flex;
      gap: 10px;
      align-items: center;
      background: rgba(255,255,255,0.82);
      border: 1px solid var(--border);
      padding: 12px;
      border-radius: 16px;
      box-shadow: var(--shadow);
      flex-wrap: wrap;
    }
    .toolbar label { color: var(--muted); font-size: 13px; }
    .toolbar input {
      width: 84px;
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 9px 10px;
      font-size: 14px;
      outline: none;
    }
    button {
      border: 0;
      border-radius: 12px;
      padding: 10px 16px;
      background: linear-gradient(135deg, #2563eb, #1d4ed8);
      color: #fff;
      font-weight: 700;
      cursor: pointer;
      box-shadow: 0 10px 18px rgba(37, 99, 235, 0.25);
    }
    button:disabled { opacity: 0.55; cursor: wait; }
    .status {
      margin: 14px 0 18px;
      padding: 12px 14px;
      border-radius: 14px;
      background: #eff6ff;
      color: #1e40af;
      border: 1px solid #bfdbfe;
    }
    .status.error { background: #fef2f2; color: #991b1b; border-color: #fecaca; }
    .grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; margin-bottom: 16px; }
    .card {
      background: rgba(255,255,255,0.92);
      border: 1px solid var(--border);
      border-radius: 18px;
      padding: 18px;
      box-shadow: var(--shadow);
    }
    .metric-label { color: var(--muted); font-size: 13px; margin-bottom: 8px; }
    .metric-value { font-size: 26px; font-weight: 800; }
    .metric-sub { margin-top: 8px; color: var(--muted); font-size: 13px; }
    .score-pill {
      display: inline-flex;
      padding: 7px 11px;
      border-radius: 999px;
      font-weight: 800;
      font-size: 13px;
      margin-top: 10px;
    }
    .score-low { background: #dcfce7; color: #166534; }
    .score-mid { background: #fef3c7; color: #92400e; }
    .score-high { background: #fee2e2; color: #991b1b; }
    .chart-card { padding: 20px; }
    .chart-wrap { height: 460px; }
    .table-wrap { overflow: auto; max-height: 340px; }
    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    th, td { border-bottom: 1px solid var(--border); padding: 9px 10px; text-align: right; }
    th:first-child, td:first-child { text-align: left; }
    th { color: var(--muted); font-weight: 700; background: #f8fafc; position: sticky; top: 0; }
    @media (max-width: 900px) {
      .hero { flex-direction: column; align-items: stretch; }
      .grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    }
    @media (max-width: 560px) { .grid { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <div class="page">
    <section class="hero">
      <div>
        <h1 class="title">Wind 全A指数 PE 估值监控</h1>
        <p class="subtitle">通过 Wind Excel 插件获取 881001.WI 的 PE 序列，展示近 5 年估值百分位和逃顶评分。</p>
      </div>
      <div class="toolbar">
        <label>回看年数</label>
        <input id="years" type="number" min="1" max="10" value="5">
        <label>最大行数</label>
        <input id="rows" type="number" min="100" max="3000" value="1500">
        <button id="loadBtn" onclick="loadData()">获取数据并绘图</button>
      </div>
    </section>

    <div id="status" class="status">请点击“获取数据并绘图”。首次取数会启动 Excel COM，请确保 Wind 终端已登录且 Excel 插件可用。</div>

    <section class="grid">
      <div class="card"><div class="metric-label">当前 PE</div><div id="currentPe" class="metric-value">--</div><div id="currentDate" class="metric-sub">--</div></div>
      <div class="card"><div class="metric-label">历史百分位</div><div id="percentile" class="metric-value">--</div><div id="level" class="score-pill score-low">--</div></div>
      <div class="card"><div class="metric-label">逃顶估值得分</div><div id="score" class="metric-value">--</div><div class="metric-sub">规则：60%-95% 线性映射</div></div>
      <div class="card"><div class="metric-label">样本统计</div><div id="count" class="metric-value">--</div><div id="range" class="metric-sub">--</div></div>
    </section>

    <section class="card chart-card">
      <div class="chart-wrap"><canvas id="peChart"></canvas></div>
    </section>

    <section class="card" style="margin-top: 16px;">
      <h3 style="margin-top:0;">最近 20 个交易日</h3>
      <div class="table-wrap"><table><thead><tr><th>日期</th><th>PE</th></tr></thead><tbody id="recentRows"></tbody></table></div>
    </section>
  </div>

  <script>
    let chart = null;

    function fmt(num, digits = 2) {
      if (num === null || num === undefined || Number.isNaN(Number(num))) return '--';
      return Number(num).toFixed(digits);
    }

    function setStatus(text, isError = false) {
      const el = document.getElementById('status');
      el.textContent = text;
      el.className = isError ? 'status error' : 'status';
    }

    function levelClass(level) {
      if (level === '极高估值') return 'score-pill score-high';
      if (level === '中等估值') return 'score-pill score-mid';
      return 'score-pill score-low';
    }

    async function loadData() {
      const btn = document.getElementById('loadBtn');
      const years = document.getElementById('years').value || 5;
      const rows = document.getElementById('rows').value || 1500;
      btn.disabled = true;
      setStatus('正在通过 Wind Excel 插件获取数据，请稍候...');

      try {
        const resp = await fetch(`/api/valuation?years=${encodeURIComponent(years)}&rows=${encodeURIComponent(rows)}`);
        const data = await resp.json();
        if (!resp.ok || !data.ok) throw new Error(data.error || '获取失败');

        document.getElementById('currentPe').textContent = fmt(data.summary.current_pe);
        document.getElementById('currentDate').textContent = `最新日期：${data.summary.current_date}`;
        document.getElementById('percentile').textContent = `${fmt(data.summary.percentile, 1)}%`;
        document.getElementById('score').textContent = fmt(data.summary.score, 2);
        document.getElementById('count').textContent = `${data.summary.count} 条`;
        document.getElementById('range').textContent = `${data.summary.start_date} 至 ${data.summary.current_date}`;
        const level = document.getElementById('level');
        level.textContent = data.summary.level;
        level.className = levelClass(data.summary.level);

        renderChart(data.series, data.summary);
        renderRecent(data.series.slice(-20));
        setStatus(`数据获取成功：${data.summary.current_date} PE=${fmt(data.summary.current_pe)}，百分位=${fmt(data.summary.percentile, 1)}%。`);
      } catch (err) {
        setStatus(`获取失败：${err.message}`, true);
      } finally {
        btn.disabled = false;
      }
    }

    function renderChart(series, summary) {
      const labels = series.map(x => x.date);
      const peValues = series.map(x => x.pe);
      const meanLine = series.map(() => summary.mean_pe);
      const p95Line = series.map(() => summary.p95_pe);

      const ctx = document.getElementById('peChart');
      if (chart) chart.destroy();
      chart = new Chart(ctx, {
        type: 'line',
        data: {
          labels,
          datasets: [
            { label: 'Wind全A PE', data: peValues, borderColor: '#2563eb', backgroundColor: 'rgba(37,99,235,0.10)', borderWidth: 2, pointRadius: 0, tension: 0.18, fill: true },
            { label: '平均 PE', data: meanLine, borderColor: '#16a34a', borderWidth: 1.5, borderDash: [6, 5], pointRadius: 0 },
            { label: '95%分位 PE', data: p95Line, borderColor: '#dc2626', borderWidth: 1.5, borderDash: [6, 5], pointRadius: 0 }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          interaction: { mode: 'index', intersect: false },
          plugins: {
            legend: { position: 'top' },
            title: { display: true, text: 'Wind 全A指数 PE 时间序列与估值阈值' },
            tooltip: { callbacks: { label: ctx => `${ctx.dataset.label}: ${fmt(ctx.parsed.y)}` } }
          },
          scales: {
            x: { ticks: { maxTicksLimit: 12 }, grid: { display: false } },
            y: { title: { display: true, text: 'PE' }, beginAtZero: false }
          }
        }
      });
    }

    function renderRecent(rows) {
      const tbody = document.getElementById('recentRows');
      tbody.innerHTML = rows.reverse().map(row => `<tr><td>${row.date}</td><td>${fmt(row.pe, 4)}</td></tr>`).join('');
    }
  </script>
</body>
</html>
"""


def _calc_score(percentile):
    """按当前逃顶估值规则计算得分与级别。"""
    if percentile >= 95:
        return 1.0, "极高估值"
    if percentile <= 60:
        return 0.0, "合理估值"
    return (percentile - 60) / (95 - 60), "中等估值"


def fetch_valuation_data(years=5, rows=1500):
    """获取 Wind 全A PE 数据并计算 Web 展示所需结果。"""
    if not is_wind_available():
        raise RuntimeError("Wind Excel 插件不可用，或当前环境缺少 win32com/pythoncom")

    years = max(1, min(int(years), 10))
    rows = max(100, min(int(rows), 3000))
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=365 * years + 30)).strftime("%Y-%m-%d")
    code = "881001.WI"
    field = "pe"

    formula = _build_wind_valuation_formula(code, field, start_date, end_date, rows)
    raw_df = fetch_wind_formula(formula, timeout=120, interval=0.5, visible=False)
    df = _parse_wind_excel_valuation(raw_df, field, start_date)

    if len(df) < 100:
        raise RuntimeError(f"有效估值数据不足，当前仅 {len(df)} 条")

    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df[field] = pd.to_numeric(df[field], errors="coerce")
    df = df.dropna(subset=[field]).sort_values("date").reset_index(drop=True)

    current_pe = float(df.iloc[-1][field])
    percentile = float((df[field] < current_pe).sum() / len(df) * 100)
    score, level = _calc_score(percentile)

    series = [
        {"date": row["date"].strftime("%Y-%m-%d"), "pe": round(float(row[field]), 4)}
        for _, row in df.iterrows()
    ]
    summary = {
        "code": code,
        "field": field,
        "start_date": df.iloc[0]["date"].strftime("%Y-%m-%d"),
        "current_date": df.iloc[-1]["date"].strftime("%Y-%m-%d"),
        "count": int(len(df)),
        "current_pe": current_pe,
        "min_pe": float(df[field].min()),
        "max_pe": float(df[field].max()),
        "mean_pe": float(df[field].mean()),
        "p95_pe": float(df[field].quantile(0.95)),
        "percentile": percentile,
        "score": float(score),
        "level": level,
    }
    return {"summary": summary, "series": series}


@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/api/valuation")
def api_valuation():
    try:
        years = request.args.get("years", 5, type=int)
        rows = request.args.get("rows", 1500, type=int)
        result = fetch_valuation_data(years=years, rows=rows)
        return jsonify({"ok": True, **result})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


def main():
    parser = argparse.ArgumentParser(description="Wind 全A估值 Web 展示")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=7793)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    app.run(host=args.host, port=args.port, debug=args.debug, use_reloader=False)


if __name__ == "__main__":
    main()
