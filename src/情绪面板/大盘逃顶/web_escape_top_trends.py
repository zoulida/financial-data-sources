"""
大盘逃顶指标走势 Web 展示
整合 Wind 估值、Wind 开户数据、Wind 融资余额和量价背离行情，用于观察多指标走势。
"""

import argparse
import hashlib
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from flask import Flask, jsonify, render_template_string, request


CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = Path(__file__).resolve().parents[3]
WIND_EXCEL_DIR = PROJECT_ROOT / "md" / "winds" / "通过excel插件"
OPENTDX_ROOT = PROJECT_ROOT / "md" / "通达信" / "opentdx-main"
QLIB_TOOLS_DIR = PROJECT_ROOT / "md" / "qlib数据"

for path in (PROJECT_ROOT, CURRENT_DIR, WIND_EXCEL_DIR, OPENTDX_ROOT, QLIB_TOOLS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from md.winds.通过excel插件.wind_client import fetch_wind_formula, is_wind_available
from qlib_config import DEFAULT_QLIB_PROVIDER_URI
from src.板块炒作阶段预测.opentdx_sector_loader import OpenTdxSectorConfig, build_opentdx_sector_universe, load_opentdx_sector_kline_panel
from 测试Wind估值 import _build_wind_valuation_formula, _parse_wind_excel_valuation
from 测试Wind开户数据 import DEFAULT_ACCOUNT_CODE, DEFAULT_ACCOUNT_NAME, _fetch_account_data
from 测试Wind融资余额 import _fetch_margin_total, _parse_single_series


app = Flask(__name__)
CACHE_DIR = CURRENT_DIR / "cache" / "daily_trends"
CACHE_SWITCH_HOUR = 15
CACHE_SWITCH_MINUTE = 10
QLIB_CHECK_HOUR = 18
BOND_YIELD_SOURCES = [
    ("S0059749", "中国国债到期收益率:10年"),
]

HTML = """
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>大盘逃顶指标走势</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    :root { --bg:#f4f7fb; --card:#fff; --text:#0f172a; --muted:#64748b; --border:#e5e7eb; --blue:#2563eb; --red:#dc2626; --green:#16a34a; --amber:#d97706; --purple:#7c3aed; --shadow:0 18px 45px rgba(15,23,42,.08); }
    * { box-sizing:border-box; }
    body { margin:0; font-family:"Microsoft YaHei","Segoe UI",Arial,sans-serif; background:radial-gradient(circle at top left,#dbeafe 0,transparent 34%),var(--bg); color:var(--text); }
    .page { max-width:1320px; margin:0 auto; padding:28px 18px 46px; }
    .hero { display:flex; justify-content:space-between; align-items:center; gap:18px; margin-bottom:18px; }
    h1 { margin:0 0 8px; font-size:30px; font-weight:900; }
    .subtitle { margin:0; color:var(--muted); line-height:1.7; }
    .toolbar { display:flex; align-items:center; gap:10px; flex-wrap:wrap; background:rgba(255,255,255,.9); border:1px solid var(--border); padding:12px; border-radius:16px; box-shadow:var(--shadow); }
    label { color:var(--muted); font-size:13px; }
    input, select { border:1px solid var(--border); border-radius:10px; padding:9px 10px; font-size:14px; outline:none; background:#fff; }
    input { width:88px; }
    button { border:0; border-radius:12px; padding:10px 16px; background:linear-gradient(135deg,#2563eb,#1d4ed8); color:#fff; font-weight:800; cursor:pointer; box-shadow:0 10px 18px rgba(37,99,235,.25); }
    button:disabled { opacity:.55; cursor:wait; }
    .status { margin:14px 0 18px; padding:12px 14px; border-radius:14px; background:#eff6ff; color:#1e40af; border:1px solid #bfdbfe; white-space:pre-wrap; }
    .status.error { background:#fef2f2; color:#991b1b; border-color:#fecaca; }
    .metrics { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:14px; margin-bottom:16px; }
    .card { background:rgba(255,255,255,.94); border:1px solid var(--border); border-radius:18px; padding:18px; box-shadow:var(--shadow); }
    .metric-label { color:var(--muted); font-size:13px; margin-bottom:8px; }
    .metric-value { font-size:24px; font-weight:900; }
    .metric-sub { margin-top:8px; color:var(--muted); font-size:13px; line-height:1.5; }
    .charts { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:16px; }
    .chart-title { margin:0 0 12px; font-size:18px; }
    .chart-wrap { height:360px; }
    .full { grid-column:1 / -1; }
    .table-wrap { overflow:auto; max-height:360px; }
    table { width:100%; border-collapse:collapse; font-size:13px; }
    th, td { border-bottom:1px solid var(--border); padding:9px 10px; text-align:right; }
    th:first-child, td:first-child { text-align:left; }
    th { color:var(--muted); background:#f8fafc; position:sticky; top:0; }
    @media (max-width:980px) { .hero { flex-direction:column; align-items:stretch; } .metrics,.charts { grid-template-columns:1fr; } .full { grid-column:auto; } }
  </style>
</head>
<body>
  <div class="page">
    <section class="hero">
      <div>
        <h1>大盘逃顶指标走势观察</h1>
        <p class="subtitle">整合 Wind 全A PE、开户数据、融资余额、上证指数量价数据和 Qlib 全市场大盘拥挤度。首次取数会调用 Excel COM，请确保 Wind 终端已登录且 Excel 插件可用。</p>
      </div>
      <div class="toolbar">
        <label>估值年数</label><input id="valuationYears" type="number" min="1" max="10" value="5">
        <label>开户月数</label><input id="accountMonths" type="number" min="3" max="60" value="12">
        <label>融资天数</label><input id="marginDays" type="number" min="20" max="500" value="120">
        <label>融资买入天数</label><input id="marginPurchaseDays" type="number" min="20" max="500" value="120">
        <label>行业拥挤天数</label><input id="industryCongestionDays" type="number" min="20" max="500" value="120">
        <label>恐贪天数</label><input id="marketStyleDays" type="number" min="20" max="500" value="120">
        <label>国债天数</label><input id="bondYieldDays" type="number" min="20" max="1500" value="500">
        <label>量价天数</label><input id="priceDays" type="number" min="20" max="500" value="120">
        <label>拥挤度年数</label><input id="crowdingYears" type="number" min="1" max="10" value="3">
        <label>量价源</label><select id="priceSource"><option value="opentdx">OpenTDX</option><option value="xtquant">XtQuant</option></select>
        <button id="loadBtn" onclick="loadData()">获取数据并绘图</button>
      </div>
    </section>

    <div id="status" class="status">请点击“获取数据并绘图”。</div>

    <section class="metrics">
      <div class="card"><div class="metric-label">Wind 全A PE</div><div id="peMetric" class="metric-value">--</div><div id="peSub" class="metric-sub">--</div></div>
      <div class="card"><div class="metric-label">最新开户数</div><div id="accountMetric" class="metric-value">--</div><div id="accountSub" class="metric-sub">--</div></div>
      <div class="card"><div class="metric-label">融资余额</div><div id="marginMetric" class="metric-value">--</div><div id="marginSub" class="metric-sub">--</div></div>
      <div class="card"><div class="metric-label">融资买入/成交额</div><div id="marginPurchaseMetric" class="metric-value">--</div><div id="marginPurchaseSub" class="metric-sub">--</div></div>
      <div class="card"><div class="metric-label">行业拥挤度最高</div><div id="industryCongestionMetric" class="metric-value">--</div><div id="industryCongestionSub" class="metric-sub">--</div></div>
      <div class="card"><div class="metric-label">恐慌&贪心</div><div id="marketStyleMetric" class="metric-value">--</div><div id="marketStyleSub" class="metric-sub">--</div></div>
      <div class="card"><div class="metric-label">10年期国债收益率</div><div id="bondYieldMetric" class="metric-value">--</div><div id="bondYieldSub" class="metric-sub">--</div></div>
      <div class="card"><div class="metric-label">量价背离</div><div id="divergenceMetric" class="metric-value">--</div><div id="divergenceSub" class="metric-sub">--</div></div>
      <div class="card"><div class="metric-label">交易拥挤度</div><div id="crowdingMetric" class="metric-value">--</div><div id="crowdingSub" class="metric-sub">--</div></div>
    </section>

    <section class="charts">
      <div class="card"><h3 class="chart-title">Wind 全A PE 走势</h3><div class="chart-wrap"><canvas id="valuationChart"></canvas></div></div>
      <div class="card"><h3 class="chart-title">新增开户数走势</h3><div class="chart-wrap"><canvas id="accountChart"></canvas></div></div>
      <div class="card"><h3 class="chart-title">融资余额与日变化</h3><div class="chart-wrap"><canvas id="marginChart"></canvas></div></div>
      <div class="card"><h3 class="chart-title">全部A股 融资买入/成交额 vs 上证指数</h3><div class="chart-wrap"><canvas id="marginPurchaseChart"></canvas></div></div>
      <div class="card full"><h3 class="chart-title">行业拥挤度 Top 行业走势</h3><div class="chart-wrap"><canvas id="industryCongestionChart"></canvas></div></div>
      <div class="card full"><h3 class="chart-title">最新行业拥挤度排行</h3><div class="table-wrap"><table><thead><tr><th>行业</th><th>板块类型</th><th>成分数</th><th>成交额占比</th><th>成交额(亿元)</th></tr></thead><tbody id="industryCongestionRows"></tbody></table></div></div>
      <div class="card full"><h3 class="chart-title">恐慌&贪心指标走势</h3><div class="chart-wrap"><canvas id="marketStyleChart"></canvas></div></div>
      <div class="card full"><h3 class="chart-title">中国10年期国债收益率</h3><div class="chart-wrap"><canvas id="bondYieldChart"></canvas></div></div>
      <div class="card"><h3 class="chart-title">上证指数收盘价与成交量</h3><div class="chart-wrap"><canvas id="priceChart"></canvas></div></div>
      <div class="card full"><h3 class="chart-title">交易拥挤度走势</h3><div class="chart-wrap"><canvas id="crowdingChart"></canvas></div></div>
      <div class="card full"><h3 class="chart-title">最近量价背离检测</h3><div class="table-wrap"><table><thead><tr><th>日期</th><th>收盘价</th><th>成交量(万手)</th><th>涨跌幅</th><th>量变</th><th>量价背离</th></tr></thead><tbody id="divergenceRows"></tbody></table></div></div>
    </section>
  </div>

<script>
  const charts = {};
  function fmt(num, digits=2) { if (num === null || num === undefined || Number.isNaN(Number(num))) return '--'; return Number(num).toFixed(digits); }
  function setStatus(text, isError=false) { const el = document.getElementById('status'); el.textContent = text; el.className = isError ? 'status error' : 'status'; }
  function destroyChart(id) { if (charts[id]) charts[id].destroy(); }
  async function loadData() {
    const btn = document.getElementById('loadBtn');
    btn.disabled = true;
    setStatus('正在获取数据：Wind 指标可能需要较长时间，请稍候...');
    const params = new URLSearchParams({
      valuation_years: document.getElementById('valuationYears').value || 5,
      account_months: document.getElementById('accountMonths').value || 12,
      margin_days: document.getElementById('marginDays').value || 120,
      margin_purchase_days: document.getElementById('marginPurchaseDays').value || 120,
      industry_congestion_days: document.getElementById('industryCongestionDays').value || 120,
      market_style_days: document.getElementById('marketStyleDays').value || 120,
      bond_yield_days: document.getElementById('bondYieldDays').value || 500,
      price_days: document.getElementById('priceDays').value || 120,
      crowding_years: document.getElementById('crowdingYears').value || 3,
      price_source: document.getElementById('priceSource').value || 'opentdx'
    });
    try {
      const resp = await fetch(`/api/trends?${params.toString()}`);
      const data = await resp.json();
      if (!resp.ok || !data.ok) throw new Error(data.error || '获取失败');
      renderMetrics(data);
      renderValuation(data.valuation.series);
      renderAccount(data.account.series);
      renderMargin(data.margin.series);
      renderMarginPurchase(data.margin_purchase.series);
      renderIndustryCongestion(data.industry_congestion);
      renderMarketStyle(data.market_style.series);
      renderBondYield(data.bond_yield.series);
      renderPrice(data.price_volume.series);
      renderCrowding(data.crowding.series);
      renderDivergence(data.price_volume.divergence_rows);
      setStatus(`数据获取完成。估值 ${data.valuation.series.length} 条，开户 ${data.account.series.length} 条，融资 ${data.margin.series.length} 条，融资买入占比 ${data.margin_purchase.series.length} 条，行业拥挤度 ${data.industry_congestion.series.length} 条，恐贪 ${data.market_style.series.length} 条，国债 ${data.bond_yield.series.length} 条，量价 ${data.price_volume.series.length} 条，拥挤度 ${data.crowding.series.length} 条。`);
    } catch (err) {
      setStatus(`获取失败：${err.message}`, true);
    } finally {
      btn.disabled = false;
    }
  }
  function renderMetrics(data) {
    document.getElementById('peMetric').textContent = fmt(data.valuation.summary.current_pe);
    document.getElementById('peSub').textContent = `${data.valuation.summary.current_date}，百分位 ${fmt(data.valuation.summary.percentile, 1)}%`;
    document.getElementById('accountMetric').textContent = fmt(data.account.summary.current_value, 0);
    document.getElementById('accountSub').textContent = `${data.account.summary.current_date}，环比 ${fmt(data.account.summary.mom_change_pct, 1)}%`;
    document.getElementById('marginMetric').textContent = `${fmt(data.margin.summary.current_balance_yi, 2)} 亿`;
    document.getElementById('marginSub').textContent = `${data.margin.summary.current_date}，日变化 ${fmt(data.margin.summary.current_change_yi, 2)} 亿`;
    document.getElementById('marginPurchaseMetric').textContent = `${fmt(data.margin_purchase.summary.current_ratio, 2)}%`;
    document.getElementById('marginPurchaseSub').textContent = `${data.margin_purchase.summary.current_date}，融资买入 ${fmt(data.margin_purchase.summary.current_purchase_yi, 2)} 亿`;
    document.getElementById('industryCongestionMetric').textContent = data.industry_congestion.summary.top_sector || '--';
    document.getElementById('industryCongestionSub').textContent = `${data.industry_congestion.summary.current_date}，占比 ${fmt(data.industry_congestion.summary.top_ratio, 2)}%，${data.industry_congestion.summary.classification}`;
    document.getElementById('marketStyleMetric').textContent = fmt(data.market_style.summary.current_score, 1);
    document.getElementById('marketStyleSub').textContent = `${data.market_style.summary.current_date}，${data.market_style.summary.level}`;
    document.getElementById('bondYieldMetric').textContent = `${fmt(data.bond_yield.summary.current_yield, 3)}%`;
    document.getElementById('bondYieldSub').textContent = `${data.bond_yield.summary.current_date}，近一年分位 ${fmt(data.bond_yield.summary.percentile_1y, 1)}%`;
    document.getElementById('divergenceMetric').textContent = `${data.price_volume.summary.divergence_days} 天`;
    document.getElementById('divergenceSub').textContent = `最近5日量价背离，得分 ${fmt(data.price_volume.summary.score, 2)}，数据源 ${data.price_volume.summary.source}`;
    document.getElementById('crowdingMetric').textContent = `${fmt(data.crowding.summary.current_percentile, 1)}%`;
    document.getElementById('crowdingSub').textContent = `${data.crowding.summary.current_date}，前5%成交额占比，${data.crowding.summary.level}`;
  }
  function renderValuation(series) {
    destroyChart('valuationChart');
    charts.valuationChart = new Chart(document.getElementById('valuationChart'), { type:'line', data:{ labels:series.map(x=>x.date), datasets:[{ label:'PE', data:series.map(x=>x.pe), borderColor:'#2563eb', backgroundColor:'rgba(37,99,235,.10)', pointRadius:0, borderWidth:2, tension:.18, fill:true }] }, options:baseOptions('PE') });
  }
  function renderAccount(series) {
    destroyChart('accountChart');
    charts.accountChart = new Chart(document.getElementById('accountChart'), { type:'line', data:{ labels:series.map(x=>x.date), datasets:[{ label:'新增开户数', data:series.map(x=>x.value), borderColor:'#7c3aed', backgroundColor:'rgba(124,58,237,.10)', pointRadius:2, borderWidth:2, tension:.18, fill:true }] }, options:baseOptions('户') });
  }
  function renderMargin(series) {
    destroyChart('marginChart');
    charts.marginChart = new Chart(document.getElementById('marginChart'), { type:'line', data:{ labels:series.map(x=>x.date), datasets:[{ label:'融资余额(亿元)', data:series.map(x=>x.margin_balance_yi), borderColor:'#16a34a', yAxisID:'y', pointRadius:0, borderWidth:2, tension:.18 }, { label:'日变化(亿元)', data:series.map(x=>x.period_net_purchases_yi), borderColor:'#dc2626', yAxisID:'y1', pointRadius:0, borderWidth:1.5, tension:.18 }] }, options:dualOptions('余额(亿元)', '日变化(亿元)') });
  }
  function renderMarginPurchase(series) {
    destroyChart('marginPurchaseChart');
    charts.marginPurchaseChart = new Chart(document.getElementById('marginPurchaseChart'), { type:'line', data:{ labels:series.map(x=>x.date), datasets:[{ label:'融资买入/成交额(%)', data:series.map(x=>x.purchase_ratio), borderColor:'#dc2626', yAxisID:'y', pointRadius:0, borderWidth:2, tension:.18 }, { label:'上证指数', data:series.map(x=>x.index_close), borderColor:'#2563eb', yAxisID:'y1', pointRadius:0, borderWidth:1.5, tension:.18 }] }, options:dualOptions('融资买入/成交额(%)', '上证指数') });
  }
  function renderIndustryCongestion(data) {
    destroyChart('industryCongestionChart');
    const colors = ['#dc2626','#2563eb','#16a34a','#d97706','#7c3aed','#0ea5e9','#db2777','#475569'];
    const labels = data.series.map(x=>x.date);
    const datasets = data.top_sectors.map((name, idx) => ({ label:name, data:data.series.map(x=>x.ratios[name]), borderColor:colors[idx % colors.length], pointRadius:0, borderWidth:1.8, tension:.18 }));
    charts.industryCongestionChart = new Chart(document.getElementById('industryCongestionChart'), { type:'line', data:{ labels, datasets }, options:baseOptions('成交额占比(%)') });
    document.getElementById('industryCongestionRows').innerHTML = data.latest_rank.map(row => `<tr><td>${row.sector}</td><td>${row.board_type}</td><td>${row.member_count}</td><td>${fmt(row.ratio, 2)}%</td><td>${fmt(row.amount_yi, 2)}</td></tr>`).join('');
  }
  function renderMarketStyle(series) {
    destroyChart('marketStyleChart');
    charts.marketStyleChart = new Chart(document.getElementById('marketStyleChart'), { type:'line', data:{ labels:series.map(x=>x.date), datasets:[{ label:'恐慌&贪心得分', data:series.map(x=>x.score), borderColor:'#dc2626', pointRadius:0, borderWidth:2.2, tension:.18 }, { label:'20日上涨动量', data:series.map(x=>x.momentum_score), borderColor:'#2563eb', pointRadius:0, borderWidth:1.4, tension:.18 }, { label:'20日均线宽度', data:series.map(x=>x.breadth_score), borderColor:'#16a34a', pointRadius:0, borderWidth:1.4, tension:.18 }, { label:'新高新低强度', data:series.map(x=>x.high_low_score), borderColor:'#d97706', pointRadius:0, borderWidth:1.4, tension:.18 }] }, options:baseOptions('得分(0-100)') });
  }
  function renderBondYield(series) {
    destroyChart('bondYieldChart');
    charts.bondYieldChart = new Chart(document.getElementById('bondYieldChart'), { type:'line', data:{ labels:series.map(x=>x.date), datasets:[{ label:'10年期国债收益率(%)', data:series.map(x=>x.yield), borderColor:'#0f766e', backgroundColor:'rgba(15,118,110,.10)', pointRadius:0, borderWidth:2, tension:.18, fill:true }] }, options:baseOptions('收益率(%)') });
  }
  function renderPrice(series) {
    destroyChart('priceChart');
    charts.priceChart = new Chart(document.getElementById('priceChart'), { type:'line', data:{ labels:series.map(x=>x.date), datasets:[{ label:'收盘价', data:series.map(x=>x.close), borderColor:'#2563eb', yAxisID:'y', pointRadius:0, borderWidth:2, tension:.18 }, { label:'成交量(万手)', data:series.map(x=>x.volume_wan), borderColor:'#d97706', yAxisID:'y1', pointRadius:0, borderWidth:1.5, tension:.18 }] }, options:dualOptions('收盘价', '成交量(万手)') });
  }
  function renderCrowding(series) {
    destroyChart('crowdingChart');
    charts.crowdingChart = new Chart(document.getElementById('crowdingChart'), { type:'line', data:{ labels:series.map(x=>x.date), datasets:[{ label:'前5%个股成交额占比(%)', data:series.map(x=>x.crowding_ratio), borderColor:'#ef4444', yAxisID:'y', pointRadius:0, borderWidth:2, tension:.18 }, { label:'全A成交额(亿元)', data:series.map(x=>x.total_amount_yi), borderColor:'#0ea5e9', yAxisID:'y1', pointRadius:0, borderWidth:1.5, tension:.18 }] }, options:dualOptions('占比(%)', '全A成交额(亿元)') });
  }
  function renderDivergence(rows) {
    document.getElementById('divergenceRows').innerHTML = rows.map(row => `<tr><td>${row.date}</td><td>${fmt(row.close)}</td><td>${fmt(row.volume_wan)}</td><td>${fmt(row.price_change_pct, 2)}%</td><td>${fmt(row.volume_change_pct, 2)}%</td><td>${row.is_divergence ? '是' : '否'}</td></tr>`).join('');
  }
  function baseOptions(yTitle) { return { responsive:true, maintainAspectRatio:false, interaction:{ mode:'index', intersect:false }, plugins:{ legend:{ position:'top' } }, scales:{ x:{ ticks:{ maxTicksLimit:10 }, grid:{ display:false } }, y:{ title:{ display:true, text:yTitle }, beginAtZero:false } } }; }
  function dualOptions(leftTitle, rightTitle) { const opt = baseOptions(leftTitle); opt.scales.y1 = { position:'right', title:{ display:true, text:rightTitle }, grid:{ drawOnChartArea:false }, beginAtZero:false }; return opt; }
</script>
</body>
</html>
"""


def _as_float(value):
    if pd.isna(value):
        return None
    return float(value)


def _cache_cycle_key(now=None):
    now = now or datetime.now()
    switch_time = now.replace(hour=CACHE_SWITCH_HOUR, minute=CACHE_SWITCH_MINUTE, second=0, microsecond=0)
    if now >= switch_time:
        candidate = now.date()
        if now.weekday() < 5:
            return candidate.strftime("%Y-%m-%d")
    else:
        candidate = (now - timedelta(days=1)).date()
    calendar_dates = _read_qlib_calendar_dates(Path(DEFAULT_QLIB_PROVIDER_URI).resolve())
    if calendar_dates:
        candidates = [item for item in calendar_dates if item <= candidate]
        if candidates:
            return candidates[-1].strftime("%Y-%m-%d")
    return candidate.strftime("%Y-%m-%d")


def _cache_path(name, params):
    payload = json.dumps(params, ensure_ascii=False, sort_keys=True, default=str)
    digest = hashlib.md5(payload.encode("utf-8")).hexdigest()
    return CACHE_DIR / name / f"{_cache_cycle_key()}_{digest}.json"


def _read_json_cache(path):
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return None


def _write_json_cache(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "cached_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "cache_cycle": _cache_cycle_key(),
        "data": value,
    }
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False)


