# 公共模块说明

本目录包含项目通用的工具模块。

## 模块列表

### shelve_tool.py

**功能**: 缓存工具模块

**装饰器**:
- `@shelve_me` - 永久缓存
- `@shelve_me_hour` - 按小时缓存
- `@shelve_me_today` - 按天缓存
- `@shelve_me_week` - 按周缓存

**使用示例**:
```python
from src.common.shelve_tool import shelve_me_today

@shelve_me_today
def fetch_data(param):
    # 耗时操作
    return expensive_operation(param)

# 首次调用：执行函数并缓存
result1 = fetch_data("test")

# 再次调用：直接返回缓存
result2 = fetch_data("test")  # 快速返回
```

**详细文档**: 参考 `src/高股息低波动/CACHE_GUIDE.md`

### path_config.py

**功能**: 路径配置模块

**使用示例**:
```python
from src.common.path_config import get_project_root

project_root = get_project_root()
data_dir = project_root / "data"
```

---

**最后更新**: 2024-10-31

