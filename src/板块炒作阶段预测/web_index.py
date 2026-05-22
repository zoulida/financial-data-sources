# -*- coding: utf-8 -*-
"""控制台单页 HTML 模板。"""
from __future__ import annotations


def render_index_html() -> str:
    return """<!doctype html>
<html lang=\"zh-CN\">
<head>
<meta charset=\"utf-8\" />
<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
<title>板块炒作阶段预测控制台</title>
<script src=\"https://cdn.tailwindcss.com\"></script>
<style>
  body { font-family: -apple-system, \"Segoe UI\", \"Microsoft YaHei\", sans-serif; }
  .log-line { white-space: pre-wrap; word-break: break-all; }
  table.compact td, table.compact th { padding: 4px 8px; }
  .pill { padding: 2px 8px; border-radius: 999px; font-size: 12px; font-weight: 600; }
  .pill-prep { background: #dbeafe; color: #1d4ed8; }
  .pill-active { background: #dcfce7; color: #166534; }
  .pill-late { background: #fee2e2; color: #b91c1c; }
  .pill-cold { background: #f1f5f9; color: #475569; }
  .pill-neutral { background: #fef3c7; color: #92400e; }
</style>
</head>
<body class=\"bg-slate-50 text-slate-800\">
<div class=\"max-w-7xl mx-auto p-6\">
  <header class=\"mb-6\">
    <h1 class=\"text-2xl font-bold\">板块炒作阶段预测 · Web 控制台</h1>
    <p class=\"text-sm text-slate-500\">基于 Qlib 全市场行情 + XtQuant 板块成分，输出每日板块四阶段分类。</p>
  </header>

  <section class=\"grid grid-cols-1 lg:grid-cols-3 gap-4\">
    <div class=\"lg:col-span-1 bg-white rounded-lg shadow p-4\">
      <h2 class=\"font-semibold mb-3\">运行参数</h2>
      <form id=\"cfg-form\" class=\"space-y-2 text-sm\">
        <label class=\"block\">起始日期
          <input type=\"date\" name=\"start_date\" class=\"mt-1 w-full border rounded px-2 py-1\" />
        </label>
        <label class=\"block\">结束日期
          <input type=\"date\" name=\"end_date\" class=\"mt-1 w-full border rounded px-2 py-1\" />
        </label>
        <div class=\"grid grid-cols-3 gap-2\">
          <label class=\"block\">短窗口
            <input type=\"number\" name=\"short_horizon\" class=\"mt-1 w-full border rounded px-2 py-1\" />
          </label>
          <label class=\"block\">主窗口
            <input type=\"number\" name=\"horizon\" class=\"mt-1 w-full border rounded px-2 py-1\" />
          </label>
          <label class=\"block\">长窗口
            <input type=\"number\" name=\"long_horizon\" class=\"mt-1 w-full border rounded px-2 py-1\" />
          </label>
        </div>
        <div class=\"grid grid-cols-2 gap-2\">
          <label class=\"block\">最小成分股
            <input type=\"number\" name=\"min_members\" class=\"mt-1 w-full border rounded px-2 py-1\" />
          </label>
          <label class=\"block\">最大成分股
            <input type=\"number\" name=\"max_members\" class=\"mt-1 w-full border rounded px-2 py-1\" />
          </label>
        </div>
        <div class=\"grid grid-cols-2 gap-2\">
          <label class=\"block\">模型
            <select name=\"model\" class=\"mt-1 w-full border rounded px-2 py-1\">
              <option value=\"lightgbm\">LightGBM</option>
              <option value=\"hgb\">HistGradientBoosting</option>
            </select>
          </label>
          <label class=\"block\">板块缓存(小时)
            <input type=\"number\" name=\"sector_cache_hours\" class=\"mt-1 w-full border rounded px-2 py-1\" />
          </label>
        </div>
        <div class=\"grid grid-cols-2 gap-2\">
          <label class=\"block\">训练比例
            <input type=\"number\" step=\"0.05\" name=\"train_ratio\" class=\"mt-1 w-full border rounded px-2 py-1\" />
          </label>
          <label class=\"block\">验证比例
            <input type=\"number\" step=\"0.05\" name=\"valid_ratio\" class=\"mt-1 w-full border rounded px-2 py-1\" />
          </label>
        </div>
        <label class=\"block\">指定板块（逗号或换行分隔，可空）
          <textarea name=\"sectors\" rows=\"2\" class=\"mt-1 w-full border rounded px-2 py-1\" placeholder=\"留空表示全部板块\"></textarea>
        </label>
        <label class=\"flex items-center gap-2\">
          <input type=\"checkbox\" name=\"update_sectors\" />
          <span>启动前更新本地板块数据 (download_sector_data)</span>
        </label>
        <div class=\"flex gap-2 pt-2\">
          <button type=\"button\" id=\"btn-run\" class=\"flex-1 bg-blue-600 hover:bg-blue-700 text-white py-2 rounded\">开始训练</button>
          <button type=\"button\" id=\"btn-save\" class=\"px-3 py-2 border rounded\">仅保存配置</button>
        </div>
      </form>
      <div class=\"mt-4 text-xs text-slate-500\" id=\"meta-line\">状态：未运行</div>
    </div>

    <div class=\"lg:col-span-2 bg-white rounded-lg shadow p-4\">
      <div class=\"flex items-center justify-between mb-2\">
        <h2 class=\"font-semibold\">运行日志</h2>
        <span id=\"status-pill\" class=\"pill pill-cold\">空闲</span>
      </div>
      <div id=\"log-box\" class=\"h-72 overflow-auto bg-slate-900 text-slate-100 text-xs rounded p-3 font-mono\"></div>
      <div id=\"split-meta\" class=\"mt-3 text-xs text-slate-500\"></div>
    </div>
  </section>

  <section class=\"grid grid-cols-1 lg:grid-cols-3 gap-4 mt-4\">
    <div class=\"bg-white rounded-lg shadow p-4 lg:col-span-2\">
      <div class=\"flex items-center justify-between mb-2\">
        <h2 class=\"font-semibold\">最新预测榜单 <span id=\"latest-date\" class=\"text-xs text-slate-500\"></span></h2>
        <div class=\"flex items-center gap-2 text-xs\">
          <select id=\"sort-by\" class=\"border rounded px-2 py-1\">
            <option value=\"prob_正在炒作\">按 正在炒作 概率</option>
            <option value=\"prob_预备炒作\">按 预备炒作 概率</option>
            <option value=\"prob_炒作末期\">按 炒作末期 概率</option>
            <option value=\"prob_冷门板块\">按 冷门板块 概率</option>
          </select>
          <input id=\"top-n\" type=\"number\" min=\"5\" max=\"500\" value=\"30\" class=\"w-20 border rounded px-2 py-1\" />
          <a id=\"download-latest\" class=\"text-blue-600 hover:underline\" target=\"_blank\">下载 CSV</a>
        </div>
      </div>
      <div class=\"overflow-auto max-h-[480px]\">
        <table class=\"w-full text-sm compact\" id=\"latest-table\">
          <thead class=\"bg-slate-100 sticky top-0\">
            <tr>
              <th class=\"text-left\">板块</th>
              <th>主分类</th>
              <th>预备炒作</th>
              <th>正在炒作</th>
              <th>炒作末期</th>
              <th>冷门板块</th>
            </tr>
          </thead>
          <tbody id=\"latest-tbody\"></tbody>
        </table>
      </div>
    </div>

    <div class=\"bg-white rounded-lg shadow p-4\">
      <h2 class=\"font-semibold mb-2\">模型评估</h2>
      <div id=\"eval-box\" class=\"text-sm space-y-1\"></div>
      <div class=\"mt-3\">
        <h3 class=\"font-semibold text-sm mb-1\">混淆矩阵</h3>
        <table class=\"w-full text-xs compact border\" id=\"confusion-table\"></table>
      </div>
      <div class=\"mt-3\">
        <h3 class=\"font-semibold text-sm mb-1\">Top 20 特征重要性</h3>
        <ol id=\"feat-imp\" class=\"list-decimal pl-5 text-xs space-y-0.5\"></ol>
      </div>
    </div>
  </section>

  <footer class=\"mt-6 text-xs text-slate-400\">板块炒作阶段预测 · 数据：Qlib + XtQuant</footer>
</div>

<script>
const LABELS = ['预备炒作','正在炒作','炒作末期','冷门板块'];
const PILL_CLS = {
  '预备炒作': 'pill pill-prep',
  '正在炒作': 'pill pill-active',
  '炒作末期': 'pill pill-late',
  '冷门板块': 'pill pill-cold',
  '中性板块': 'pill pill-neutral',
};

function $ (sel) { return document.querySelector(sel); }
function fmtPct (v) { return (v == null || isNaN(v)) ? '-' : (v * 100).toFixed(1) + '%'; }

async function loadConfig () {
  const res = await fetch('/api/config');
  const cfg = await res.json();
  for (const [k, v] of Object.entries(cfg)) {
    const el = document.querySelector(`[name=\"${k}\"]`);
    if (!el) continue;
    if (el.type === 'checkbox') el.checked = !!v;
    else if (Array.isArray(v)) el.value = v.join(', ');
    else el.value = v ?? '';
  }
}

function readForm () {
  const form = $('#cfg-form');
  const data = {};
  for (const el of form.elements) {
    if (!el.name) continue;
    if (el.type === 'checkbox') data[el.name] = el.checked;
    else if (el.type === 'number') data[el.name] = el.value === '' ? null : Number(el.value);
    else if (el.name === 'sectors') {
      const v = el.value.trim();
      data[el.name] = v ? v.split(/[\\s,，]+/).filter(Boolean) : [];
    } else data[el.name] = el.value;
  }
  return data;
}

async function postJSON (url, body) {
  const res = await fetch(url, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body) });
  return res.json();
}

async function saveConfig () { const r = await postJSON('/api/config', readForm()); return r; }

async function runTask () {
  const r = await postJSON('/api/run', readForm());
  if (!r.ok) alert(r.error || '启动失败');
}

function renderConfusion (eval_) {
  const box = $('#confusion-table');
  if (!eval_ || !eval_.confusion_matrix) { box.innerHTML = ''; return; }
  const labels = eval_.labels || LABELS;
  let html = '<thead><tr><th></th>';
  for (const l of labels) html += `<th>${l}</th>`;
  html += '</tr></thead><tbody>';
  eval_.confusion_matrix.forEach((row, i) => {
    html += `<tr><th class=\"text-left\">${labels[i] || i}</th>`;
    for (const v of row) html += `<td class=\"text-right\">${v}</td>`;
    html += '</tr>';
  });
  html += '</tbody>';
  box.innerHTML = html;
}

function renderEval (eval_) {
  const box = $('#eval-box');
  if (!eval_) { box.innerHTML = '<div class=\"text-slate-400\">暂无</div>'; return; }
  const per = eval_.per_class || {};
  let html = '';
  html += `<div>样本数: <b>${eval_.n_samples ?? '-'}</b></div>`;
  html += `<div>Accuracy: <b>${fmtPct(eval_.accuracy)}</b> · macro F1: <b>${(eval_.macro_f1 ?? 0).toFixed(3)}</b> · balanced acc: <b>${(eval_.balanced_accuracy ?? 0).toFixed(3)}</b></div>`;
  html += '<table class=\"w-full text-xs mt-2 compact\"><thead><tr><th class=\"text-left\">类别</th><th>P</th><th>R</th><th>F1</th><th>支持</th></tr></thead><tbody>';
  for (const [k, v] of Object.entries(per)) {
    html += `<tr><td><span class=\"${PILL_CLS[k] || ''}\">${k}</span></td><td class=\"text-right\">${(v.precision*100).toFixed(1)}%</td><td class=\"text-right\">${(v.recall*100).toFixed(1)}%</td><td class=\"text-right\">${v.f1.toFixed(3)}</td><td class=\"text-right\">${v.support}</td></tr>`;
  }
  html += '</tbody></table>';
  box.innerHTML = html;
}

function renderImportance (importance) {
  const ol = $('#feat-imp');
  if (!importance) { ol.innerHTML = ''; return; }
  const items = Object.entries(importance).sort((a,b)=>b[1]-a[1]).slice(0, 20);
  ol.innerHTML = items.map(([k, v]) => `<li><span class=\"font-mono\">${k}</span> <span class=\"text-slate-400\">${v.toFixed(0)}</span></li>`).join('');
}

function renderLatest (latest, sortBy, topN) {
  const tbody = $('#latest-tbody');
  if (!latest || !latest.length) { tbody.innerHTML = '<tr><td colspan=\"6\" class=\"text-center text-slate-400 py-4\">暂无</td></tr>'; return; }
  const sorted = [...latest].sort((a,b)=>(b[sortBy] ?? -Infinity)-(a[sortBy] ?? -Infinity)).slice(0, topN);
  tbody.innerHTML = sorted.map(row => {
    const cls = PILL_CLS[row.pred_label] || 'pill pill-cold';
    return `<tr class=\"border-b\"><td class=\"font-medium\">${row.sector}</td>` +
      `<td class=\"text-center\"><span class=\"${cls}\">${row.pred_label}</span></td>` +
      `<td class=\"text-right\">${fmtPct(row['prob_预备炒作'])}</td>` +
      `<td class=\"text-right\">${fmtPct(row['prob_正在炒作'])}</td>` +
      `<td class=\"text-right\">${fmtPct(row['prob_炒作末期'])}</td>` +
      `<td class=\"text-right\">${fmtPct(row['prob_冷门板块'])}</td></tr>`;
  }).join('');
}

let _lastLogLen = 0;
async function poll () {
  try {
    const res = await fetch('/api/status');
    const s = await res.json();
    const pill = $('#status-pill');
    if (s.running) { pill.textContent = '运行中'; pill.className = 'pill pill-active'; }
    else if (s.error) { pill.textContent = '失败'; pill.className = 'pill pill-late'; }
    else if (s.last_results) { pill.textContent = '已完成'; pill.className = 'pill pill-prep'; }
    else { pill.textContent = '空闲'; pill.className = 'pill pill-cold'; }
    $('#meta-line').textContent = `状态：${pill.textContent}` +
      (s.start_time ? ` · 开始：${s.start_time}` : '') +
      (s.end_time ? ` · 结束：${s.end_time}` : '');

    const logs = s.logs || [];
    if (logs.length !== _lastLogLen) {
      const box = $('#log-box');
      box.innerHTML = logs.map(l => `<div class=\"log-line\">${l.replace(/</g,'&lt;')}</div>`).join('');
      box.scrollTop = box.scrollHeight;
      _lastLogLen = logs.length;
    }

    const r = s.last_results;
    if (r) {
      $('#latest-date').textContent = r.latest_date ? `(${r.latest_date})` : '';
      $('#split-meta').textContent = r.split_meta ?
        `时间切分：train ≤ ${r.split_meta.train_end} · valid ≤ ${r.split_meta.valid_end} · test ≥ ${r.split_meta.test_start} · 模型: ${r.model_used}` : '';
      renderEval(r.test_eval);
      renderConfusion(r.test_eval);
      renderImportance(r.feature_importance);
      renderLatest(r.latest_predictions || [], $('#sort-by').value, Number($('#top-n').value || 30));
      if (r.latest_csv_url) $('#download-latest').href = r.latest_csv_url;
    }
  } catch (e) {
    console.error(e);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  loadConfig();
  $('#btn-save').addEventListener('click', async () => { await saveConfig(); alert('配置已保存'); });
  $('#btn-run').addEventListener('click', async () => { await saveConfig(); await runTask(); });
  $('#sort-by').addEventListener('change', poll);
  $('#top-n').addEventListener('change', poll);
  setInterval(poll, 1500);
  poll();
});
</script>
</body>
</html>
"""