def _with_daily_cache(name, params, loader):
    path = _cache_path(name, params)
    cached = _read_json_cache(path)
    if cached and "data" in cached:
        data = cached["data"]
        summary = data.setdefault("summary", {})
        summary["cache_hit"] = True
        summary["cache_cycle"] = cached.get("cache_cycle")
        summary["cached_at"] = cached.get("cached_at")
        return data
    data = loader()
    summary = data.setdefault("summary", {})
    summary["cache_hit"] = False
    summary["cache_cycle"] = _cache_cycle_key()
    summary["cached_at"] = None
    _write_json_cache(path, data)
    return data


def _get_latest_qlib_calendar_date(provider_uri):
    calendar_dates = _read_qlib_calendar_dates(provider_uri)
    if not calendar_dates:
        return None
    return calendar_dates[-1].strftime("%Y-%m-%d")


def _read_qlib_calendar_dates(provider_uri):
    calendar_file = Path(provider_uri) / "calendars" / "day.txt"
    if not calendar_file.exists():
        return []
    dates = []
    with calendar_file.open("r", encoding="utf-8", errors="replace") as file:
        for line in file:
            value = line.strip()
            if value:
                try:
                    dates.append(pd.to_datetime(value).date())
                except Exception:
                    pass
    return sorted(set(dates))


