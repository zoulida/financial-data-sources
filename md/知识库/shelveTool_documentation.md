# shelveTool.py - Python Shelve 缓存模块

## 概述

`shelveTool.py` 是一个功能全面的 Python 模块，使用 Python 内置的 `shelve` 模块提供缓存功能。它提供各种装饰器和实用函数，可以以不同的过期时间（小时、天、周或永久）缓存函数结果。

## 功能特性

- **多种缓存策略**：小时级、日级、周级和永久缓存
- **基于装饰器的缓存**：易于使用的函数缓存装饰器
- **自动键生成**：基于函数名、参数和时间的智能键生成
- **错误处理**：抛出异常的函数不会被缓存
- **类方法支持**：专门用于类方法的装饰器
- **模块路径感知**：高级装饰器在缓存键中包含模块路径

## 依赖项

- `shelve` (Python 内置模块)
- `inspect` (Python 内置模块)
- `os` (Python 内置模块)
- `Config.py` (自定义配置模块)

## 配置

该模块需要一个包含 `FILEPATH` 枚举的 `Config.py` 文件来定义 shelve 目录：

```python
from enum import Enum

class CustomEnum(Enum):
    def __repr__(self):
        return "%s.%s" % (self.__class__.__name__, self._name_)

class FILEPATH(CustomEnum):
    SHELVEDIR = "F:\\SHELVEDIR\\SHELVEFILE20240926"  # 您的 shelve 目录路径
```

## 核心函数

### 基础 Shelve 操作

#### `saveShelve(key, content)`
将内容保存到 shelve 数据库。

**参数:**
- `key` (str): 存储内容的键
- `content`: 要存储的数据

**示例:**
```python
import tools.shelveTool as st
st.saveShelve('my_key', {'data': [1, 2, 3]})
```

#### `getShelve(key)`
从 shelve 数据库检索内容。

**参数:**
- `key` (str): 要检索的键

**返回值:** 存储的内容

**示例:**
```python
data = st.getShelve('my_key')
```

#### `getShelveData(name, fun, args, kwargs)`
处理缓存逻辑的核心函数。检查数据是否存在于缓存中，如果不存在，则执行函数并缓存结果。

**参数:**
- `name` (str): 缓存键名称
- `fun` (callable): 如果未缓存则要执行的函数
- `args` (tuple): 函数参数
- `kwargs` (dict): 函数关键字参数

**返回值:** 缓存的结果或新计算的结果

## 装饰器

### 基于时间的缓存装饰器

#### `@shelve_me_week`
缓存函数结果一周。

```python
@shelve_me_week
def expensive_calculation(data):
    # 对于相同参数，这只会每周运行一次
    return process_data(data)
```

#### `@shelve_me_hour`
缓存函数结果一小时。

```python
@shelve_me_hour
def api_call(endpoint):
    # 对于相同参数，这只会每小时运行一次
    return make_api_request(endpoint)
```

#### `@shelve_me_today`
缓存函数结果一天。

```python
@shelve_me_today
def daily_report(date):
    # 对于相同参数，这只会每天运行一次
    return generate_report(date)
```

#### `@shelve_me`
永久缓存（无过期时间）。

```python
@shelve_me
def expensive_computation(input_data):
    # 对于相同参数，这只会运行一次
    return complex_calculation(input_data)
```

### 高级装饰器

#### `@shelve_it(howlong='time', update='')`
具有可配置过期时间和更新参数的高级装饰器。

**参数:**
- `howlong` (str): 过期时间 ('today', 'hour', 'week', 或 'time' 表示永久)
- `update` (str): 包含在缓存键中的额外字符串，用于手动缓存失效

```python
@shelve_it('hour', 'v2')
def versioned_function(data):
    # 缓存一小时，键中包含 'v2' 用于手动失效
    return process_data(data)
```

#### `@shelve_me_for_class`
专门用于类方法的装饰器，从缓存键中排除 `self` 参数。

