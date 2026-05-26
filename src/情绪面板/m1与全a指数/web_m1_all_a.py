"""
M1 与 Wind 全A指数 Web 展示
"""

import argparse
import sys
import threading
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from flask import Flask, jsonify, render_template_string, request


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from md.winds.通过excel插件.wind_client import (
    _close_excel_session,
    _convert_pywintypes,
    _create_excel_session,
    _normalize_used_range,
    fetch_wind_formula,
    is_wind_available,
)


app = Flask(__name__)

DEFAULT_ALL_A_CODE = "881001.WI"
DEFAULT_ALL_A_FIELD = "close"
DEFAULT_M1_CODE = "M0001383"
DEFAULT_M1_FIELD = "close"
DEFAULT_YEARS = 10

TASK_LOCK = threading.Lock()
TASK_STATE = {
    "task_id": None,
    "running": False,
    "done": False,
    "ok": False,
    "error": None,
    "current_step": "等待开始",
    "started_at": None,
    "ended_at": None,
    "elapsed": 0,
    "logs": [],
    "result": None,
}

HTML = """
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>M1 与 Wind 全A指数</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    :root {
      --bg: #f5f7fb;
      --card: #ffffff;
      --text: #111827;
      --muted: #64748b;
      --blue: #2563eb;
      --red: #dc2626;
      --green: #16a34a;
      --border: #e5e7eb;
      --shadow: 0 18px 42px rgba(15, 23, 42, 0.08);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      color: var(--text);
      font-family: "Microsoft YaHei", "Segoe UI", Arial, sans-serif;
      background: radial-gradient(circle at 10% 0%, #dbeafe 0, transparent 30%), var(--bg);
    }
    .page { max-width: 1220px; margin: 0 auto; padding: 28px 18px 46px; }
    .hero { display: flex; justify-content: space-between; gap: 18px; align-items: center; margin-bottom: 18px; }
    h1 { margin: 0 0 8px; font-size: 30px; letter-spacing: -0.03em; }
    .desc { margin: 0; color: var(--muted); line-height: 1.7; }
    .toolbar {
      display: grid;
      grid-template-columns: repeat(4, auto);
      gap: 10px;
      align-items: end;
      background: rgba(255,255,255,0.9);
      border: 1px solid var(--border);
      border-radius: 18px;
      padding: 14px;
      box-shadow: var(--shadow);
    }
    label { display: block; color: var(--muted); font-size: 12px; margin-bottom: 5px; }
    input {
      width: 120px;
      border: 1px solid var(--border);
      border-radius: 11px;
      padding: 9px 10px;
      outline: none;
      font-size: 14px;
      background: white;
    }
    input.wide { width: 150px; }
    button {
      border: 0;
      border-radius: 12px;
      padding: 10px 18px;
      background: linear-gradient(135deg, #2563eb, #1d4ed8);
      color: #fff;
      font-weight: 800;
      cursor: pointer;
      box-shadow: 0 10px 18px rgba(37, 99, 235, 0.24);
    }
    button:disabled { opacity: 0.55; cursor: wait; }
    .status {
      margin: 12px 0 16px;
      border: 1px solid #bfdbfe;
      border-radius: 14px;
      padding: 12px 14px;
      background: #eff6ff;
      color: #1e40af;
    }
    .status.error { background: #fef2f2; border-color: #fecaca; color: #991b1b; }
    .run-status {
      display: grid;
      grid-template-columns: 1.1fr 0.9fr;
      gap: 14px;
      margin-bottom: 16px;
    }
    .step-title { font-size: 18px; font-weight: 800; margin-bottom: 8px; }
    .step-meta { color: var(--muted); font-size: 13px; line-height: 1.7; }
    .log-box {
      height: 150px;
      overflow: auto;
      background: #0f172a;
      color: #dbeafe;
      border-radius: 12px;
      padding: 10px 12px;
      font-family: Consolas, monospace;
      font-size: 12px;
      line-height: 1.55;
      white-space: pre-wrap;
    }
    .cards { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; margin-bottom: 16px; }
    .card {
      background: rgba(255,255,255,0.94);
      border: 1px solid var(--border);
      border-radius: 18px;
      padding: 18px;
      box-shadow: var(--shadow);
    }
    .metric-label { color: var(--muted); font-size: 13px; margin-bottom: 8px; }
    .metric-value { font-size: 25px; font-weight: 850; }
    .metric-sub { margin-top: 8px; color: var(--muted); font-size: 13px; line-height: 1.5; }
    .analysis-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin: 16px 0; }
    .conclusion { font-size: 18px; font-weight: 850; line-height: 1.6; margin-bottom: 10px; }
    .analysis-note { color: var(--muted); line-height: 1.7; font-size: 13px; }
    .chart-card { padding: 20px; }
    .chart-wrap { height: 510px; }
    .formula-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-top: 16px; }
    pre {
      white-space: pre-wrap;
      word-break: break-all;
      margin: 0;
      padding: 12px;
      background: #0f172a;
      color: #dbeafe;
      border-radius: 12px;
      font-size: 12px;
      line-height: 1.5;
    }
    .table-wrap { max-height: 330px; overflow: auto; }
    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    th, td { border-bottom: 1px solid var(--border); padding: 9px 10px; text-align: right; }
    th:first-child, td:first-child { text-align: left; }
    th { color: var(--muted); background: #f8fafc; position: sticky; top: 0; }
    @media (max-width: 980px) {
      .hero { flex-direction: column; align-items: stretch; }
      .toolbar { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .cards { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .formula-grid { grid-template-columns: 1fr; }
      .run-status { grid-template-columns: 1fr; }
      .analysis-grid { grid-template-columns: 1fr; }
    }
    @media (max-width: 560px) { .cards { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <div class="page">
    <section class="hero">
      <div>
        <h1>M1 与 Wind 全A指数月频同图观察</h1>
        <p class="desc">数据通过 Wind Excel 插件获取。M1 使用你在 Excel 验证过的 <b>WSD</b> 公式取月末数据；全A指数取日频 close 后按 M1 月末日期对齐。</p>
      </div>
      <div class="toolbar">
        <div><label>M1代码</label><input id="m1Code" class="wide" value="M0001383"></div>
        <div><label>M1字段</label><input id="m1Field" value="close"></div>
        <div><label>回看年数</label><input id="years" type="number" min="1" max="20" value="10"></div>
        <div><label>全A最大行数</label><input id="rows" type="number" min="200" max="6000" value="3000"></div>
        <button id="loadBtn" onclick="loadData()">获取数据并绘图</button>
      </div>
    </section>

    <div id="status" class="status">请点击“获取数据并绘图”。如果默认 M1 代码或字段无法取数，请按你 Excel 中 N27/N25 的实际值替换。</div>

    <section class="run-status">
      <div class="card">
        <div class="metric-label">运行状态</div>
        <div id="currentStep" class="step-title">等待开始</div>
        <div id="elapsed" class="step-meta">耗时：0 秒</div>
        <div id="taskId" class="step-meta">任务：--</div>
      </div>
      <div class="card">
        <div class="metric-label">运行日志</div>
        <div id="logBox" class="log-box">暂无日志</div>
      </div>
    </section>

    <section class="cards">
      <div class="card"><div class="metric-label">最新 M1</div><div id="latestM1" class="metric-value">--</div><div id="latestM1Date" class="metric-sub">--</div></div>
      <div class="card"><div class="metric-label">最新 Wind 全A</div><div id="latestAllA" class="metric-value">--</div><div id="latestAllADate" class="metric-sub">--</div></div>
      <div class="card"><div class="metric-label">M1 样本</div><div id="m1Count" class="metric-value">--</div><div id="m1Range" class="metric-sub">--</div></div>
      <div class="card"><div class="metric-label">对齐后月频样本</div><div id="allACount" class="metric-value">--</div><div id="allARange" class="metric-sub">--</div></div>
    </section>

    <section class="card chart-card">
      <div class="chart-wrap"><canvas id="mainChart"></canvas></div>
    </section>

    <section class="analysis-grid">
      <div class="card">
        <h3 style="margin-top:0;">领先性结论</h3>
        <div id="leadConclusion" class="conclusion">等待计算</div>
        <div id="leadDetails" class="analysis-note">将比较 M1 环比/同比变化与全A未来收益的相关性。</div>
      </div>
      <div class="card">
        <h3 style="margin-top:0;">最佳领先指标</h3>
        <div id="bestLead" class="metric-value">--</div>
        <div id="bestLeadSub" class="metric-sub">--</div>
      </div>
    </section>

    <section class="card" style="margin-bottom:16px;">
      <h3 style="margin-top:0;">滞后相关分析</h3>
      <div class="table-wrap">
        <table>
          <thead><tr><th>领先月数</th><th>M1水平</th><th>M1月度变化</th><th>M1同比变化</th><th>样本数</th></tr></thead>
          <tbody id="leadRows"></tbody>
        </table>
      </div>
    </section>

    <section class="formula-grid">
      <div class="card"><h3 style="margin-top:0;">M1 WSD 公式</h3><pre id="m1Formula">--</pre></div>
      <div class="card"><h3 style="margin-top:0;">全A WSD 公式</h3><pre id="allAFormula">--</pre></div>
    </section>

    <section class="card" style="margin-top:16px;">
      <h3 style="margin-top:0;">合并后的最近数据</h3>
      <div class="table-wrap">
        <table>
          <thead><tr><th>M1日期</th><th>M1</th><th>全A收盘价</th><th>全A交易日</th><th>M1归一化</th><th>全A归一化</th></tr></thead>
          <tbody id="recentRows"></tbody>
        </table>
      </div>
    </section>
  </div>

  <script>
    let chart = null;
    let pollTimer = null;

    function fmt(value, digits = 2) {
      if (value === null || value === undefined || Number.isNaN(Number(value))) return '--';
      return Number(value).toFixed(digits);
    }

    function setStatus(text, isError = false) {
      const el = document.getElementById('status');
      el.textContent = text;
      el.className = isError ? 'status error' : 'status';
    }

    async function loadData() {
      const btn = document.getElementById('loadBtn');
      const m1Code = document.getElementById('m1Code').value || 'M0001383';
      const m1Field = document.getElementById('m1Field').value || 'close';
      const years = document.getElementById('years').value || '10';
      const rows = document.getElementById('rows').value || '3000';
      btn.disabled = true;
      setStatus('任务已提交，正在启动后台取数...');
      document.getElementById('currentStep').textContent = '正在提交任务';
      document.getElementById('elapsed').textContent = '耗时：0 秒';
      document.getElementById('taskId').textContent = '任务：--';
      document.getElementById('logBox').textContent = '正在提交任务...';

      try {
        const url = `/api/start?m1_code=${encodeURIComponent(m1Code)}&m1_field=${encodeURIComponent(m1Field)}&years=${encodeURIComponent(years)}&rows=${encodeURIComponent(rows)}`;
        const resp = await fetch(url);
        const data = await resp.json();
        if (!resp.ok || !data.ok) throw new Error(data.error || '任务启动失败');
        document.getElementById('taskId').textContent = `任务：${data.task_id}`;
        startPolling();
      } catch (err) {
        setStatus(`获取失败：${err.message}`, true);
        btn.disabled = false;
      }
    }

    function startPolling() {
      if (pollTimer) clearInterval(pollTimer);
      pollStatus();
      pollTimer = setInterval(pollStatus, 1000);
    }

    async function pollStatus() {
      try {
        const resp = await fetch('/api/status');
        const data = await resp.json();
        updateRunStatus(data);

        if (data.done) {
          clearInterval(pollTimer);
          pollTimer = null;
          document.getElementById('loadBtn').disabled = false;
          if (data.ok && data.result) {
            renderSummary(data.result.summary);
            renderChart(data.result.series);
            renderLeadAnalysis(data.result.analysis);
            renderRecent(data.result.series.slice(-30));
            document.getElementById('m1Formula').textContent = data.result.formulas.m1;
            document.getElementById('allAFormula').textContent = data.result.formulas.all_a;
            setStatus(`数据获取成功：M1 ${data.result.summary.m1.count} 条，全A ${data.result.summary.all_a.count} 条，合并 ${data.result.series.length} 条。`);
          } else {
            setStatus(`获取失败：${data.error || '未知错误'}`, true);
          }
        }
      } catch (err) {
        setStatus(`状态查询失败：${err.message}`, true);
        clearInterval(pollTimer);
        pollTimer = null;
        document.getElementById('loadBtn').disabled = false;
      }
    }

    function updateRunStatus(data) {
      document.getElementById('currentStep').textContent = data.current_step || '未知状态';
      document.getElementById('elapsed').textContent = `耗时：${fmt(data.elapsed || 0, 1)} 秒`;
      document.getElementById('taskId').textContent = `任务：${data.task_id || '--'}`;
      const logs = data.logs && data.logs.length ? data.logs.join('\\n') : '暂无日志';
      const logBox = document.getElementById('logBox');
      logBox.textContent = logs;
      logBox.scrollTop = logBox.scrollHeight;
      if (data.running) {
        setStatus(`正在运行：${data.current_step || '处理中'}，已耗时 ${fmt(data.elapsed || 0, 1)} 秒。`);
      }
    }

    function renderSummary(summary) {
      document.getElementById('latestM1').textContent = fmt(summary.m1.latest_value, 2);
      document.getElementById('latestM1Date').textContent = `日期：${summary.m1.latest_date}`;
      document.getElementById('latestAllA').textContent = fmt(summary.all_a.latest_value, 2);
      document.getElementById('latestAllADate').textContent = `日期：${summary.all_a.latest_date}`;
      document.getElementById('m1Count').textContent = `${summary.m1.count} 条`;
      document.getElementById('m1Range').textContent = `${summary.m1.start_date} 至 ${summary.m1.latest_date}`;
      document.getElementById('allACount').textContent = `${summary.all_a.count} 条`;
      document.getElementById('allARange').textContent = `${summary.all_a.start_date} 至 ${summary.all_a.latest_date}`;
    }

    function renderChart(series) {
      const labels = series.map(x => x.date);
      const m1Raw = series.map(x => x.m1);
      const allARaw = series.map(x => x.all_a_close);
      const m1Norm = series.map(x => x.m1_norm);
      const allANorm = series.map(x => x.all_a_norm);
      const ctx = document.getElementById('mainChart');
      if (chart) chart.destroy();
      chart = new Chart(ctx, {
        type: 'line',
        data: {
          labels,
          datasets: [
            { label: 'M1 归一化(首期=100)', data: m1Norm, yAxisID: 'yNorm', borderColor: '#dc2626', backgroundColor: 'rgba(220,38,38,0.08)', borderWidth: 2.2, pointRadius: 0, tension: 0.18 },
            { label: 'Wind全A 归一化(首期=100)', data: allANorm, yAxisID: 'yNorm', borderColor: '#2563eb', backgroundColor: 'rgba(37,99,235,0.08)', borderWidth: 2.2, pointRadius: 0, tension: 0.18 },
            { label: 'M1 原始值', data: m1Raw, yAxisID: 'yM1', borderColor: 'rgba(220,38,38,0.35)', borderWidth: 1, pointRadius: 0, hidden: true },
            { label: '全A收盘价', data: allARaw, yAxisID: 'yAllA', borderColor: 'rgba(37,99,235,0.35)', borderWidth: 1, pointRadius: 0, hidden: true }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          interaction: { mode: 'index', intersect: false },
          plugins: {
            legend: { position: 'top' },
            title: { display: true, text: 'M1 与 Wind 全A指数同图对比' },
            tooltip: {
              callbacks: {
                label: ctx => `${ctx.dataset.label}: ${fmt(ctx.parsed.y, 2)}`
              }
            }
          },
          scales: {
            x: { ticks: { maxTicksLimit: 12 }, grid: { display: false } },
            yNorm: { type: 'linear', position: 'left', title: { display: true, text: '归一化指数' } },
            yM1: { type: 'linear', position: 'right', display: false, grid: { drawOnChartArea: false } },
            yAllA: { type: 'linear', position: 'right', display: false, grid: { drawOnChartArea: false } }
          }
        }
      });
    }

    function renderLeadAnalysis(analysis) {
      if (!analysis || !analysis.best) {
        document.getElementById('leadConclusion').textContent = '样本不足，无法判断';
        document.getElementById('leadDetails').textContent = '至少需要较长月频样本，建议回看 8-10 年。';
        document.getElementById('bestLead').textContent = '--';
        document.getElementById('bestLeadSub').textContent = '--';
        document.getElementById('leadRows').innerHTML = '';
        return;
      }
      document.getElementById('leadConclusion').textContent = analysis.conclusion;
      document.getElementById('leadDetails').textContent = analysis.detail;
      document.getElementById('bestLead').textContent = `${analysis.best.months} 个月`;
      document.getElementById('bestLeadSub').textContent = `${analysis.best.metric} 相关系数 ${fmt(analysis.best.correlation, 3)}，样本 ${analysis.best.count} 个`;
      const rows = analysis.lead_correlations || [];
      document.getElementById('leadRows').innerHTML = rows.map(row => `
        <tr>
          <td>${row.months}</td>
          <td>${fmt(row.m1_level_corr, 3)}</td>
          <td>${fmt(row.m1_mom_corr, 3)}</td>
          <td>${fmt(row.m1_yoy_corr, 3)}</td>
          <td>${row.count}</td>
        </tr>
      `).join('');
    }

    function renderRecent(rows) {
      const tbody = document.getElementById('recentRows');
      tbody.innerHTML = rows.reverse().map(row => `
        <tr>
          <td>${row.date}</td>
          <td>${fmt(row.m1, 2)}</td>
          <td>${fmt(row.all_a_close, 2)}</td>
          <td>${row.all_a_date || '--'}</td>
          <td>${fmt(row.m1_norm, 2)}</td>
          <td>${fmt(row.all_a_norm, 2)}</td>
        </tr>
      `).join('');
    }
  </script>
</body>
</html>
"""


