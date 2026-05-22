from __future__ import annotations

import ast
import json
import os
import re
import tempfile
import textwrap
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
SOURCE_DIR = BASE_DIR.parent
CUSTOM_DIR = SOURCE_DIR / "factors" / "custom"
LLM_CONFIG_PATH = BASE_DIR / "llm_config.json"
LLM_CONFIG_EXAMPLE_PATH = BASE_DIR / "llm_config.example.json"


def _ensure_dirs() -> None:
    CUSTOM_DIR.mkdir(parents=True, exist_ok=True)
    BASE_DIR.mkdir(parents=True, exist_ok=True)


def _safe_factor_name(name: Optional[str]) -> str:
    text = str(name or "custom_factor").strip().lower()
    text = re.sub(r"[^0-9a-zA-Z_]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    if not text:
        text = "custom_factor"
    if text[0].isdigit():
        text = f"factor_{text}"
    return text


def list_custom_factors() -> List[str]:
    _ensure_dirs()
    return sorted(
        p.stem
        for p in CUSTOM_DIR.glob("*.py")
        if p.is_file() and not p.name.startswith("_")
    )


def _compute_functions(namespace: Dict[str, Any]) -> List[Any]:
    funcs = []
    for name, value in namespace.items():
        if name.startswith("compute_") and callable(value):
            funcs.append(value)
    return funcs


def validate_factor_code(source: str, run_smoke_test: bool = True) -> Tuple[bool, str]:
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return False, f"语法错误: {exc}"

    forbidden_imports = {"subprocess", "socket", "shutil"}
    forbidden_calls = {"eval", "exec", "compile", "open", "__import__"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root in forbidden_imports:
                    return False, f"禁止导入模块: {root}"
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            if root in forbidden_imports:
                return False, f"禁止导入模块: {root}"
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in forbidden_calls:
                return False, f"禁止调用函数: {node.func.id}"

    namespace: Dict[str, Any] = {"np": np, "pd": pd}
    try:
        exec(compile(tree, "<custom_factor>", "exec"), namespace)
    except Exception as exc:
        return False, f"代码执行失败: {type(exc).__name__}: {exc}"

    funcs = _compute_functions(namespace)
    if not funcs:
        return False, "未找到 compute_ 开头的因子函数"

    if not run_smoke_test:
        return True, "校验通过"

    index = pd.date_range("2024-01-01", periods=8, freq="D")
    columns = ["SH600000", "SZ000001", "BJ430017"]
    base = pd.DataFrame(
        np.arange(len(index) * len(columns), dtype=float).reshape(len(index), len(columns)) + 10.0,
        index=index,
        columns=columns,
    )
    sample_map = {
        "open_df": base + 0.1,
        "high_df": base + 1.0,
        "low_df": base - 1.0,
        "close_df": base,
        "volume_df": base * 1000.0,
        "amount_df": base * base * 1000.0,
        "vwap_df": base + 0.2,
        "returns_df": base.pct_change(),
    }
    for func in funcs:
        try:
            args = func.__code__.co_varnames[: func.__code__.co_argcount]
            kwargs = {arg: sample_map[arg] for arg in args if arg in sample_map}
            result = func(**kwargs)
            if not isinstance(result, pd.DataFrame):
                return False, f"{func.__name__} 返回值不是 DataFrame"
            if result.empty:
                return False, f"{func.__name__} 返回空 DataFrame"
        except Exception as exc:
            return False, f"{func.__name__} 冒烟测试失败: {type(exc).__name__}: {exc}"
    return True, "校验通过"


def _read_llm_config() -> Dict[str, Any]:
    config: Dict[str, Any] = {}
    if LLM_CONFIG_PATH.exists():
        try:
            config.update(json.loads(LLM_CONFIG_PATH.read_text(encoding="utf-8")))
        except Exception:
            pass
    api_key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY") or config.get("api_key")
    base_url = config.get("base_url") or os.environ.get("DEEPSEEK_BASE_URL") or "https://api.deepseek.com/chat/completions"
    return {
        "api_key": api_key,
        "base_url": base_url,
        "model": config.get("model") or "deepseek-chat",
        "timeout": int(config.get("timeout", 120)),
    }


def describe_llm_config(mask_key: bool = True) -> Dict[str, Any]:
    cfg = _read_llm_config()
    key = cfg.get("api_key") or ""
    if mask_key and key:
        cfg["api_key"] = f"{key[:4]}...{key[-4:]}" if len(key) > 8 else "***"
    cfg["config_path"] = str(LLM_CONFIG_PATH)
    cfg["example_path"] = str(LLM_CONFIG_EXAMPLE_PATH)
    cfg["custom_dir"] = str(CUSTOM_DIR)
    cfg["configured"] = bool(key)
    return cfg


def _extract_code(text: str) -> str:
    match = re.search(r"```(?:python)?\s*(.*?)```", text, flags=re.S | re.I)
    if match:
        return match.group(1).strip()
    return text.strip()


def _call_llm(description: str, model: str) -> str:
    cfg = _read_llm_config()
    api_key = cfg.get("api_key")
    if not api_key:
        raise RuntimeError(f"未配置 LLM API Key，请创建 {LLM_CONFIG_PATH} 或设置 DEEPSEEK_API_KEY")
    prompt = f"""
请生成一个 Python 量化因子文件，只输出代码。
要求：
1. 必须包含一个 compute_ 开头的函数。
2. 函数参数只能从 open_df, high_df, low_df, close_df, volume_df, amount_df, vwap_df, returns_df 中选择。
3. 返回 pandas.DataFrame，index/columns 与输入保持一致。
4. 只能使用 numpy as np 和 pandas as pd。
5. 不要读写文件，不要联网，不要打印。

因子需求：
{description}
""".strip()
    payload = {
        "model": model or cfg.get("model") or "deepseek-chat",
        "messages": [
            {"role": "system", "content": "你是量化因子研究员，只输出可运行 Python 代码。"},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }
    req = urllib.request.Request(
        str(cfg.get("base_url")),
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=int(cfg.get("timeout", 120))) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"LLM 请求失败: HTTP {exc.code} {detail[:500]}") from exc
    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    if not content:
        raise RuntimeError("LLM 返回为空")
    return _extract_code(content)


def generate_custom_factor(
    description: str,
    factor_name: Optional[str] = None,
    model: str = "deepseek-chat",
    overwrite: bool = False,
    dry_run: bool = False,
) -> Path:
    _ensure_dirs()
    source = _call_llm(description=description, model=model)
    ok, msg = validate_factor_code(source, run_smoke_test=True)
    if not ok:
        raise RuntimeError(f"生成代码校验失败: {msg}")
    stem = _safe_factor_name(factor_name)
    if not stem.startswith("compute_"):
        stem = f"compute_{stem}"
    target = CUSTOM_DIR / f"{stem}.py"
    if target.exists() and not overwrite:
        suffix = 1
        while (CUSTOM_DIR / f"{stem}_{suffix:03d}.py").exists():
            suffix += 1
        target = CUSTOM_DIR / f"{stem}_{suffix:03d}.py"
    if dry_run:
        tmp = Path(tempfile.gettempdir()) / target.name
        tmp.write_text(source, encoding="utf-8")
        return tmp
    target.write_text(textwrap.dedent(source).strip() + "\n", encoding="utf-8")
    return target