def _get_qlib_freshness(provider_uri):
    now = datetime.now()
    latest = _get_latest_qlib_calendar_date(provider_uri)
    should_check = now.hour >= QLIB_CHECK_HOUR
    if not should_check:
        return {
            "checked": False,
            "latest_calendar_date": latest,
            "message": "18:00 前不检查 Qlib 是否最新",
        }
    expected = now.strftime("%Y-%m-%d") if now.weekday() < 5 else latest
    is_latest = latest == expected
    return {
        "checked": True,
        "latest_calendar_date": latest,
        "expected_date": expected,
        "is_latest": is_latest,
        "message": "Qlib 本地日历已到今天" if is_latest else f"18:00 后建议更新 Qlib 数据，当前最新 {latest}",
    }


def _fetch_valuation_series(years):
    if not is_wind_available():
        raise RuntimeError("Wind Excel 插件不可用，或当前环境缺少 win32com/pythoncom")
    years = max(1, min(int(years), 10))
    rows = max(300, min(365 * years + 120, 3000))
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=365 * years + 30)).strftime("%Y-%m-%d")
    formula = _build_wind_valuation_formula("881001.WI", "pe", start_date, end_date, rows)
    raw_df = fetch_wind_formula(formula, timeout=120, interval=0.5, visible=False)
    df = _parse_wind_excel_valuation(raw_df, "pe", start_date)
    df = df.dropna(subset=["date", "pe"]).sort_values("date").reset_index(drop=True)
    if df.empty:
        raise RuntimeError("估值数据为空")
    current_pe = float(df.iloc[-1]["pe"])
    percentile = float((df["pe"] < current_pe).sum() / len(df) * 100)
    return {
        "summary": {
            "current_date": df.iloc[-1]["date"].strftime("%Y-%m-%d"),
            "current_pe": current_pe,
            "percentile": percentile,
            "count": int(len(df)),
        },
        "series": [{"date": row["date"].strftime("%Y-%m-%d"), "pe": round(float(row["pe"]), 4)} for _, row in df.iterrows()],
    }