def _build_wsd_formula(code, field, start_date, end_date, rows):
    return (
        f'=WSD("{code}","{field}","{start_date}","{end_date}",'
        f'"TradingCalendar=SSE","ShowParams=Y","cols=1;rows={rows}")'
    )


def _build_m1_wsd_formula(code, field, start_date, end_date, rows):
    return (
        f'=WSD("{code}","{field}","{start_date}","{end_date}",'
        f'"TradingCalendar=SSE","PriceAdj=","rptType=1","Version=1",'
        f'"ShowParams=Y","cols=1;rows={rows}")'
    )


def _looks_like_date(value):
    if value in (None, ""):
        return False
    if hasattr(value, "year") and hasattr(value, "month") and hasattr(value, "day"):
        return True
    try:
        return pd.notna(pd.to_datetime(value, errors="coerce"))
    except Exception:
        return False


def _looks_like_number(value):
    if value in (None, ""):
        return False
    try:
        return pd.notna(pd.to_numeric(value, errors="coerce"))
    except Exception:
        return False


def _fetch_m1_formula_from_b1(formula, timeout=120, interval=0.5, visible=False):
    excel = wb = ws = None
    try:
        excel, wb, ws = _create_excel_session(visible=visible)
        ws.Cells.Clear()
        ws.Range("B1").Formula = formula
        start_time = time.time()
        while True:
            try:
                excel.Calculate()
            except Exception:
                pass
            raw = ws.Range("A1:B5000").Value
            matrix = _normalize_used_range(raw)
            has_date = False
            has_value = False
            for row in matrix:
                if not row:
                    continue
                if len(row) > 0 and _looks_like_date(row[0]):
                    has_date = True
                if len(row) > 1 and _looks_like_number(row[1]):
                    has_value = True
                if has_date and has_value:
                    break
            if has_date and has_value:
                break
            if time.time() - start_time > timeout:
                raise TimeoutError(f"M1 WSD 数据加载超时({timeout}s): {formula[:80]}...")
            time.sleep(interval)

        matrix = _normalize_used_range(ws.Range("A1:B5000").Value)
        normalized = [
            row + [None] * (2 - len(row))
            for row in matrix
            if row and any(value not in (None, "") for value in row)
        ]
        converted = [
            [_convert_pywintypes(value) for value in row[:2]]
            for row in normalized
        ]
        df = pd.DataFrame(converted, columns=[0, 1], dtype=object)
        return df
    finally:
        _close_excel_session(excel, wb, ws)


