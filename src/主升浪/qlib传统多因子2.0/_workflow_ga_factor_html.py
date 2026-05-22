#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations


def render_index_html() -> str:
    return """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>GA 因子生成工作流</title>
<style>
body { font-family:-apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", sans-serif; margin:0; padding:20px; background:#f5f7fb; color:#222; }
h1 { margin:0 0 14px; font-size:22px; }
.container { display:grid; grid-template-columns: minmax(420px, 560px) 1fr; gap:16px; }
fieldset { background:#fff; border:1px solid #dfe4ef; border-radius:10px; padding:14px 16px; margin-bottom:14px; }
legend { font-weight:700; padding:0 6px; }
.row { display:flex; flex-wrap:wrap; gap:10px; align-items:flex-end; }
label { display:flex; flex-direction:column; font-size:12px; color:#555; }
label > span { margin-bottom:4px; }
input, select { border:1px solid #cfd7e6; border-radius:6px; padding:6px 8px; min-width:120px; font-size:13px; }
input[type="checkbox"] { min-width:auto; }
button { background:#2f6feb; color:white; border:0; border-radius:7px; padding:8px 16px; cursor:pointer; }
button:disabled { background:#9aa8bd; cursor:not-allowed; }
pre { background:#111827; color:#d1d5db; padding:12px; border-radius:10px; min-height:360px; max-height:620px; overflow:auto; white-space:pre-wrap; }
table { width:100%; border-collapse:collapse; font-size:12px; background:#fff; }
th, td { border-bottom:1px solid #edf0f5; padding:6px 8px; text-align:left; }
th { background:#eef3fb; }
.panel { background:#fff; border:1px solid #dfe4ef; border-radius:10px; padding:14px 16px; margin-bottom:14px; }
.status { display:inline-block; border-radius:999px; padding:3px 10px; font-size:12px; background:#eef3fb; }
.status.run { background:#fff4d6; color:#946200; }
.status.ok { background:#e8f7ee; color:#147a3d; }
.status.err { background:#fdeaea; color:#bd2c2c; }
.hint { color:#777; font-size:12px; line-height:1.6; }
</style>
</head>
<body>
<h1>🧬 GA 因子生成工作流 <span class="hint">逐代生成 → 逐代评价 → 逐代进化 → 最终入库回测</span></h1>
<div class="container">
<form id="cfg-form" onsubmit="event.preventDefault(); return false;">
  <fieldset><legend>1. 数据区间</legend>
    <div class="row">
      <label><span>provider_uri</span><input name="provider_uri" type="text" style="min-width:360px"></label>
      <label><span>market</span><input name="market" type="text"></label>
      <label><span>benchmark</span><input name="benchmark" type="text"></label>
    </div>
    <div class="row">
      <label><span>start_time</span><input name="start_time" type="text"></label>
      <label><span>end_time</span><input name="end_time" type="text"></label>
      <label><span>train_end_time</span><input name="train_end_time" type="text"></label>
      <label><span>test_start_time</span><input name="test_start_time" type="text"></label>
    </div>
  </fieldset>

  <fieldset><legend>2. GA 进化参数</legend>
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
    </div>
    <div class="row">
      <label><span>早停轮数</span><input name="early_stop_rounds" type="number" min="1"></label>
      <label><span>窗口集合</span><input name="window_choices" type="text" placeholder="3,5,10,20,30,60"></label>
      <label><span>最终导出数</span><input name="export_topk" type="number" min="1"></label>
      <label><span>随机种子</span><input name="random_seed" type="number"></label>
    </div>
  </fieldset>

  <fieldset><legend>3. 过滤 / 回测</legend>
    <div class="row">
      <label><span>filter_method</span><select name="filter_method"><option value="none">none</option><option value="threshold">threshold</option><option value="topk">topk</option></select></label>
      <label><span>|RankIC mean|</span><input name="filter_rank_ic_min" type="number" step="0.001"></label>
      <label><span>|RankIC IR|</span><input name="filter_rank_ic_ir_min" type="number" step="0.01"></label>
      <label><span>|corr| 最大</span><input name="filter_corr_max" type="number" step="0.05"></label>
    </div>
    <div class="row">
      <label><span>topn</span><input name="topn" type="number" min="1"></label>
      <label><span>holding_period</span><input name="holding_period" type="number" min="1"></label>
      <label><span>signal_mode</span><select name="signal_mode"><option value="traditional">traditional</option><option value="ml">ml</option><option value="all">all</option></select></label>
      <label><span>ml_model</span><input name="ml_model" type="text" placeholder="lightgbm,ridge,lasso"></label>
    </div>
    <div class="row">
      <label><span><input name="filter_use_train_only" type="checkbox"> 训练期评价过滤</span></label>
      <label><span><input name="backtest_test_period_only" type="checkbox"> 仅测试期绩效</span></label>
      <label><span><input name="enable_price_filter" type="checkbox"> 股价过滤</span></label>
      <label><span><input name="enable_market_cap_filter" type="checkbox"> 市值过滤</span></label>
    </div>
  </fieldset>

  <button id="btn-run" type="submit">▶ 启动 GA 工作流</button>
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
    <h3>📜 按代查看</h3>
    <div class="row" style="margin-bottom:8px">
      <label><span>选择代数</span><select id="gen-select"></select></label>
      <span class="hint">每代仅展示 fitness 最高的前 50 个个体</span>
    </div>
    <div id="gen-table" class="hint">尚无数据。</div>
  </div>
  <div class="panel">
    <h3>🌳 最优血缘 (Top 10)</h3>
    <div id="lineage-img" class="hint" style="margin-bottom:10px;">尚无图片。</div>
    <pre id="lineage-top" style="min-height:200px; max-height:420px;">尚无数据。</pre>
  </div>
</div>
</div>

<script>
const form = document.getElementById('cfg-form');
const btn = document.getElementById('btn-run');
const statusEl = document.getElementById('status');
const logsEl = document.getElementById('logs');
const resultsEl = document.getElementById('results');
const DEFAULT_CONFIG = {
  provider_uri: 'd:/pythonProject/sdufe-qlib/source/qlib-data数据下载/cn_data',
  market: 'all',
  benchmark: 'SH000300',
  start_time: '2024-11-01',
  end_time: '2026-04-30',
  train_end_time: '2025-09-24',
  test_start_time: '2026-01-12',
  population_size: 50,
  generations: 20,
  max_depth: 4,
  max_nodes: 24,
  crossover_rate: 0.7,
  mutation_rate: 0.2,
  elite_keep: 5,
  generation_elite_k: 10,
  early_stop_rounds: 5,
  window_choices: [3,5,10,20,30,60],
  export_topk: 10,
  random_seed: 20260520,
  filter_method: 'threshold',
  filter_rank_ic_min: 0.02,
  filter_rank_ic_ir_min: 0.3,
  filter_corr_max: 0.7,
  topn: 50,
  holding_period: 14,
  signal_mode: 'all',
  ml_model: ['lightgbm','ridge','lasso'],
  filter_use_train_only: true,
  backtest_test_period_only: true,
  enable_price_filter: true,
  enable_market_cap_filter: true
};

function fillForm(cfg) {
  cfg = Object.assign({}, DEFAULT_CONFIG, cfg || {});
  for (const [k, v] of Object.entries(cfg)) {
    const el = form.elements.namedItem(k);
    if (!el) continue;
    if (v === null || v === undefined || v === '') continue;
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

const genSelect = document.getElementById('gen-select');
const genTableEl = document.getElementById('gen-table');
const lineageTopEl = document.getElementById('lineage-top');
const lineageImgEl = document.getElementById('lineage-img');
let _lastLineageBuckets = null;

function shortKey(s, n) {
  if (s === null || s === undefined) return '';
  s = String(s);
  if (n && s.length > n) return s.slice(0, n) + '\u2026';
  return s;
}
function esc(s) {
  return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function renderResults(r) {
  let html = '';
  if (r.performance && r.performance.length) {
    html += '<h4>绩效</h4><table><tr><th>signal</th><th>annual</th><th>sharpe</th><th>max_dd</th><th>excess</th></tr>';
    for (const row of r.performance) {
      html += `<tr><td>${esc(row.signal)}</td><td>${((row.annual_return||0)*100).toFixed(2)}%</td><td>${(row.sharpe||0).toFixed(2)}</td><td>${((row.max_drawdown||0)*100).toFixed(2)}%</td><td>${((row.excess_return||0)*100).toFixed(2)}%</td></tr>`;
    }
    html += '</table>';
  }
  if (r.generation_stats && r.generation_stats.length) {
    html += '<h4>每代统计</h4><table><tr><th>gen</th><th>n_valid</th><th>best</th><th>mean</th><th>best_factor</th></tr>';
    for (const row of r.generation_stats) {
      html += `<tr><td>${row.generation}</td><td>${row.n_valid}</td><td>${(row.best_fitness||0).toFixed(4)}</td><td>${(row.mean_fitness||0).toFixed(4)}</td><td>${esc(row.best_factor||'')}</td></tr>`;
    }
    html += '</table>';
  }
  if (r.diversity && r.diversity.length) {
    html += '<h4>每代多样性 / 进化操作</h4><table><tr><th>gen</th><th>n_eval</th><th>unique</th><th>depth</th><th>complex</th><th>fit_max</th><th>fit_std</th><th>elite</th><th>cross</th><th>mut</th><th>cx+mut</th><th>repro</th><th>rand_init</th><th>rand_inj</th></tr>';
    for (const row of r.diversity) {
      html += `<tr><td>${row.generation}</td><td>${row.n_evaluated}</td><td>${row.n_unique_expr}</td><td>${(row.depth_mean||0).toFixed(2)}</td><td>${(row.complexity_mean||0).toFixed(2)}</td><td>${(row.fitness_max||0).toFixed(4)}</td><td>${(row.fitness_std||0).toFixed(4)}</td><td>${row.op_elite||0}</td><td>${row.op_crossover||0}</td><td>${row.op_mutate||0}</td><td>${row.op_crossover_mutate||0}</td><td>${row.op_reproduction||0}</td><td>${row.op_random_init||0}</td><td>${row.op_random_inject||0}</td></tr>`;
    }
    html += '</table>';
  }
  if (r.exported && r.exported.length) {
    html += '<h4>已导出因子</h4><table><tr><th>function</th><th>factor</th><th>path</th></tr>';
    for (const row of r.exported) html += `<tr><td>${esc(row.function)}</td><td>${esc(row.factor)}</td><td>${esc(row.path)}</td></tr>`;
    html += '</table>';
  }
  html += `<p class="hint">输出目录：${esc(r.output_dir || '')}</p>`;
  resultsEl.innerHTML = html || '尚无结果。';

  // 按代查看
  const buckets = r.lineage_by_generation || null;
  if (buckets && Object.keys(buckets).length) {
    if (_lastLineageBuckets !== buckets) {
      const prev = genSelect.value;
      genSelect.innerHTML = '';
      const gens = Object.keys(buckets).map(x => parseInt(x, 10)).sort((a, b) => a - b);
      for (const g of gens) {
        const opt = document.createElement('option');
        opt.value = String(g);
        opt.textContent = '第 ' + g + ' 代 (' + buckets[g].length + ')';
        genSelect.appendChild(opt);
      }
      genSelect.value = (prev && buckets[prev]) ? prev : String(gens[gens.length - 1]);
      _lastLineageBuckets = buckets;
    }
    renderGenTable(buckets[genSelect.value] || []);
  } else {
    _lastLineageBuckets = null;
    genSelect.innerHTML = '';
    genTableEl.innerHTML = '尚无数据。';
  }

  // 最优血缘
  if (r.lineage_tree_url) {
    lineageImgEl.innerHTML = `<a href="${esc(r.lineage_tree_url)}" target="_blank">打开大图</a><br><img src="${esc(r.lineage_tree_url)}?t=${Date.now()}" style="width:100%; max-height:720px; object-fit:contain; background:#fff; border:1px solid var(--border); border-radius:10px; margin-top:8px;">`;
  } else {
    lineageImgEl.innerHTML = '尚无图片。';
  }
  if (r.lineage_top_text && r.lineage_top_text.trim()) {
    lineageTopEl.textContent = r.lineage_top_text;
  } else {
    lineageTopEl.textContent = '尚无数据。';
  }
}

function renderGenTable(rows) {
  if (!rows || !rows.length) { genTableEl.innerHTML = '该代无有效因子。'; return; }
  let html = '<table><tr><th>#</th><th>factor</th><th>op</th><th>mut</th><th>fitness</th><th>rank_ic</th><th>IR</th><th>depth</th><th>cx</th><th>survived</th><th>expr</th><th>parents</th></tr>';
  rows.forEach((row, i) => {
    const survived = row.survived ? '✓' : '';
    html += `<tr><td>${i + 1}</td><td>${esc(row.factor)}</td><td>${esc(row.operation)}</td><td>${esc(row.mutation_op || '')}</td><td>${(row.fitness||0).toFixed(4)}</td><td>${(row.rank_ic_mean||0).toFixed(4)}</td><td>${(row.rank_ic_ir||0).toFixed(2)}</td><td>${row.depth||0}</td><td>${row.complexity||0}</td><td>${survived}</td><td title="${esc(row.expr_key)}">${esc(shortKey(row.expr_key, 80))}</td><td title="${esc(row.parents)}">${esc(shortKey(row.parents, 60))}</td></tr>`;
  });
  html += '</table>';
  genTableEl.innerHTML = html;
}

genSelect.addEventListener('change', () => {
  if (_lastLineageBuckets) renderGenTable(_lastLineageBuckets[genSelect.value] || []);
});

async function pollStatus() {
  try {
    const s = await fetch('/api/status').then(r => r.json());
    if (s.running) {
      statusEl.className = 'status run';
      statusEl.textContent = '运行中 ' + (s.start_time || '');
      btn.disabled = true;
    } else if (s.error) {
      statusEl.className = 'status err';
      statusEl.textContent = '失败: ' + s.error;
      btn.disabled = false;
    } else if (s.last_results) {
      statusEl.className = 'status ok';
      statusEl.textContent = '完成 ' + (s.end_time || '');
      btn.disabled = false;
    } else {
      statusEl.className = 'status';
      statusEl.textContent = '空闲';
      btn.disabled = false;
    }
    if (s.logs && s.logs.length) {
      const nearBottom = logsEl.scrollHeight - logsEl.scrollTop - logsEl.clientHeight < 30;
      logsEl.textContent = s.logs.join('\\n');
      if (nearBottom) logsEl.scrollTop = logsEl.scrollHeight;
    }
    if (s.last_results) renderResults(s.last_results);
  } catch (e) {}
}

form.addEventListener('submit', async ev => {
  ev.preventDefault();
  btn.disabled = true;
  const resp = await fetch('/api/run', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(readForm())});
  const j = await resp.json();
  if (!j.ok) {
    alert(j.error || '启动失败');
    btn.disabled = false;
  }
});

async function init() {
  const cfg = await fetch('/api/config').then(r => r.json());
  fillForm(cfg);
  pollStatus();
  setInterval(pollStatus, 1500);
}
init();
</script>
</body>
</html>"""
