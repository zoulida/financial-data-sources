#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations


def render_index_html() -> str:
    return """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>主升浪事件 GA 挖掘器</title>
<style>
body { font-family:-apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", sans-serif; margin:0; padding:20px; background:#f5f7fb; color:#222; }
h1 { margin:0 0 14px; font-size:22px; }
.container { display:grid; grid-template-columns:minmax(460px, 620px) 1fr; gap:16px; }
fieldset { background:#fff; border:1px solid #dfe4ef; border-radius:10px; padding:14px 16px; margin-bottom:14px; }
legend { font-weight:700; padding:0 6px; }
.row { display:flex; flex-wrap:wrap; gap:10px; align-items:flex-end; margin-bottom:8px; }
label { display:flex; flex-direction:column; font-size:12px; color:#555; }
label > span { margin-bottom:4px; }
input, select { border:1px solid #cfd7e6; border-radius:6px; padding:6px 8px; min-width:118px; font-size:13px; }
input[type="checkbox"] { min-width:auto; }
button { background:#1f8a70; color:white; border:0; border-radius:7px; padding:8px 16px; cursor:pointer; }
button:disabled { background:#9aa8bd; cursor:not-allowed; }
pre { background:#111827; color:#d1d5db; padding:12px; border-radius:10px; min-height:340px; max-height:620px; overflow:auto; white-space:pre-wrap; }
table { width:100%; border-collapse:collapse; font-size:12px; background:#fff; }
th, td { border-bottom:1px solid #edf0f5; padding:6px 8px; text-align:left; vertical-align:top; }
th { background:#eef3fb; }
.panel { background:#fff; border:1px solid #dfe4ef; border-radius:10px; padding:14px 16px; margin-bottom:14px; }
.status { display:inline-block; border-radius:999px; padding:3px 10px; font-size:12px; background:#eef3fb; }
.status.run { background:#fff4d6; color:#946200; }
.status.ok { background:#e8f7ee; color:#147a3d; }
.status.err { background:#fdeaea; color:#bd2c2c; }
.hint { color:#777; font-size:12px; line-height:1.6; }
img { max-width:100%; border:1px solid #edf0f5; border-radius:8px; margin:6px 0; }
</style>
</head>
<body>
<h1>🌊 主升浪事件序列 GA 挖掘器 <span class="hint">事件库 → 启动/中继标签 → 顺序组合进化 → 因子入库回测</span></h1>
<div class="container">
<form id="cfg-form" onsubmit="event.preventDefault(); return false;">
  <fieldset><legend>1. 数据区间</legend>
    <div class="row">
      <label><span>provider_uri</span><input name="provider_uri" type="text" style="min-width:380px"></label>
      <label><span>market</span><input name="market" type="text"></label>
      <label><span>benchmark</span><input name="benchmark" type="text"></label>
    </div>
    <div class="row">
      <label><span>start_time</span><input name="start_time" type="text"></label>
      <label><span>end_time</span><input name="end_time" type="text"></label>
      <label><span>train_end_time</span><input name="train_end_time" type="text"></label>
      <label><span>valid_end_time</span><input name="valid_end_time" type="text"></label>
      <label><span>test_start_time</span><input name="test_start_time" type="text"></label>
    </div>
  </fieldset>

  <fieldset><legend>2. 主升浪标签</legend>
    <div class="row">
      <label><span>label_mode</span><select name="label_mode"><option value="all">all</option><option value="start">start</option><option value="continuation">continuation</option></select></label>
      <label><span>启动 horizon</span><input name="label_horizon" type="number" min="2"></label>
      <label><span>中继 horizon</span><input name="continuation_horizon" type="number" min="2"></label>
      <label><span>启动最小涨幅</span><input name="start_min_return" type="number" step="0.01"></label>
      <label><span>中继最小涨幅</span><input name="continuation_min_return" type="number" step="0.01"></label>
    </div>
    <div class="row">
      <label><span>最大回撤下限</span><input name="label_max_drawdown" type="number" step="0.01"></label>
      <label><span>5日失败收益</span><input name="fail_return_5d" type="number" step="0.01"></label>
      <label><span>失败回撤</span><input name="fail_drawdown" type="number" step="0.01"></label>
    </div>
  </fieldset>

  <fieldset><legend>3. 基础事件阈值</legend>
    <div class="row">
      <label><span>涨停阈值</span><input name="limit_up_threshold" type="number" step="0.005"></label>
      <label><span>近涨停阈值</span><input name="near_limit_up_threshold" type="number" step="0.005"></label>
      <label><span>大涨阈值</span><input name="big_up_threshold" type="number" step="0.005"></label>
      <label><span>大跌阈值</span><input name="big_down_threshold" type="number" step="0.005"></label>
    </div>
    <div class="row">
      <label><span>放量倍数</span><input name="volume_surge_ratio" type="number" step="0.1"></label>
      <label><span>缩量倍数</span><input name="shrink_volume_ratio" type="number" step="0.05"></label>
      <label><span>触发阈值</span><input name="event_trigger_threshold" type="number" step="0.05"></label>
    </div>
  </fieldset>

  <fieldset><legend>4. GA 进化参数</legend>
    <div class="row">
      <label><span>种群规模</span><input name="population_size" type="number" min="5"></label>
      <label><span>最大代数</span><input name="generations" type="number" min="1"></label>
      <label><span>最大深度</span><input name="max_depth" type="number" min="1"></label>
      <label><span>最大节点数</span><input name="max_nodes" type="number" min="3"></label>
    </div>
    <div class="row">
      <label><span>交叉率</span><input name="crossover_rate" type="number" step="0.05" min="0" max="1"></label>
      <label><span>变异率</span><input name="mutation_rate" type="number" step="0.05" min="0" max="1"></label>
      <label><span>精英保留</span><input name="elite_keep" type="number" min="1"></label>
      <label><span>每代 elite</span><input name="generation_elite_k" type="number" min="1"></label>
      <label><span>早停轮数</span><input name="early_stop_rounds" type="number" min="1"></label>
    </div>
    <div class="row">
      <label><span>窗口集合</span><input name="window_choices" type="text" placeholder="3,5,10,20,30,60"></label>
      <label><span>顺序 gap 集合</span><input name="sequence_gap_choices" type="text" placeholder="1,2,3,5,10"></label>
      <label><span>COUNT 阈值</span><input name="count_threshold_choices" type="text" placeholder="1,2,3"></label>
      <label><span>模板注入比例</span><input name="template_injection_ratio" type="number" step="0.05"></label>
      <label><span>随机种子</span><input name="random_seed" type="number"></label>
    </div>
  </fieldset>

  <fieldset><legend>5. 过滤 / 回测 / 导出</legend>
    <div class="row">
      <label><span>最小样本数</span><input name="min_event_support" type="number" min="1"></label>
      <label><span>最小覆盖率</span><input name="min_event_coverage" type="number" step="0.001"></label>
      <label><span>最大覆盖率</span><input name="max_event_coverage" type="number" step="0.01"></label>
      <label><span>Jaccard 上限</span><input name="jaccard_max" type="number" step="0.05"></label>
      <label><span>最终导出数</span><input name="export_topk" type="number" min="1"></label>
    </div>
    <div class="row">
      <label><span>topn</span><input name="topn" type="number" min="1"></label>
      <label><span>holding_period</span><input name="holding_period" type="number" min="1"></label>
      <label><span>信号模式</span><select name="signal_mode"><option value="all">规则+LightGBM</option><option value="ml">仅 LightGBM</option><option value="traditional">仅规则</option></select></label>
      <label><span>ML 模型</span><input name="ml_model" type="text" placeholder="lightgbm"></label>
      <label><span><input name="backtest_test_period_only" type="checkbox"> 仅测试期绩效</span></label>
      <label><span><input name="enable_price_filter" type="checkbox"> 股价过滤</span></label>
      <label><span><input name="enable_market_cap_filter" type="checkbox"> 市值过滤</span></label>
    </div>
  </fieldset>

  <button id="btn-run" type="submit">▶ 启动主升浪事件 GA</button>
</form>

<div>
  <div class="panel">
    <h3>运行状态 <span id="status" class="status">空闲</span></h3>
    <pre id="logs">等待运行...</pre>
  </div>
  <div class="panel">
    <h3>结果摘要</h3>
    <div id="results">尚无结果。</div>
  </div>
  <div class="panel">
    <h3>Top Elite 事件序列</h3>
    <div id="elite">尚无数据。</div>
  </div>
  <div class="panel">
    <h3>图表</h3>
    <div id="figs" class="hint">尚无图片。</div>
  </div>
</div>
</div>

<script>
const form = document.getElementById('cfg-form');
const btn = document.getElementById('btn-run');
const statusEl = document.getElementById('status');
const logsEl = document.getElementById('logs');
const resultsEl = document.getElementById('results');
const eliteEl = document.getElementById('elite');
const figsEl = document.getElementById('figs');
const DEFAULT_CONFIG = {
  provider_uri: 'd:/pythonProject/sdufe-qlib/source/qlib-data数据下载/cn_data',
  market: 'all',
  benchmark: 'SH000300',
  start_time: '2024-11-01',
  end_time: '2026-04-30',
  train_end_time: '2025-09-24',
  valid_end_time: '2026-01-09',
  test_start_time: '2026-01-12',
  label_mode: 'all',
  label_horizon: 20,
  continuation_horizon: 10,
  start_min_return: 0.18,
  continuation_min_return: 0.06,
  label_max_drawdown: -0.12,
  fail_return_5d: -0.06,
  fail_drawdown: -0.15,
  limit_up_threshold: 0.095,
  near_limit_up_threshold: 0.075,
  big_up_threshold: 0.045,
  big_down_threshold: -0.045,
  volume_surge_ratio: 1.8,
  shrink_volume_ratio: 0.8,
  event_trigger_threshold: 0.5,
  population_size: 60,
  generations: 20,
  max_depth: 5,
  max_nodes: 28,
  crossover_rate: 0.7,
  mutation_rate: 0.25,
  elite_keep: 6,
  generation_elite_k: 12,
  early_stop_rounds: 6,
  window_choices: [3,5,10,20,30,60],
  sequence_gap_choices: [1,2,3,5,10],
  count_threshold_choices: [1,2,3],
  template_injection_ratio: 0.35,
  random_seed: 20260522,
  min_event_support: 200,
  min_event_coverage: 0.001,
  max_event_coverage: 0.25,
  jaccard_max: 0.8,
  export_topk: 10,
  topn: 50,
  holding_period: 10,
  signal_mode: 'all',
  ml_model: ['lightgbm'],
  backtest_test_period_only: true,
  enable_price_filter: true,
  enable_market_cap_filter: true
};

function esc(s) {
  return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
function shortText(s, n) {
  s = String(s == null ? '' : s);
  return s.length > n ? s.slice(0, n) + '…' : s;
}
function fillForm(cfg) {
  cfg = Object.assign({}, DEFAULT_CONFIG, cfg || {});
  for (const [k, v] of Object.entries(cfg)) {
    const el = form.elements.namedItem(k);
    if (!el || v === null || v === undefined || v === '') continue;
    if (el.type === 'checkbox') el.checked = Boolean(v);
    else if (Array.isArray(v)) el.value = v.join(',');
    else el.value = v;
  }
}
function readForm() {
  const data = {};
  for (const el of form.elements) {
    if (!el.name) continue;
    if (el.type === 'checkbox') data[el.name] = el.checked;
    else if (String(el.value).trim() !== '') data[el.name] = el.value;
  }
  return data;
}
function renderResults(r) {
  let html = '';
  if (r.output_dir) html += `<p class="hint">输出目录：${esc(r.output_dir)}</p>`;
  if (r.performance && r.performance.length) {
    html += '<h4>绩效</h4><table><tr><th>signal</th><th>annual</th><th>sharpe</th><th>max_dd</th><th>excess</th></tr>';
    for (const row of r.performance) {
      html += `<tr><td>${esc(row.signal)}</td><td>${((row.annual_return||0)*100).toFixed(2)}%</td><td>${(row.sharpe||0).toFixed(2)}</td><td>${((row.max_drawdown||0)*100).toFixed(2)}%</td><td>${((row.excess_return||0)*100).toFixed(2)}%</td></tr>`;
    }
    html += '</table>';
  }
  if (r.selected_factors && r.selected_factors.length) {
    html += '<h4>入选事件因子</h4><p>' + r.selected_factors.map(esc).join(', ') + '</p>';
  }
  if (r.signal_info) {
    html += '<h4>信号信息</h4><pre style="min-height:80px;max-height:220px;background:#f8fafc;color:#334155;border:1px solid #edf0f5;">' + esc(JSON.stringify(r.signal_info, null, 2)) + '</pre>';
  }
  if (r.exported && r.exported.length) {
    html += '<h4>已导出</h4><table><tr><th>factor</th><th>function</th><th>expression</th></tr>';
    for (const row of r.exported) {
      html += `<tr><td>${esc(row.factor)}</td><td>${esc(row.function)}</td><td title="${esc(row.expression)}">${esc(shortText(row.expression, 120))}</td></tr>`;
    }
    html += '</table>';
  }
  resultsEl.innerHTML = html || '暂无结果。';

  if (r.elite && r.elite.length) {
    let eliteHtml = '<table><tr><th>factor</th><th>fitness</th><th>hit</th><th>uplift</th><th>coverage</th><th>expr</th></tr>';
    for (const row of r.elite.slice(0, 20)) {
      eliteHtml += `<tr><td>${esc(row.factor)}</td><td>${(row.fitness||0).toFixed(4)}</td><td>${((row.hit_rate||0)*100).toFixed(2)}%</td><td>${(row.uplift||0).toFixed(2)}</td><td>${((row.coverage||0)*100).toFixed(2)}%</td><td title="${esc(row.expr_key)}">${esc(shortText(row.expr_key, 100))}</td></tr>`;
    }
    eliteHtml += '</table>';
    eliteEl.innerHTML = eliteHtml;
  }
  let figHtml = '';
  if (r.fitness_url) figHtml += `<h4>Fitness</h4><img src="${r.fitness_url}" alt="fitness">`;
  if (r.cumulative_url) figHtml += `<h4>净值</h4><img src="${r.cumulative_url}" alt="cumulative">`;
  figsEl.innerHTML = figHtml || '尚无图片。';
}

async function loadConfig() {
  try {
    const res = await fetch('/api/config');
    fillForm(await res.json());
  } catch (e) {
    fillForm(DEFAULT_CONFIG);
  }
}
async function poll() {
  try {
    const res = await fetch('/api/status');
    const data = await res.json();
    btn.disabled = Boolean(data.running);
    statusEl.textContent = data.running ? '运行中' : (data.error ? '失败' : '空闲');
    statusEl.className = 'status ' + (data.running ? 'run' : (data.error ? 'err' : 'ok'));
    logsEl.textContent = (data.logs && data.logs.length) ? data.logs.join('\\n') : '等待运行...';
    logsEl.scrollTop = logsEl.scrollHeight;
    if (data.error) {
      resultsEl.innerHTML = `<p style="color:#bd2c2c">${esc(data.error)}</p>`;
    } else if (data.last_results) {
      renderResults(data.last_results);
    }
  } catch (e) {}
  setTimeout(poll, 1500);
}
btn.addEventListener('click', async () => {
  btn.disabled = true;
  resultsEl.textContent = '任务已提交，等待结果...';
  eliteEl.textContent = '等待运行...';
  figsEl.textContent = '等待运行...';
  try {
    const res = await fetch('/api/run', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(readForm())});
    const data = await res.json();
    if (!data.ok) throw new Error(data.error || '启动失败');
  } catch (e) {
    resultsEl.innerHTML = `<p style="color:#bd2c2c">${esc(e.message || e)}</p>`;
    btn.disabled = false;
  }
});
fillForm(DEFAULT_CONFIG);
loadConfig();
poll();
</script>
</body>
</html>"""