def _build_fallback_dates(start_date, periods, freq="business_day"):
    start_ts = pd.to_datetime(start_date)
    if freq == "month_end":
        first_date = start_ts + pd.offsets.MonthEnd(0)
        return pd.date_range(start=first_date, periods=periods, freq="ME")
    return pd.bdate_range(start=start_ts, periods=periods)


def _parse_single_series(raw_df, value_name, start_date, min_rows=1, fallback_freq="business_day"):
    if raw_df is None or raw_df.empty:
        return pd.DataFrame(columns=["date", value_name])

    df = raw_df.copy()
    date_col = None
    value_col = None

    for col in df.columns:
        parsed = pd.to_datetime(df[col], errors="coerce")
        if parsed.notna().sum() >= min_rows:
            date_col = col
            break

    for col in df.columns:
        if col == date_col:
            continue
        numeric = pd.to_numeric(df[col], errors="coerce")
        if numeric.notna().sum() >= min_rows:
            value_col = col
            break

    if date_col is not None and value_col is not None:
        result = pd.DataFrame({
            "date": pd.to_datetime(df[date_col], errors="coerce"),
            value_name: pd.to_numeric(df[value_col], errors="coerce"),
        })
    else:
        values = []
        for col in df.columns:
            series = pd.to_numeric(df[col], errors="coerce").dropna()
            if not series.empty:
                values.extend(series.tolist())
        result = pd.DataFrame({
            "date": _build_fallback_dates(start_date, len(values), freq=fallback_freq),
            value_name: values,
        })

    result = result.dropna(subset=["date", value_name]).sort_values("date").reset_index(drop=True)
    return result