def _fetch_valuation_series_cached(years):
    years = max(1, min(int(years), 10))
    return _with_daily_cache("valuation", {"years": years}, lambda: _fetch_valuation_series(years))


def _fetch_account_series(months):
    months = max(3, min(int(months), 60))
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=months * 31 + 15)).strftime("%Y-%m-%d")
    candidate_codes = [DEFAULT_ACCOUNT_CODE, "F5536637", "K7243555", "M0010362"]
    _, df, formula, used_code = _fetch_account_data(candidate_codes, start_date, end_date)
    df = df.dropna(subset=["date", "value"]).sort_values("date").tail(months).reset_index(drop=True)
    if df.empty:
        raise RuntimeError("开户数据为空")
    current_value = float(df.iloc[-1]["value"])
    prev_value = float(df.iloc[-2]["value"]) if len(df) >= 2 else None
    mom_change_pct = (current_value - prev_value) / prev_value * 100 if prev_value else None
    return {
        "summary": {
            "name": DEFAULT_ACCOUNT_NAME,
            "used_code": used_code,
            "formula": formula,
            "current_date": df.iloc[-1]["date"].strftime("%Y-%m"),
            "current_value": current_value,
            "mom_change_pct": mom_change_pct,
            "count": int(len(df)),
        },
        "series": [{"date": row["date"].strftime("%Y-%m"), "value": round(float(row["value"]), 4)} for _, row in df.iterrows()],
    }


def _fetch_account_series_cached(months):
    months = max(3, min(int(months), 60))
    return _with_daily_cache("account", {"months": months}, lambda: _fetch_account_series(months))