```python
class MyClass:
    @shelve_me_for_class
    def expensive_method(self, param1, param2):
        # 只有 param1 和 param2 用于缓存键，不包括 self
        return self.compute(param1, param2)
```

### 缓存管理

#### `@shelve_del`
删除缓存数据而不是检索数据的装饰器。

```python
@shelve_del
def clear_cache(param):
    # 这将删除此函数和这些参数的缓存数据
    return "已删除"  # 总是返回 "已删除"
```

## 实用函数

### `get_module_path(function)`
获取包含给定函数的模块文件路径。

**参数:**
- `function`: 要获取模块路径的函数

**返回值:** 模块文件路径或 None

### `delShelveData(name, fn, args, kwargs)`
删除特定的缓存数据。

**参数:**
- `name` (str): 缓存键名称
- `fn` (callable): 函数（用于键生成）
- `args` (tuple): 函数参数
- `kwargs` (dict): 函数关键字参数

**返回值:** 被删除的数据

## 使用示例

### 基础用法

```python
import tools.shelveTool as st

# 简单缓存
@shelve_me
def get_user_data(user_id):
    # 昂贵的数据库查询
    return database.query_user(user_id)

# 基于时间的缓存
@shelve_me_hour
def fetch_stock_price(symbol):
    # 应该缓存一小时的 API 调用
    return api.get_stock_price(symbol)

# 周级缓存
@shelve_me_week
def generate_weekly_report(week_start):
    # 昂贵的报告生成
    return create_report(week_start)
```

### 高级用法

```python
# 可配置缓存与手动失效
@shelve_it('today', 'v1.2')
def process_data(data):
    return expensive_processing(data)

# 类方法缓存
class DataProcessor:
    @shelve_me_for_class
    def process(self, data, options):
        # 只有 data 和 options 用于缓存键
        return self.algorithm.process(data, options)

# 缓存删除
@shelve_del
def clear_old_cache(param):
    # 这将删除缓存数据
    pass
```

### 错误处理

抛出异常的函数不会被缓存：

```python
@shelve_me
def risky_function(param):
    if param < 0:
        raise ValueError("Invalid parameter")
    return param * 2

# 第一次使用无效参数调用：抛出异常，不缓存
# 第二次使用相同无效参数调用：再次抛出异常（未缓存）
```

## 缓存键生成

缓存键使用以下模式生成：
- 基础前缀：`'shelve_me'` 或 `'shelve_it'`
- 函数名
- 所有参数的字符串表示
- 所有关键字参数的字符串表示
- 基于时间的后缀（用于时间限制的缓存）
- 模块路径（用于 `@shelve_it` 装饰器）
- 更新字符串（用于 `@shelve_it` 装饰器）

## 最佳实践

1. **使用适当的过期时间**：根据数据变化频率选择合适的装饰器
2. **正确处理异常**：可能失败的函数应该有适当的错误处理
3. **使用描述性函数名**：缓存键包含函数名，所以要使其有意义
4. **考虑缓存大小**：监控您的 shelve 数据库大小，必要时清理旧数据
5. **测试缓存行为**：验证您的函数在有缓存和无缓存时都能正确工作

## 与其他项目的集成

要在其他项目中使用此模块：

1. 将 `shelveTool.py` 复制到您的项目
2. 创建一个包含 `FILEPATH` 枚举的 `Config.py` 文件
3. 确保 shelve 目录存在且可写
4. 根据需要导入和使用装饰器

```python
# 在您项目的 Config.py 中
from enum import Enum

class CustomEnum(Enum):
    def __repr__(self):
        return "%s.%s" % (self.__class__.__name__, self._name_)

class FILEPATH(CustomEnum):
    SHELVEDIR = "/path/to/your/shelve/directory"
```

## 注意事项

- 该模块使用 Python 的 `shelve` 模块，创建特定于平台的数据库文件
- 缓存键生成为字符串，因此所有参数必须可转换为字符串
- 该模块包含显示生成缓存键的调试打印
- 基于时间的缓存依赖于 `tools.timeTools` 模块进行时间计算