def _normalize(series):
    series = pd.to_numeric(series, errors="coerce")
    valid = series.dropna()
    if valid.empty or valid.iloc[0] == 0:
        return pd.Series([None] * len(series), index=series.index)
    return series / valid.iloc[0] * 100


def _align_all_a_to_m1_monthly(all_a_df, m1_df):
    all_a = all_a_df.sort_values("date").drop_duplicates("date", keep="last").copy()
    m1 = m1_df.sort_values("date").drop_duplicates("date", keep="last").copy()
    all_a["all_a_date"] = all_a["date"]
    merged = pd.merge_asof(
        m1,
        all_a[["date", "all_a_close", "all_a_date"]],
        on="date",
        direction="backward",
    ).dropna(subset=["m1", "all_a_close"]).reset_index(drop=True)
    return merged


def _safe_corr(left, right):
    pair = pd.concat([left, right], axis=1).dropna()
    pair = pair.replace([float("inf"), float("-inf")], pd.NA).dropna()
    if len(pair) < 12:
        return None, int(len(pair))
    if pair.iloc[:, 0].std() == 0 or pair.iloc[:, 1].std() == 0:
        return None, int(len(pair))
    corr = pair.iloc[:, 0].corr(pair.iloc[:, 1])
    if pd.isna(corr):
        return None, int(len(pair))
    return float(corr), int(len(pair))