def _fetch_margin_series(days):
    days = max(20, min(int(days), 500))
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=int(days * 1.6) + 10)).strftime("%Y-%m-%d")
    df, components = _fetch_margin_total(start_date, end_date, rows=max(days + 30, 120))
    df = df.dropna(subset=["date", "margin_balance"]).sort_values("date").tail(days).reset_index(drop=True)
    if df.empty:
        raise RuntimeError("融资余额数据为空")
    current_change = df.iloc[-1].get("period_net_purchases")
    return {
        "summary": {
            "current_date": df.iloc[-1]["date"].strftime("%Y-%m-%d"),
            "current_balance_yi": float(df.iloc[-1]["margin_balance"]) / 1e4,
            "current_change_yi": float(current_change) / 1e4 if pd.notna(current_change) else None,
            "components": components,
            "count": int(len(df)),
        },
        "series": [
            {
                "date": row["date"].strftime("%Y-%m-%d"),
                "margin_balance_yi": round(float(row["margin_balance"]) / 1e4, 4),
                "period_net_purchases_yi": round(float(row["period_net_purchases"]) / 1e4, 4) if pd.notna(row.get("period_net_purchases")) else None,
            }
            for _, row in df.iterrows()
        ],
    }


def _fetch_margin_series_cached(days):
    days = max(20, min(int(days), 500))
    return _with_daily_cache("margin", {"days": days}, lambda: _fetch_margin_series(days))


def _build_edb_formula(code, start_date, end_date, rows=800):
    return (
        f'=WSD("{code}","EDBclose","{start_date}","{end_date}",'
        f'"TradingCalendar=SSE","PriceAdj=","rptType=1","Version=1",'
        f'"ShowParams=Y","cols=1;rows={rows}")'
    )


def _fetch_bond_yield_windpy(start_date, end_date):
    last_error = None
    for code, name in BOND_YIELD_SOURCES:
        try:
            from WindPy import w
            w.start()
            data = w.edb(code, start_date, end_date)
        except Exception as exc:
            last_error = exc
            continue
        if getattr(data, "ErrorCode", -1) != 0 or not getattr(data, "Data", None):
            last_error = RuntimeError(f"WindPy edb 错误代码: {getattr(data, 'ErrorCode', None)}")
            continue
        rows = []
        fields = list(getattr(data, "Fields", []) or [])
        values = list(getattr(data, "Data", []) or [])
        if len(values) >= 2:
            date_values = values[0] if "DATE" in str(fields[0]).upper() else values[-1]
            yield_values = values[1] if date_values is values[0] else values[0]
            rows = [{"date": date, "yield": value} for date, value in zip(date_values, yield_values)]
        df = pd.DataFrame(rows)
        if not df.empty:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            df["yield"] = pd.to_numeric(df["yield"], errors="coerce")
            df = df.dropna(subset=["date", "yield"]).sort_values("date").reset_index(drop=True)
        if not df.empty:
            return df, "WindPy EDB", code, name, f'w.edb("{code}", "{start_date}", "{end_date}")'
    raise RuntimeError(f"WindPy EDB 获取失败: {last_error}")


def _fetch_bond_yield_akshare(start_date):
    try:
        import akshare as ak
    except Exception as exc:
        raise RuntimeError(f"未安装 AKShare，无法兜底获取中国10年期国债收益率: {exc}") from exc
    raw = ak.bond_zh_us_rate(start_date=pd.to_datetime(start_date).strftime("%Y%m%d"))
    if raw is None or raw.empty:
        raise RuntimeError("AKShare 中国/美国国债收益率数据为空")
    date_col = raw.columns[0]
    yield_col = next((col for col in raw.columns if "中国" in str(col) and "10" in str(col)), None)
    if yield_col is None:
        yield_col = next((col for col in raw.columns if "10" in str(col)), None)
    if yield_col is None:
        raise RuntimeError("AKShare 返回数据缺少中国10年期国债收益率字段")
    df = pd.DataFrame({
        "date": pd.to_datetime(raw[date_col], errors="coerce"),
        "yield": pd.to_numeric(raw[yield_col], errors="coerce"),
    })
    df = df.dropna(subset=["date", "yield"]).sort_values("date").reset_index(drop=True)
    if df.empty:
        raise RuntimeError("AKShare 中国10年期国债收益率解析为空")
    return df, "AKShare bond_zh_us_rate", None, "中国10年期国债收益率", "ak.bond_zh_us_rate"


def _fetch_bond_yield_series(days):
    days = max(20, min(int(days), 1500))
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=int(days * 1.8) + 30)).strftime("%Y-%m-%d")
    try:
        df, source, used_code, used_name, used_formula = _fetch_bond_yield_windpy(start_date, end_date)
    except Exception:
        df, source, used_code, used_name, used_formula = _fetch_bond_yield_akshare(start_date)
    df = df.tail(days).reset_index(drop=True)
    current_yield = float(df.iloc[-1]["yield"])
    one_year = df.tail(min(len(df), 252))
    percentile_1y = float((one_year["yield"] < current_yield).sum() / len(one_year) * 100)
    return {
        "summary": {
            "source": source,
            "name": used_name,
            "used_code": used_code,
            "formula": used_formula,
            "current_date": df.iloc[-1]["date"].strftime("%Y-%m-%d"),
            "current_yield": current_yield,
            "percentile_1y": percentile_1y,
            "count": int(len(df)),
        },
        "series": [
            {
                "date": row["date"].strftime("%Y-%m-%d"),
                "yield": round(float(row["yield"]), 6),
            }
            for _, row in df.iterrows()
        ],
    }


def _fetch_bond_yield_series_cached(days):
    days = max(20, min(int(days), 1500))
    return _with_daily_cache("bond_yield", {"days": days}, lambda: _fetch_bond_yield_series(days))


def _build_margin_purchase_formula(start_date, end_date):
    return (
        '=WSET("margintradingsizeanalys(value)",'
        f'"exchange=all;startdate={start_date};enddate={end_date};frequency=day;sort=asc")'
    )


def _normalize_wset_table(raw_df):
    if raw_df is None or raw_df.empty:
        return pd.DataFrame()
    df = raw_df.copy()
    first_row = [str(x).strip() for x in df.iloc[0].tolist()]
    known_headers = {
        "end_date", "date", "trade_date", "日期",
        "qjmre", "period_bought_amount", "期间买入额",
        "mrezb", "total_amount_ratio_a-share_amount", "买入额占A股成交额(%)",
    }
    if any(item in known_headers for item in first_row):
        df = df.iloc[1:].reset_index(drop=True)
        df.columns = first_row
    return df


def _pick_column(df, names, date_like=False, numeric_like=False):
    for name in names:
        if name in df.columns:
            return name
    best_col = None
    best_count = 0
    for col in df.columns:
        series = pd.to_datetime(df[col], errors="coerce") if date_like else pd.to_numeric(df[col], errors="coerce")
        count = int(series.notna().sum())
        if count > best_count:
            best_col = col
            best_count = count
    if date_like and best_count >= 5:
        return best_col
    if numeric_like and best_count >= 5:
        return best_col
    return None


def _parse_margin_purchase_data(raw_df):
    df = _normalize_wset_table(raw_df)
    if df.empty:
        return pd.DataFrame(columns=["date", "period_bought_amount", "purchase_ratio"])
    date_col = _pick_column(df, ["end_date", "date", "trade_date", "日期"], date_like=True)
    purchase_col = next((name for name in ["period_bought_amount", "qjmre", "期间买入额"] if name in df.columns), None)
    ratio_col = _pick_column(
        df,
        ["total_amount_ratio_a-share_amount", "mrezb", "买入额占A股成交额(%)", "买入额占A股成交额_百分比"],
        numeric_like=True,
    )
    if date_col is None or ratio_col is None:
        raise RuntimeError("融资买入/成交额数据缺少日期或比例字段")
    result = pd.DataFrame({
        "date": pd.to_datetime(df[date_col], errors="coerce"),
        "purchase_ratio": pd.to_numeric(df[ratio_col], errors="coerce"),
    })
    if purchase_col is not None:
        result["period_bought_amount"] = pd.to_numeric(df[purchase_col], errors="coerce")
    else:
        result["period_bought_amount"] = None
    return result.dropna(subset=["date", "purchase_ratio"]).sort_values("date").reset_index(drop=True)


