#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""``workflow_custom_factors`` 的 Web 控制台 HTML 渲染。

把 HTML/CSS/JS 单独抽出，避免把主文件撑得太大；
``workflow_custom_factors.py`` 里通过
``from _workflow_custom_factors_html import render_index_html`` 引用。
"""

from __future__ import annotations

from pathlib import Path
import sys

_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

import factor_loader  # type: ignore  # noqa: E402


def render_index_html() -> str:
    libraries = factor_loader.list_libraries()
    if "custom" not in libraries:
        libraries = ["custom"] + libraries
    # 把 custom 排到最前，且默认勾上；其它库默认不勾
    libs_sorted = ["custom"] + [x for x in libraries if x != "custom"]
    lib_options_html = "".join(
        f'<label class="lib-opt"><input type="checkbox" name="factor_libraries" '
        f'value="{lib}" {"checked" if lib == "custom" else ""}> {lib}</label>'
        for lib in libs_sorted
    )

    return f"""<!doctype html>
<html lang="zh-CN"><head>
<meta charset="utf-8"><title>自定义因子分析控制台</title>
<style>
  body {{ font-family: -apple-system, "Segoe UI", "Microsoft Yahei", sans-serif; margin:0; padding:20px; background:#f5f6fa; color:#222; }}
  h1 {{ margin:0 0 12px; font-size:20px; }}
  h1 .sub {{ font-size:13px; color:#666; font-weight:normal; margin-left:10px; }}
  fieldset {{ background:#fff; border:1px solid #dfe2ea; border-radius:8px; padding:14px 16px; margin-bottom:14px; }}
  legend {{ font-weight:600; color:#333; padding:0 6px; }}
  .row {{ display:flex; flex-wrap:wrap; gap:12px; align-items:flex-end; }}
  .row label {{ display:flex; flex-direction:column; font-size:12px; color:#444; }}
  .row label > div {{ margin-bottom:4px; color:#666; }}
  input[type="text"], input[type="number"], select, textarea {{
    padding:6px 8px; border:1px solid #ccd0d8; border-radius:6px; font-size:13px; background:#fff; min-width:140px;
  }}
  textarea {{ width:100%; min-height:80px; resize:vertical; font-family:inherit; }}
  button {{ padding:7px 14px; border:0; border-radius:6px; background:#2f6feb; color:#fff; cursor:pointer; font-size:13px; }}
  button.secondary {{ background:#5a6477; }}
  button.danger {{ background:#d24b4b; }}
  button:disabled {{ background:#9aa6b8; cursor:not-allowed; }}
  table {{ width:100%; border-collapse:collapse; margin:6px 0; font-size:12px; }}
  th, td {{ border-bottom:1px solid #eee; padding:4px 8px; text-align:left; }}
  th {{ background:#f0f3f8; }}
  .lib-opt {{ display:inline-flex; gap:4px; padding:4px 10px; margin:2px; border:1px solid #d8dde6; border-radius:14px; background:#fafbfc; font-size:12px; cursor:pointer; }}
  .lib-opt:hover {{ background:#eef3ff; }}
  #logs {{ background:#181c24; color:#d2d6e0; padding:10px; border-radius:8px; font-family:Consolas, monospace; font-size:12px; height:240px; overflow-y:auto; white-space:pre-wrap; }}
  #gen-logs {{ background:#181c24; color:#d2d6e0; padding:10px; border-radius:8px; font-family:Consolas, monospace; font-size:12px; min-height:80px; max-height:200px; overflow-y:auto; white-space:pre-wrap; }}
  .pill {{ display:inline-block; padding:2px 8px; border-radius:12px; font-size:11px; background:#eef3ff; color:#2f6feb; margin-right:4px; }}
  .pill.warn {{ background:#fdecea; color:#d24b4b; }}
  .pill.ok {{ background:#e7f6ec; color:#218c5a; }}
  .factor-list-item {{ display:flex; align-items:center; gap:8px; padding:4px 0; border-bottom:1px dashed #eee; font-size:12px; }}
  .factor-list-item .name {{ flex:0 0 240px; font-family:Consolas, monospace; }}
  .factor-list-item .meta {{ flex:1; color:#999; }}
  img.fig {{ max-width:100%; border:1px solid #e2e6ee; border-radius:6px; margin:6px 0; }}
</style>
</head>
<body>

<h1>🧪 自定义因子分析控制台 <span class="sub">DeepSeek 自动生成 → 与经典因子对照评价（IC / 分层 / 相关性）</span></h1>

<!-- ============================================================ -->
<fieldset>
  <legend>0. DeepSeek 因子生成</legend>
  <div class="row">
    <label style="flex:1; min-width:340px;"><div>自然语言描述（例如：5 日反转因子，过去窗口跌得越多，未来反弹概率越高）</div>
      <textarea id="gen-desc" placeholder="用中文/英文描述你想要的单因子逻辑..."></textarea>
    </label>
  </div>
  <div class="row" style="margin-top:8px;">
    <label><div>因子名（可选，不含 compute_ 前缀）</div>
      <input id="gen-name" type="text" placeholder="如 simple_reversal_5d"/>
    </label>
    <label><div>模型（留空走配置文件）</div>
      <input id="gen-model" type="text" placeholder="如 deepseek-chat / deepseek-reasoner"/>
    </label>
    <label><div><input id="gen-overwrite" type="checkbox"> 覆盖已存在</div></label>
    <label><div><input id="gen-dryrun" type="checkbox"> 预览（dry_run，不联网/不落盘）</div></label>
    <button id="btn-generate">🚀 生成</button>
  </div>
  <div id="llm-info" style="margin-top:8px; font-size:11px; color:#666;">⏳ 正在读取 LLM 配置...</div>
  <div id="gen-logs" style="margin-top:10px;">尚未提交生成请求。</div>
  <div style="margin-top:14px;">
    <strong>已生成因子（custom 库）</strong>
    <button id="btn-refresh-list" class="secondary" style="margin-left:8px; font-size:11px; padding:3px 8px;">刷新</button>
    <div id="factor-list" style="margin-top:6px;"></div>
  </div>
</fieldset>

<!-- ============================================================ -->
<form id="cfg-form">
<fieldset>
  <legend>1. 数据范围</legend>
  <div class="row">
    <label><div>provider_uri</div><input name="provider_uri" type="text" style="min-width:340px;"/></label>
    <label><div>market（成分股池）</div>
      <select name="market">
        <option value="csi300">csi300 — 沪深 300，大盘股池子</option>
        <option value="csi500">csi500 — 中证 500，中盘股池子</option>
        <option value="csi800">csi800 — 中证 800（300+500）</option>
        <option value="csi1000">csi1000 — 中证 1000，中小盘</option>
        <option value="all">all — 全 A 股（最彻底）</option>
        <option value="csiall">csiall — 全市场指数池</option>
      </select>
    </label>
    <label><div>benchmark</div>
      <select name="benchmark">
        <option value="SH000300">SH000300 — 沪深 300 指数</option>
        <option value="SH000905">SH000905 — 中证 500 指数</option>
        <option value="SH000852">SH000852 — 中证 1000 指数</option>
        <option value="SH000016">SH000016 — 上证 50 指数</option>
        <option value="SH000001">SH000001 — 上证综指</option>
        <option value="SZ399001">SZ399001 — 深证成指</option>
      </select>
    </label>
    <label><div>start_time</div><input name="start_time" type="text" placeholder="YYYY-MM-DD"/></label>
    <label><div>end_time</div><input name="end_time" type="text" placeholder="YYYY-MM-DD"/></label>
  </div>
</fieldset>

<fieldset>
  <legend>1.5 股票池过滤（akshare 市值 + 静态股价区间）</legend>
  <div class="row">
    <label><div><input name="enable_market_cap_filter" type="checkbox"> 启用市值过滤</div></label>
    <label><div>市值下限（亿元）</div><input name="min_market_cap_yi" type="number" step="1" min="0"/></label>
    <label><div>市值上限（亿元）</div><input name="max_market_cap_yi" type="number" step="1" min="0"/></label>
    <label><div>市值口径</div>
      <select name="market_cap_kind">
        <option value="total">total（总市值）</option>
        <option value="float">float（流通市值）</option>
      </select>
    </label>
  </div>
  <div class="row">
    <label><div><input name="enable_price_filter" type="checkbox"> 启用股价过滤</div></label>
    <label><div>股价下限（元）</div><input name="min_close_price" type="number" step="0.1" min="0"/></label>
    <label><div>股价上限（元）</div><input name="max_close_price" type="number" step="0.1" min="0"/></label>
    <label><div>参考价取法</div>
      <select name="price_filter_mode">
        <option value="last">last</option>
        <option value="mean">mean</option>
        <option value="median">median</option>
      </select>
    </label>
  </div>
  <div class="row">
    <label><div>市值缓存有效期（天）</div><input name="market_cap_cache_max_age_days" type="number" step="1" min="0"/></label>
    <label><div><input name="force_refresh_market_cap_cache" type="checkbox"> 强制刷新市值缓存</div></label>
  </div>
  <div class="row">
    <label><div><input name="enable_market_data_cache" type="checkbox"> 启用行情缓存</div></label>
    <label><div>行情缓存目录</div><input name="market_data_cache_dir" type="text"/></label>
  </div>
</fieldset>

<fieldset>
  <legend>2. 因子库（默认勾选 custom，可一并选其他库做对照）</legend>
  <div id="lib-options">{lib_options_html}</div>
  <div class="row" style="margin-top:8px;">
    <label><div><input name="enable_factor_cache" type="checkbox"> 启用因子缓存</div></label>
    <label><div>缓存目录</div><input name="factor_cache_dir" type="text"/></label>
    <button type="button" id="btn-cache-stats" class="secondary">查看缓存</button>
    <button type="button" id="btn-cache-clear" class="danger">清空缓存</button>
    <span id="cache-info" style="font-size:11px; color:#666;"></span>
  </div>
</fieldset>

<fieldset>
  <legend>3. 未来收益 + 分层</legend>
  <div class="row">
    <label><div>future_return_mode</div>
      <select name="future_return_mode">
        <option value="holding_close">holding_close</option>
        <option value="max_high">max_high</option>
        <option value="max_close">max_close</option>
      </select>
    </label>
    <label><div>holding_period</div><input name="holding_period" type="number" min="1" step="1"/></label>
    <label><div>quantiles</div><input name="quantiles" type="number" min="2" step="1"/></label>
    <label><div>output_dir</div><input name="output_dir" type="text"/></label>
  </div>
</fieldset>

<div class="row" style="margin:16px 0;">
  <button type="submit" id="btn-run">▶️ 开始分析</button>
  <button type="button" id="btn-save" class="secondary">仅保存配置</button>
  <span id="run-status" style="font-size:12px; color:#666; margin-left:8px;"></span>
</div>
</form>

<!-- ============================================================ -->
<fieldset>
  <legend>📜 运行日志</legend>
  <div id="logs">（尚未运行）</div>
</fieldset>

<fieldset>
  <legend>📊 运行结果</legend>
  <div id="results">尚无结果。</div>
</fieldset>

<script>
const cfgForm = document.getElementById('cfg-form');
const logsEl  = document.getElementById('logs');
const resultsEl = document.getElementById('results');
const runStatusEl = document.getElementById('run-status');
const cacheInfoEl = document.getElementById('cache-info');
const factorListEl = document.getElementById('factor-list');
const genLogsEl = document.getElementById('gen-logs');

let activeJobId = null;
let lastRunStatusText = '';
let lastLogsText = '';
let lastResultsKey = '';
let lastResultsRendered = false;

function setFormValues(cfg) {{
  for (const [k, v] of Object.entries(cfg)) {{
    const els = cfgForm.elements[k];
    if (!els) continue;
    if (els instanceof RadioNodeList) {{
      // factor_libraries 多选
      const want = Array.isArray(v) ? new Set(v.map(String)) : new Set();
      els.forEach(el => {{ el.checked = want.has(el.value); }});
    }} else if (els.type === 'checkbox') {{
      els.checked = !!v;
    }} else {{
      els.value = v;
    }}
  }}
}}

function readForm() {{
  const fd = new FormData(cfgForm);
  const obj = {{}};
  // 先用 entries 收集普通字段（多值会被覆盖）
  for (const [k, v] of fd.entries()) {{ obj[k] = v; }}
  // 再处理多值
  obj.factor_libraries = fd.getAll('factor_libraries');
  // 处理 checkbox：未勾选时 FormData 完全不会出现 → 手动补 false
  ['enable_market_cap_filter', 'enable_price_filter', 'force_refresh_market_cap_cache', 'enable_market_data_cache', 'enable_factor_cache']
    .forEach(k => {{ obj[k] = !!cfgForm.elements[k]?.checked; }});
  return obj;
}}

async function loadCfg() {{
  const r = await fetch('/api/config'); const cfg = await r.json();
  setFormValues(cfg);
}}

async function refreshCacheStats() {{
  try {{
    const r = await fetch('/api/factor_cache/stats'); const j = await r.json();
    cacheInfoEl.textContent = `因子缓存: ${{j.count||0}} 条 / ${{(j.size_mb||0).toFixed(1)}} MB；行情缓存: ${{j.market_data_count||0}} 条 / ${{(j.market_data_size_mb||0).toFixed(1)}} MB`;
  }} catch (e) {{ cacheInfoEl.textContent = '(读取失败)'; }}
}}

async function refreshFactorList() {{
  try {{
    const r = await fetch('/api/custom_factors'); const j = await r.json();
    if (!j.items || j.items.length === 0) {{
      factorListEl.innerHTML = '<div style="color:#999; font-size:12px; padding:6px 0;">尚无自定义因子，先在上方生成一个。</div>';
      return;
    }}
    factorListEl.innerHTML = j.items.map(item => `
      <div class="factor-list-item">
        <span class="name">${{item.name}}.py</span>
        <span class="meta">${{item.mtime}} · ${{(item.size||0)}} bytes</span>
        <button type="button" data-act="view" data-name="${{item.name}}" class="secondary" style="padding:3px 8px; font-size:11px;">查看</button>
        <button type="button" data-act="del"  data-name="${{item.name}}" class="danger" style="padding:3px 8px; font-size:11px;">删除</button>
      </div>
    `).join('');
  }} catch (e) {{ factorListEl.innerHTML = '<div>(加载失败)</div>'; }}
}}

factorListEl.addEventListener('click', async (ev) => {{
  const btn = ev.target.closest('button');
  if (!btn) return;
  const name = btn.dataset.name;
  if (btn.dataset.act === 'del') {{
    if (!confirm(`确定删除 ${{name}}.py 吗？`)) return;
    const r = await fetch('/api/custom_factors/delete', {{ method:'POST', headers:{{'Content-Type':'application/json'}}, body: JSON.stringify({{name}}) }});
    const j = await r.json();
    if (j.ok) refreshFactorList(); else alert('删除失败：' + (j.error||''));
  }} else if (btn.dataset.act === 'view') {{
    const r = await fetch('/api/custom_factors/source?name=' + encodeURIComponent(name));
    const j = await r.json();
    if (j.ok) {{
      genLogsEl.textContent = `# ${{name}}.py\\n\\n` + j.source;
    }} else {{
      alert('查看失败：' + (j.error||''));
    }}
  }}
}});

document.getElementById('btn-cache-stats').addEventListener('click', refreshCacheStats);
document.getElementById('btn-cache-clear').addEventListener('click', async () => {{
  if (!confirm('确定清空因子缓存？')) return;
  await fetch('/api/factor_cache/clear', {{ method:'POST' }});
  refreshCacheStats();
}});
document.getElementById('btn-refresh-list').addEventListener('click', refreshFactorList);

document.getElementById('btn-save').addEventListener('click', async () => {{
  const r = await fetch('/api/config', {{ method:'POST', headers:{{'Content-Type':'application/json'}}, body: JSON.stringify(readForm()) }});
  const j = await r.json();
  if (j.ok) {{
    if (j.config) setFormValues(j.config);
    runStatusEl.textContent = '✅ 配置已保存，下次打开会默认使用本配置';
  }} else {{
    runStatusEl.textContent = '❌ 保存失败';
  }}
}});

cfgForm.addEventListener('submit', async (ev) => {{
  ev.preventDefault();
  runStatusEl.textContent = '提交中...';
  const r = await fetch('/api/run', {{ method:'POST', headers:{{'Content-Type':'application/json'}}, body: JSON.stringify(readForm()) }});
  const j = await r.json();
  if (j.ok) {{
    if (j.config) setFormValues(j.config);
    runStatusEl.textContent = '🟢 已启动，正在后台运行...';
    logsEl.textContent = '';
    resultsEl.innerHTML = '正在运行，等待结果...';
    lastRunStatusText = '';
    lastLogsText = '';
    lastResultsKey = '';
    lastResultsRendered = false;
  }}
  else      {{ runStatusEl.textContent = '❌ ' + (j.error || '启动失败'); }}
}});

document.getElementById('btn-generate').addEventListener('click', async () => {{
  const desc = document.getElementById('gen-desc').value.trim();
  if (!desc) {{ alert('请输入因子描述'); return; }}
  const payload = {{
    description: desc,
    factor_name: document.getElementById('gen-name').value.trim(),
    model:       document.getElementById('gen-model').value.trim(),
    overwrite:   document.getElementById('gen-overwrite').checked,
    dry_run:     document.getElementById('gen-dryrun').checked,
  }};
  genLogsEl.textContent = '提交中...';
  const r = await fetch('/api/custom_factors/generate', {{ method:'POST', headers:{{'Content-Type':'application/json'}}, body: JSON.stringify(payload) }});
  const j = await r.json();
  if (!j.ok) {{ genLogsEl.textContent = '❌ ' + (j.error || '提交失败'); return; }}
  activeJobId = j.job_id;
  genLogsEl.textContent = '🟢 任务已提交 (job=' + j.job_id + ')，正在调用 DeepSeek...';
}});

async function pollGenStatus() {{
  if (!activeJobId) return;
  try {{
    const r = await fetch('/api/custom_factors/generate/status?job_id=' + activeJobId);
    const j = await r.json();
    if (!j.ok) return;
    let lines = [];
    lines.push((j.running ? '🟡 运行中' : (j.ok === true ? '✅ 成功' : '❌ 失败')) +
      ' | start=' + (j.start_time||'') + ' | end=' + (j.end_time||''));
    if (j.message) lines.push(j.message);
    if (j.file_path) lines.push('file: ' + j.file_path);
    if (j.code_preview) lines.push('--- code ---\\n' + j.code_preview);
    if (j.traceback) lines.push('--- traceback ---\\n' + j.traceback);
    genLogsEl.textContent = lines.join('\\n');
    if (!j.running) {{
      activeJobId = null;
      refreshFactorList();
    }}
  }} catch (e) {{}}
}}

async function pollRunStatus() {{
  try {{
    const r = await fetch('/api/status');
    if (!r.ok) {{
      resultsEl.innerHTML = `<div style="color:#d24b4b;">状态接口返回 HTTP ${{r.status}}，请查看终端日志。</div>`;
      return;
    }}
    const s = await r.json();
    let statusText = '';
    if (s.running) {{ statusText = '🟢 运行中... 起于 ' + (s.start_time||''); }}
    else if (s.error) {{ statusText = '❌ ' + s.error; }}
    else if (s.end_time) {{ statusText = '✅ 完成于 ' + s.end_time; }}
    if (statusText && statusText !== lastRunStatusText) {{
      runStatusEl.textContent = statusText;
      lastRunStatusText = statusText;
    }}
    if (s.logs && s.logs.length) {{
      const logsText = s.logs.join('\\n');
      if (logsText !== lastLogsText) {{
        const shouldFollowLogTail = (logsEl.scrollTop + logsEl.clientHeight) >= (logsEl.scrollHeight - 24);
        logsEl.textContent = logsText;
        if (shouldFollowLogTail) logsEl.scrollTop = logsEl.scrollHeight;
        lastLogsText = logsText;
      }}
    }}
    if (s.last_results) renderResults(s.last_results);
    else if (s.end_time && !s.error && !lastResultsRendered) {{
      resultsEl.innerHTML = '<div style="color:#d9822b;">运行已结束，但当前服务内存中没有结果摘要。请重新点击“开始分析”；如果仍出现，请查看终端是否有 /api/status 报错。</div>';
      lastResultsRendered = true;
    }}
  }} catch (e) {{
    resultsEl.innerHTML = `<div style="color:#d24b4b;">读取运行状态失败：${{e}}</div>`;
  }}
}}

function renderResults(r) {{
  const key = JSON.stringify(r);
  if (key === lastResultsKey) return;
  lastResultsKey = key;
  lastResultsRendered = true;
  let html = `<p style="margin:6px 0;">共加载 <b>${{r.n_factors_total||0}}</b> 个因子。</p>`;
  if (r.factor_evaluation_head && r.factor_evaluation_head.length) {{
    html += '<h3 style="font-size:14px;margin:6px 0;">🏆 因子评价 Top 20（按 |rank_ic_ir| 排序）</h3>';
    html += '<table><tr><th>factor</th><th>rank_ic_mean</th><th>rank_ic_ir</th><th>ic_mean</th><th>ic_ir</th><th>ic_win_rate</th></tr>';
    for (const row of r.factor_evaluation_head) {{
      const fmt = (v, p=4) => (v===undefined||v===null||isNaN(v)) ? '-' : Number(v).toFixed(p);
      html += `<tr><td>${{row.factor}}</td><td>${{fmt(row.rank_ic_mean)}}</td><td>${{fmt(row.rank_ic_ir,3)}}</td><td>${{fmt(row.ic_mean)}}</td><td>${{fmt(row.ic_ir,3)}}</td><td>${{((row.ic_win_rate||0)*100).toFixed(1)}}%</td></tr>`;
    }}
    html += '</table>';
  }}
  if (r.figs && r.figs.length) {{
    html += '<div style="margin-top:10px;">';
    const imageVersion = encodeURIComponent(r.end_time || r.output_dir || 'latest');
    for (const fname of r.figs) {{
      html += `<img class="fig" src="/api/figs/${{fname}}?v=${{imageVersion}}" alt="${{fname}}"/>`;
    }}
    html += '</div>';
  }}
  if (r.output_dir) html += `<p style="font-size:11px; color:#999;">结果目录：${{r.output_dir}}</p>`;
  resultsEl.innerHTML = html;
}}

async function refreshLLMInfo() {{
  const el = document.getElementById('llm-info');
  try {{
    const r = await fetch('/api/llm_config'); const j = await r.json();
    const cfgFile = j.config_exists ? '✅' : '⚠️ 未创建';
    const keyState = j.api_key_set ? `🔑 ${{j.api_key_masked||'(已设置)'}}` : '❌ 未配置';
    el.innerHTML =
      `<b>当前 LLM 配置</b> | model=<code>${{j.model||''}}</code> | base_url=<code>${{j.base_url||''}}</code> | temperature=${{j.temperature}} | max_retries=${{j.max_retries}} | api_key: ${{keyState}}<br>` +
      `📄 配置文件 ${{cfgFile}}: <code>${{j.config_path||''}}</code>（不入版本库；模板见 <code>${{j.example_path||''}}</code>）`;
  }} catch (e) {{ el.textContent = '⚠️ 读取 LLM 配置失败'; }}
}}

async function init() {{
  await loadCfg();
  await refreshCacheStats();
  await refreshFactorList();
  await refreshLLMInfo();
  await pollRunStatus();
  setInterval(pollRunStatus, 1500);
  setInterval(pollGenStatus, 1200);
}}
init();
</script>
</body></html>
"""