def _analyze_leadership(merged):
    df = merged.copy()
    df["m1_level"] = df["m1"]
    df["m1_mom_diff"] = df["m1"].diff()
    df["m1_yoy_diff"] = df["m1"].diff(12)
    rows = []
    candidates = []

    for months in range(1, 13):
        future_return = df["all_a_close"].shift(-months) / df["all_a_close"] - 1
        level_corr, level_count = _safe_corr(df["m1_level"], future_return)
        mom_corr, mom_count = _safe_corr(df["m1_mom_diff"], future_return)
        yoy_corr, yoy_count = _safe_corr(df["m1_yoy_diff"], future_return)
        count = max(level_count, mom_count, yoy_count)
        rows.append({
            "months": months,
            "m1_level_corr": round(level_corr, 4) if level_corr is not None else None,
            "m1_mom_corr": round(mom_corr, 4) if mom_corr is not None else None,
            "m1_yoy_corr": round(yoy_corr, 4) if yoy_corr is not None else None,
            "count": count,
        })
        if level_corr is not None:
            candidates.append({"months": months, "metric": "M1水平", "correlation": level_corr, "count": level_count})
        if mom_corr is not None:
            candidates.append({"months": months, "metric": "M1月度变化", "correlation": mom_corr, "count": mom_count})
        if yoy_corr is not None:
            candidates.append({"months": months, "metric": "M1同比变化", "correlation": yoy_corr, "count": yoy_count})

    if not candidates:
        return {
            "best": None,
            "lead_correlations": rows,
            "conclusion": "样本不足，暂时无法判断领先性",
            "detail": "相关性计算至少需要较长月频样本。建议回看 8-10 年以上。",
        }

    best = max(candidates, key=lambda item: abs(item["correlation"]))
    corr_abs = abs(best["correlation"])
    if corr_abs >= 0.35:
        strength = "较明显"
    elif corr_abs >= 0.2:
        strength = "偏弱"
    else:
        strength = "不明显"

    direction = "正相关" if best["correlation"] > 0 else "负相关"
    conclusion = f"M1领先性{strength}：最佳为{best['metric']}领先{best['months']}个月，{direction} {best['correlation']:.3f}"
    detail = (
        "该结果基于月频样本的滞后相关，不代表稳定因果关系。"
        "如果相关性较低，说明肉眼看到的同步走势可能多于可量化领先关系。"
    )

    best_display = {
        "months": int(best["months"]),
        "metric": best["metric"],
        "correlation": round(float(best["correlation"]), 4),
        "count": int(best["count"]),
    }
    return {
        "best": best_display,
        "lead_correlations": rows,
        "conclusion": conclusion,
        "detail": detail,
    }