def _fetch_margin_purchase_raw(start_date, end_date):
    params = f"exchange=all;startdate={start_date};enddate={end_date};frequency=day;sort=asc"
    try:
        from WindPy import w
    except Exception:
        w = None
    if w is not None:
        try:
            w.start()
            data = w.wset("margintradingsizeanalys(value)", params)
        except Exception as exc:
            raise RuntimeError(f"WindPy wset 获取融资买入/成交额失败: {exc}") from exc
        if getattr(data, "ErrorCode", -1) == 0 and getattr(data, "Data", None):
            df = pd.DataFrame(data.Data, index=data.Fields).T
            df.columns = data.Fields
            return df, f'w.wset("margintradingsizeanalys(value)", "{params}")'
        raise RuntimeError(f"WindPy wset 获取融资买入/成交额失败，错误代码: {getattr(data, 'ErrorCode', None)}")
    formula = _build_margin_purchase_formula(start_date, end_date)
    raw_df = fetch_wind_formula(formula, timeout=120, interval=0.5, visible=False)
    return raw_df, formula


def _fetch_margin_purchase_series(days):
    days = max(20, min(int(days), 500))
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=int(days * 1.8) + 30)).strftime("%Y-%m-%d")
    raw_df, formula = _fetch_margin_purchase_raw(start_date, end_date)
    df = _parse_margin_purchase_data(raw_df).tail(days).reset_index(drop=True)
    if df.empty:
        raise RuntimeError("融资买入/成交额数据为空")

    index_df, index_source = _fetch_price_volume_opentdx(max(days + 30, 120))
    index_df = index_df[["date", "close"]].copy()
    index_df["date"] = pd.to_datetime(index_df["date"], errors="coerce")
    index_df["close"] = pd.to_numeric(index_df["close"], errors="coerce")
    index_df = index_df.dropna(subset=["date", "close"]).sort_values("date")

    merged = pd.merge_asof(
        df.sort_values("date"),
        index_df.rename(columns={"close": "index_close"}),
        on="date",
        direction="backward",
    )
    merged = merged.dropna(subset=["date", "purchase_ratio"]).reset_index(drop=True)
    current_purchase = merged.iloc[-1].get("period_bought_amount")
    return {
        "summary": {
            "source": "Wind WSET margintradingsizeanalys(value)",
            "index_source": index_source,
            "formula": formula,
            "current_date": merged.iloc[-1]["date"].strftime("%Y-%m-%d"),
            "current_ratio": float(merged.iloc[-1]["purchase_ratio"]),
            "current_purchase_yi": float(current_purchase) / 1e8 if pd.notna(current_purchase) else None,
            "current_index_close": float(merged.iloc[-1]["index_close"]) if pd.notna(merged.iloc[-1].get("index_close")) else None,
            "count": int(len(merged)),
        },
        "series": [
            {
                "date": row["date"].strftime("%Y-%m-%d"),
                "purchase_ratio": round(float(row["purchase_ratio"]), 4),
                "period_bought_amount_yi": round(float(row["period_bought_amount"]) / 1e8, 4) if pd.notna(row.get("period_bought_amount")) else None,
                "index_close": round(float(row["index_close"]), 4) if pd.notna(row.get("index_close")) else None,
            }
            for _, row in merged.iterrows()
        ],
    }


def _fetch_margin_purchase_series_cached(days):
    days = max(20, min(int(days), 500))
    return _with_daily_cache("margin_purchase", {"days": days}, lambda: _fetch_margin_purchase_series(days))


def _build_industry_congestion(days):
    days = max(20, min(int(days), 500))
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=int(days * 1.8) + 30)).strftime("%Y-%m-%d")
    last_error = None
    selected_config = None
    universe = {}
    board_meta = {}
    for board_types, classification in ((["HY2"], "OpenTDX HY2 行业板块"), (["HY"], "OpenTDX HY 行业板块")):
        try:
            config = OpenTdxSectorConfig(
                opentdx_root=str(OPENTDX_ROOT),
                board_types=board_types,
                min_members=5,
                max_members=800,
                kline_count=max(days + 60, 260),
            )
            universe, board_meta = build_opentdx_sector_universe(config)
            if board_meta:
                selected_config = (config, classification)
                break
        except Exception as exc:
            last_error = exc
            continue
    if not board_meta or selected_config is None:
        raise RuntimeError(f"OpenTDX 行业板块为空，无法计算行业拥挤度: {last_error}")

    config, classification = selected_config
    panel = load_opentdx_sector_kline_panel(board_meta, start_date, end_date, config)
    amount = panel.get("amount", pd.DataFrame())
    if amount.empty:
        raise RuntimeError("OpenTDX 行业板块成交额为空，无法计算行业拥挤度")
    amount = amount.apply(pd.to_numeric, errors="coerce").dropna(how="all").tail(days)
    total_amount = amount.sum(axis=1, min_count=1)
    ratio = amount.div(total_amount.replace(0, pd.NA), axis=0) * 100
    ratio = ratio.dropna(how="all")
    if ratio.empty:
        raise RuntimeError("OpenTDX 行业拥挤度计算结果为空")

    latest_date = ratio.index[-1]
    latest_ratio = ratio.loc[latest_date].dropna().sort_values(ascending=False)
    latest_amount = amount.loc[latest_date].reindex(latest_ratio.index)
    latest_rank = []
    for sector, value in latest_ratio.head(20).items():
        meta = board_meta.get(sector, {})
        latest_rank.append({
            "sector": str(sector),
            "ratio": round(float(value), 4),
            "amount_yi": round(float(latest_amount.get(sector, 0)) / 1e8, 4),
            "board_type": str(meta.get("board_type", "")),
            "member_count": int(meta.get("member_count", 0) or 0),
        })

    top_sectors = [row["sector"] for row in latest_rank[:8]]
    series = []
    for date, row in ratio[top_sectors].iterrows():
        series.append({
            "date": pd.to_datetime(date).strftime("%Y-%m-%d"),
            "ratios": {
                sector: (round(float(row[sector]), 4) if pd.notna(row.get(sector)) else None)
                for sector in top_sectors
            },
        })

    top_row = latest_rank[0] if latest_rank else {}
    return {
        "summary": {
            "source": "OpenTDX",
            "classification": classification,
            "definition": "行业板块成交金额 / 全部行业板块成交金额",
            "current_date": pd.to_datetime(latest_date).strftime("%Y-%m-%d"),
            "top_sector": top_row.get("sector"),
            "top_ratio": top_row.get("ratio"),
            "sector_count": int(len(board_meta)),
            "count": int(len(series)),
        },
        "top_sectors": top_sectors,
        "latest_rank": latest_rank,
        "series": series,
    }


def _fetch_industry_congestion_cached(days):
    days = max(20, min(int(days), 500))
    return _with_daily_cache("industry_congestion", {"days": days}, lambda: _build_industry_congestion(days))


def _market_style_level(score):
    if score >= 80:
        return "极度贪心"
    if score >= 60:
        return "贪心"
    if score <= 20:
        return "极度恐慌"
    if score <= 40:
        return "恐慌"
    return "中性"


def _clip_score(series):
    return series.clip(lower=0, upper=100)


def _fetch_market_style_series(days):
    days = max(20, min(int(days), 500))
    provider_uri = Path(DEFAULT_QLIB_PROVIDER_URI).resolve()
    if not provider_uri.exists():
        raise FileNotFoundError(f"Qlib 数据目录不存在: {provider_uri}")

    try:
        import qlib
        from qlib.data import D
    except Exception as exc:
        raise RuntimeError(f"未能导入 pyqlib，无法读取 Qlib 数据: {exc}") from exc

    qlib.init(provider_uri=str(provider_uri), region="cn")
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=int(days * 1.8) + 120)).strftime("%Y-%m-%d")
    raw = D.features(
        instruments=D.instruments("all"),
        fields=["$close", "$amount"],
        start_time=start_date,
        end_time=end_date,
        freq="day",
    )
    if raw is None or raw.empty:
        raise RuntimeError("Qlib 全市场行情数据为空，无法计算恐慌&贪心指标")

    data = raw.reset_index()
    if "datetime" not in data.columns:
        date_cols = [col for col in data.columns if "date" in str(col).lower() or "time" in str(col).lower()]
        if not date_cols:
            raise RuntimeError("Qlib 返回数据缺少日期字段")
        data = data.rename(columns={date_cols[0]: "datetime"})
    if "instrument" not in data.columns:
        inst_cols = [col for col in data.columns if "instrument" in str(col).lower() or "code" in str(col).lower()]
        if not inst_cols:
            raise RuntimeError("Qlib 返回数据缺少股票代码字段")
        data = data.rename(columns={inst_cols[0]: "instrument"})

    data["date"] = pd.to_datetime(data["datetime"], errors="coerce").dt.normalize()
    data["close"] = pd.to_numeric(data["$close"], errors="coerce")
    data["amount"] = pd.to_numeric(data["$amount"], errors="coerce")
    data = data.dropna(subset=["date", "instrument", "close"])
    if data.empty:
        raise RuntimeError("Qlib 有效行情样本为空，无法计算恐慌&贪心指标")

    close = data.pivot_table(index="date", columns="instrument", values="close", aggfunc="last").sort_index()
    amount = data.pivot_table(index="date", columns="instrument", values="amount", aggfunc="last").reindex(close.index)
    valid_counts = close.notna().sum(axis=1)
    daily_ret = close.pct_change(fill_method=None)
    ret20 = close / close.shift(20) - 1
    ma20 = close.rolling(20, min_periods=10).mean()
    high60 = close.rolling(60, min_periods=30).max()
    low60 = close.rolling(60, min_periods=30).min()
    total_amount = amount.sum(axis=1, min_count=100)

    momentum_score = (ret20 > 0).sum(axis=1) / valid_counts * 100
    breadth_score = (close > ma20).sum(axis=1) / valid_counts * 100
    advance_score = (daily_ret > 0).sum(axis=1) / valid_counts * 100
    new_high_ratio = (close >= high60).sum(axis=1) / valid_counts
    new_low_ratio = (close <= low60).sum(axis=1) / valid_counts
    high_low_score = _clip_score(50 + (new_high_ratio - new_low_ratio) * 200)
    amount_ratio = total_amount / total_amount.rolling(20, min_periods=10).mean()
    volume_score = _clip_score(50 + (amount_ratio - 1) * 100)

    score_df = pd.DataFrame({
        "momentum_score": momentum_score,
        "breadth_score": breadth_score,
        "advance_score": advance_score,
        "high_low_score": high_low_score,
        "volume_score": volume_score,
        "sample_count": valid_counts,
        "total_amount_yi": total_amount / 1e8,
    }).dropna(subset=["momentum_score", "breadth_score", "advance_score", "high_low_score", "volume_score"])
    score_df = score_df.loc[score_df["sample_count"] >= 100].copy()
    if score_df.empty:
        raise RuntimeError("恐慌&贪心指标有效样本不足")
    score_df["score"] = score_df[["momentum_score", "breadth_score", "advance_score", "high_low_score", "volume_score"]].mean(axis=1)
    score_df = score_df.tail(days).reset_index().rename(columns={"index": "date"})

    current = score_df.iloc[-1]
    return {
        "summary": {
            "source": "Qlib",
            "definition": "Qlib 全市场动量、均线宽度、新高新低、上涨家数、成交活跃度五维合成",
            "provider_uri": str(provider_uri),
            "qlib_freshness": _get_qlib_freshness(provider_uri),
            "current_date": current["date"].strftime("%Y-%m-%d"),
            "current_score": float(current["score"]),
            "level": _market_style_level(float(current["score"])),
            "sample_count": int(current["sample_count"]),
            "count": int(len(score_df)),
        },
        "series": [
            {
                "date": row["date"].strftime("%Y-%m-%d"),
                "score": round(float(row["score"]), 4),
                "momentum_score": round(float(row["momentum_score"]), 4),
                "breadth_score": round(float(row["breadth_score"]), 4),
                "advance_score": round(float(row["advance_score"]), 4),
                "high_low_score": round(float(row["high_low_score"]), 4),
                "volume_score": round(float(row["volume_score"]), 4),
                "sample_count": int(row["sample_count"]),
                "total_amount_yi": round(float(row["total_amount_yi"]), 4) if pd.notna(row["total_amount_yi"]) else None,
            }
            for _, row in score_df.iterrows()
        ],
    }


def _calc_crowding_level(percentile):
    if percentile >= 50:
        return "极度拥挤"
    if percentile >= 40:
        return "偏拥挤"
    if percentile <= 25:
        return "交易清淡"
    return "中性"