def _task_snapshot():
    with TASK_LOCK:
        snapshot = dict(TASK_STATE)
        snapshot["logs"] = list(TASK_STATE["logs"])
    if snapshot["started_at"] is not None and snapshot["running"]:
        snapshot["elapsed"] = time.time() - snapshot["started_at"]
    return snapshot


def _task_log(message, step=None):
    with TASK_LOCK:
        if step is not None:
            TASK_STATE["current_step"] = step
        timestamp = datetime.now().strftime("%H:%M:%S")
        TASK_STATE["logs"].append(f"[{timestamp}] {message}")
        TASK_STATE["logs"] = TASK_STATE["logs"][-120:]


def _task_reset(task_id):
    now = time.time()
    with TASK_LOCK:
        TASK_STATE.update({
            "task_id": task_id,
            "running": True,
            "done": False,
            "ok": False,
            "error": None,
            "current_step": "初始化任务",
            "started_at": now,
            "ended_at": None,
            "elapsed": 0,
            "logs": [],
            "result": None,
        })


def _task_finish(ok, result=None, error=None):
    now = time.time()
    with TASK_LOCK:
        TASK_STATE.update({
            "running": False,
            "done": True,
            "ok": ok,
            "error": error,
            "ended_at": now,
            "elapsed": now - TASK_STATE["started_at"] if TASK_STATE["started_at"] else 0,
            "result": result,
            "current_step": "完成" if ok else "失败",
        })


def fetch_m1_all_a_data(m1_code=DEFAULT_M1_CODE, m1_field=DEFAULT_M1_FIELD,
                        years=DEFAULT_YEARS, rows=3000, status_callback=None):
    def report(message, step=None):
        if status_callback is not None:
            status_callback(message, step)

    report("检查 Wind Excel 插件环境", "检查环境")
    if not is_wind_available():
        raise RuntimeError("Wind Excel 插件不可用，或当前环境缺少 win32com/pythoncom")

    report("Wind Excel 插件环境可用", "准备参数")
    years = max(1, min(int(years), 20))
    rows = max(200, min(int(rows), 6000))
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=365 * years + 30)).strftime("%Y-%m-%d")
    m1_rows = max(120, years * 14)

    all_a_formula = _build_wsd_formula(DEFAULT_ALL_A_CODE, DEFAULT_ALL_A_FIELD, start_date, end_date, rows)
    m1_formula = _build_m1_wsd_formula(m1_code, m1_field, start_date, end_date, m1_rows)

    report(f"获取 Wind 全A指数：{DEFAULT_ALL_A_CODE} {DEFAULT_ALL_A_FIELD}", "获取全A指数")
    report(f"全A公式：{all_a_formula}")
    raw_all_a = fetch_wind_formula(all_a_formula, timeout=120, interval=0.5, visible=False)
    report(f"全A指数原始返回形状：{raw_all_a.shape}", "获取 M1")
    report(f"获取 M1：{m1_code} {m1_field}", "获取 M1")
    report(f"M1公式：{m1_formula}")
    raw_m1 = _fetch_m1_formula_from_b1(m1_formula, timeout=120, interval=0.5, visible=False)
    report(f"M1 原始返回形状：{raw_m1.shape}", "解析数据")

    all_a_df = _parse_single_series(raw_all_a, "all_a_close", start_date, min_rows=20)
    m1_df = _parse_single_series(raw_m1, "m1", start_date, min_rows=2, fallback_freq="month_end")
    report(f"解析完成：全A {len(all_a_df)} 条，M1 {len(m1_df)} 条", "校验数据")

    if len(all_a_df) < 20:
        raise RuntimeError(f"Wind 全A指数有效数据不足，当前仅 {len(all_a_df)} 条")
    if len(m1_df) < 2:
        raise RuntimeError(f"M1 有效数据不足，当前仅 {len(m1_df)} 条。请确认 M1 代码和字段是否正确：{m1_code}, {m1_field}")

    merged = _align_all_a_to_m1_monthly(all_a_df, m1_df)

    if merged.empty:
        raise RuntimeError("M1 与 Wind 全A指数日期无法对齐")

    report(f"按 M1 月末日期对齐完成：合并 {len(merged)} 条", "生成图表数据")
    analysis = _analyze_leadership(merged)
    merged["m1_norm"] = _normalize(merged["m1"])
    merged["all_a_norm"] = _normalize(merged["all_a_close"])

    series = []
    for _, row in merged.iterrows():
        series.append({
            "date": row["date"].strftime("%Y-%m-%d"),
            "m1": round(float(row["m1"]), 4),
            "all_a_close": round(float(row["all_a_close"]), 4),
            "all_a_date": row["all_a_date"].strftime("%Y-%m-%d") if pd.notna(row["all_a_date"]) else None,
            "m1_norm": round(float(row["m1_norm"]), 4) if pd.notna(row["m1_norm"]) else None,
            "all_a_norm": round(float(row["all_a_norm"]), 4) if pd.notna(row["all_a_norm"]) else None,
        })

    summary = {
        "m1": {
            "code": m1_code,
            "field": m1_field,
            "count": int(len(m1_df)),
            "start_date": m1_df.iloc[0]["date"].strftime("%Y-%m-%d"),
            "latest_date": m1_df.iloc[-1]["date"].strftime("%Y-%m-%d"),
            "latest_value": float(m1_df.iloc[-1]["m1"]),
        },
        "all_a": {
            "code": DEFAULT_ALL_A_CODE,
            "field": DEFAULT_ALL_A_FIELD,
            "count": int(len(merged)),
            "start_date": merged.iloc[0]["date"].strftime("%Y-%m-%d"),
            "latest_date": merged.iloc[-1]["date"].strftime("%Y-%m-%d"),
            "latest_value": float(merged.iloc[-1]["all_a_close"]),
        },
        "merged_count": int(len(merged)),
    }
    return {
        "summary": summary,
        "series": series,
        "analysis": analysis,
        "formulas": {
            "m1": m1_formula,
            "all_a": all_a_formula,
        },
    }