def _fetch_crowding_series(years):
    years = max(1, min(int(years), 10))
    provider_uri = Path(DEFAULT_QLIB_PROVIDER_URI).resolve()
    if not provider_uri.exists():
        raise FileNotFoundError(f"Qlib 数据目录不存在: {provider_uri}")

    try:
        import qlib
        from qlib.data import D
    except Exception as exc:
        raise RuntimeError(f"未能导入 pyqlib，无法读取 Qlib 数据: {exc}") from exc

    qlib.init(provider_uri=str(provider_uri), region="cn")
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=365 * years + 30)).strftime("%Y-%m-%d")
    instruments = D.instruments("all")
    raw = D.features(
        instruments=instruments,
        fields=["$amount"],
        start_time=start_date,
        end_time=end_date,
        freq="day",
    )
    if raw is None or raw.empty:
        raise RuntimeError("Qlib 全市场 amount 数据为空，无法计算交易拥挤度")

    data = raw.reset_index()
    if "$amount" not in data.columns:
        value_cols = [col for col in data.columns if str(col).lower().endswith("amount")]
        if not value_cols:
            raise RuntimeError("Qlib 返回数据缺少 $amount 字段")
        data = data.rename(columns={value_cols[0]: "$amount"})
    if "datetime" not in data.columns:
        date_cols = [col for col in data.columns if "date" in str(col).lower() or "time" in str(col).lower()]
        if not date_cols:
            raise RuntimeError("Qlib 返回数据缺少日期字段")
        data = data.rename(columns={date_cols[0]: "datetime"})

    data["date"] = pd.to_datetime(data["datetime"], errors="coerce").dt.normalize()
    data["amount"] = pd.to_numeric(data["$amount"], errors="coerce")
    data = data.dropna(subset=["date", "amount"])
    data = data.loc[data["amount"] > 0]
    if data.empty:
        raise RuntimeError("Qlib 有效成交额样本为空，无法计算交易拥挤度")

    rows = []
    for date, group in data.groupby("date", sort=True):
        amounts = group["amount"].dropna()
        sample_count = int(len(amounts))
        if sample_count < 100:
            continue
        top_count = max(1, round(sample_count * 0.05))
        total_amount = float(amounts.sum())
        top_amount = float(amounts.nlargest(top_count).sum())
        rows.append({
            "date": date,
            "top_amount": top_amount,
            "total_amount": total_amount,
            "sample_count": sample_count,
            "top_count": int(top_count),
        })
    df = pd.DataFrame(rows)
    df = df.dropna(subset=["date", "top_amount", "total_amount"])
    df = df.loc[df["total_amount"] > 0].sort_values("date").reset_index(drop=True)
    if df.empty:
        raise RuntimeError("Qlib 交易拥挤度计算结果为空")

    df["crowding_ratio"] = df["top_amount"] / df["total_amount"] * 100
    df["total_amount_yi"] = df["total_amount"] / 1e8
    current_ratio = float(df.iloc[-1]["crowding_ratio"])
    current_percentile = current_ratio
    level = _calc_crowding_level(current_percentile)

    return {
        "summary": {
            "source": "Qlib",
            "definition": "成交额排名前5%的个股成交额 / 全部A股成交额",
            "provider_uri": str(provider_uri),
            "qlib_freshness": _get_qlib_freshness(provider_uri),
            "current_date": df.iloc[-1]["date"].strftime("%Y-%m-%d"),
            "current_ratio": current_ratio,
            "current_percentile": current_percentile,
            "level": level,
            "count": int(len(df)),
            "stock_count": int(df.iloc[-1]["sample_count"]),
            "top_count": int(df.iloc[-1]["top_count"]),
        },
        "series": [
            {
                "date": row["date"].strftime("%Y-%m-%d"),
                "crowding_ratio": round(float(row["crowding_ratio"]), 4),
                "total_amount_yi": round(float(row["total_amount_yi"]), 4),
                "sample_count": int(row["sample_count"]),
                "top_count": int(row["top_count"]),
            }
            for _, row in df.iterrows()
        ],
    }


def _fetch_price_volume_opentdx(days):
    from opentdx.const import MARKET, PERIOD
    from opentdx.tdxClient import TdxClient

    days = max(20, min(int(days), 500))
    with TdxClient() as client:
        bars = client.stock_kline(MARKET.SH, "999999", PERIOD.DAILY, count=days)
    df = pd.DataFrame(bars)
    if df.empty:
        raise RuntimeError("OpenTDX 量价数据为空")
    date_col = "datetime" if "datetime" in df.columns else "date"
    df = df.rename(columns={date_col: "date", "vol": "volume"})
    return df[["date", "close", "volume"]].copy(), "OpenTDX"


def _fetch_price_volume_xtquant(days):
    from xtquant import xtdata

    days = max(20, min(int(days), 500))
    data = xtdata.get_market_data_ex(field_list=["close", "volume"], stock_list=["000001.SH"], period="1d", count=days)
    if not data or "close" not in data or "volume" not in data:
        raise RuntimeError("XtQuant 量价数据为空")
    close = data["close"]["000001.SH"]
    volume = data["volume"]["000001.SH"]
    df = pd.DataFrame({"date": close.index, "close": close.values, "volume": volume.values})
    return df, "XtQuant"


def _calc_price_volume_result(days, source):
    if source == "xtquant":
        df, source_name = _fetch_price_volume_xtquant(days)
    else:
        df, source_name = _fetch_price_volume_opentdx(days)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df["volume"] = pd.to_numeric(df["volume"], errors="coerce")
    df = df.dropna(subset=["date", "close", "volume"]).sort_values("date").reset_index(drop=True)
    if len(df) < 6:
        raise RuntimeError("量价数据不足，至少需要 6 个交易日")
    df["volume_wan"] = df["volume"] / 10000
    df["price_change_pct"] = df["close"].pct_change() * 100
    df["volume_change_pct"] = df["volume"].pct_change() * 100
    df["price_up"] = df["close"] > df["close"].shift(1)
    df["volume_shrink_rate"] = (df["volume"].shift(1) - df["volume"]) / df["volume"].shift(1)
    df["is_divergence"] = df["price_up"] & (df["volume_shrink_rate"] >= 0.20)
    recent_check = df.tail(5)
    divergence_days = int(recent_check["is_divergence"].sum())
    if divergence_days == 1:
        score = 1.0
    elif divergence_days >= 2:
        score = 1.0 + (divergence_days - 1) * 0.5
    else:
        score = 0.0
    series = [
        {
            "date": row["date"].strftime("%Y-%m-%d"),
            "close": round(float(row["close"]), 4),
            "volume_wan": round(float(row["volume_wan"]), 4),
        }
        for _, row in df.iterrows()
    ]
    divergence_rows = [
        {
            "date": row["date"].strftime("%Y-%m-%d"),
            "close": round(float(row["close"]), 4),
            "volume_wan": round(float(row["volume_wan"]), 4),
            "price_change_pct": _as_float(row["price_change_pct"]),
            "volume_change_pct": _as_float(row["volume_change_pct"]),
            "is_divergence": bool(row["is_divergence"]),
        }
        for _, row in df.tail(20).sort_values("date", ascending=False).iterrows()
    ]
    return {
        "summary": {
            "source": source_name,
            "current_date": df.iloc[-1]["date"].strftime("%Y-%m-%d"),
            "current_close": float(df.iloc[-1]["close"]),
            "divergence_days": divergence_days,
            "score": score,
            "count": int(len(df)),
        },
        "series": series,
        "divergence_rows": divergence_rows,
    }


def _calc_price_volume_result_cached(days, source):
    days = max(20, min(int(days), 500))
    source = source if source == "xtquant" else "opentdx"
    return _with_daily_cache("price_volume", {"days": days, "source": source}, lambda: _calc_price_volume_result(days, source))


@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/api/trends")
def api_trends():
    try:
        result = {
            "valuation": _fetch_valuation_series_cached(request.args.get("valuation_years", 5, type=int)),
            "account": _fetch_account_series_cached(request.args.get("account_months", 12, type=int)),
            "margin": _fetch_margin_series_cached(request.args.get("margin_days", 120, type=int)),
            "margin_purchase": _fetch_margin_purchase_series_cached(request.args.get("margin_purchase_days", 120, type=int)),
            "industry_congestion": _fetch_industry_congestion_cached(request.args.get("industry_congestion_days", 120, type=int)),
            "market_style": _fetch_market_style_series(request.args.get("market_style_days", 120, type=int)),
            "bond_yield": _fetch_bond_yield_series_cached(request.args.get("bond_yield_days", 500, type=int)),
            "crowding": _fetch_crowding_series(request.args.get("crowding_years", 3, type=int)),
            "price_volume": _calc_price_volume_result_cached(
                request.args.get("price_days", 120, type=int),
                request.args.get("price_source", "opentdx"),
            ),
        }
        return jsonify({"ok": True, **result})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


def main():
    parser = argparse.ArgumentParser(description="大盘逃顶指标走势 Web 展示")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=7796)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    app.run(host=args.host, port=args.port, debug=args.debug, use_reloader=False)


if __name__ == "__main__":
    main()