def _run_task(params):
    try:
        _task_log("后台任务启动", "初始化任务")
        result = fetch_m1_all_a_data(
            m1_code=params["m1_code"],
            m1_field=params["m1_field"],
            years=params["years"],
            rows=params["rows"],
            status_callback=_task_log,
        )
        _task_log("数据获取与整理完成", "完成")
        _task_finish(True, result=result)
    except Exception as exc:
        _task_log(f"任务失败：{exc}", "失败")
        _task_finish(False, error=str(exc))


@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/api/data")
def api_data():
    try:
        result = fetch_m1_all_a_data(
            m1_code=request.args.get("m1_code", DEFAULT_M1_CODE),
            m1_field=request.args.get("m1_field", DEFAULT_M1_FIELD),
            years=request.args.get("years", DEFAULT_YEARS, type=int),
            rows=request.args.get("rows", 3000, type=int),
        )
        return jsonify({"ok": True, **result})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.route("/api/start")
def api_start():
    with TASK_LOCK:
        if TASK_STATE["running"]:
            return jsonify({
                "ok": False,
                "error": f"已有任务正在运行：{TASK_STATE['current_step']}",
                "task_id": TASK_STATE["task_id"],
            }), 409

    task_id = uuid.uuid4().hex[:12]
    params = {
        "m1_code": request.args.get("m1_code", DEFAULT_M1_CODE),
        "m1_field": request.args.get("m1_field", DEFAULT_M1_FIELD),
        "years": request.args.get("years", DEFAULT_YEARS, type=int),
        "rows": request.args.get("rows", 3000, type=int),
    }
    _task_reset(task_id)
    thread = threading.Thread(target=_run_task, args=(params,), daemon=True)
    thread.start()
    return jsonify({"ok": True, "task_id": task_id})


@app.route("/api/status")
def api_status():
    return jsonify(_task_snapshot())


def main():
    parser = argparse.ArgumentParser(description="M1 与 Wind 全A指数 Web 展示")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=7794)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    app.run(host=args.host, port=args.port, debug=args.debug, use_reloader=False)


if __name__ == "__main__":
    main()
