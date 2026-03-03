# Wind财务分析程序

本目录包含用于从Wind获取财务指标并生成资产负债表柱状图的程序。

## 🎯 推荐使用

### `final_balance_chart.py` - 最终推荐版本 ⭐
- **功能最完整**，支持Wind真实数据和示例数据两种模式
- **智能降级**：Wind数据获取失败时自动询问是否使用示例数据
- **多股票支持**：内置贵州茅台、平安银行、万科A等示例数据
- **命令行友好**：支持命令行参数和交互式操作
- **错误处理完善**：详细的错误提示和解决方案

## 📁 文件说明

### 主要程序
1. **`final_balance_chart.py`** - 最终推荐版本（建议使用）
2. `wind_balance_sheet_chart.py` - 完整版程序
3. `simple_balance_chart.py` - 简化版程序  
4. `basic_balance_chart.py` - 基础字段版

### 测试和调试程序
5. `test_wind_data.py` - Wind数据获取测试
6. `simple_test.py` - 简单测试
7. `debug_balance_chart.py` - 调试版本
8. `wsd_test_chart.py` - WSD接口测试

## 📊 财务指标说明

程序获取以下13个关键财务指标：

### 资产类指标（蓝色显示）
- **现金**: 货币资金
- **应收款**: 应收款项
- **预付款**: 预付款项
- **存货**: 存货
- **固定资产**: 固定资产
- **其他流动**: 其他流动资产
- **无形资产**: 无形资产
- **其他非流动**: 其他非流动资产

### 负债类指标（红色显示）
- **短期借款**: 短期借款
- **应付款**: 应付款项
- **预收款**: 预收账款
- **薪酬&税**: 应付职工薪酬
- **长期借款**: 长期借款

## 🚀 使用方法

### 环境要求
```bash
pip install WindPy pandas matplotlib numpy
```

### 运行最终推荐版本

#### 1. 使用示例数据（推荐新手）
```bash
cd "d:\pythonProject\数据源\src\基本面\财务分析"
python final_balance_chart.py --sample
```

#### 2. 尝试获取Wind真实数据
```bash
python final_balance_chart.py 600519.SH 2025-06-30
```
如果Wind数据获取失败，程序会询问是否使用示例数据继续。

#### 3. 指定不同股票
```bash
# 平安银行
python final_balance_chart.py 000001.SZ --sample

# 万科A
python final_balance_chart.py 000002.SZ --sample
```

#### 4. 查看帮助信息
```bash
python final_balance_chart.py --help
```

### 其他程序使用方法

#### 简化版程序
```bash
python simple_balance_chart.py
```

#### 完整版程序
```bash
# 使用默认参数（贵州茅台，2025-06-30）
python wind_balance_sheet_chart.py

# 指定股票代码
python wind_balance_sheet_chart.py 000001.SZ

# 指定股票代码和报告期
python wind_balance_sheet_chart.py 600519.SH 2024-12-31
```

## 📋 Wind字段映射

程序使用的Wind字段映射关系：

| 中文名称 | Wind字段 | 说明 |
|---------|----------|------|
| 现金 | monetary_cap | 货币资金 |
| 短期借款 | st_borrow | 短期借款 |
| 应收款 | tot_acct_rcv | 应收款项 |
| 应付款 | tot_acct_payable | 应付款项 |
| 预付款 | prepay | 预付款项 |
| 预收款 | adv_from_cust | 预收账款 |
| 存货 | inventories | 存货 |
| 薪酬&税 | empl_ben_payable | 应付职工薪酬 |
| 固定资产 | fix_assets | 固定资产 |
| 其他流动 | oth_cur_assets | 其他流动资产 |
| 无形资产 | intang_assets | 无形资产 |
| 长期借款 | lt_borrow | 长期借款 |
| 其他非流动 | oth_non_cur_assets | 其他非流动资产 |

## 📤 输出说明

### 控制台输出
程序会在控制台显示：
- 获取的财务数据（以亿元为单位）
- 数据来源（Wind真实数据/示例数据）
- 处理进度信息
- 图表保存路径

### 图表输出
- 生成PNG格式的柱状图
- 文件名格式：`{股票代码}_资产负债表_{日期}_{数据源}.png`
- 资产类指标用蓝色显示
- 负债类指标用红色显示
- 包含数值标签和图例
- 显示数据来源（Wind数据或示例数据）

## ⚠️ 注意事项

### Wind数据获取
1. **Wind权限**: 确保Wind终端已登录且有相应数据权限
2. **报告期**: 如果指定日期无数据，Wind会返回None
3. **股票代码**: 使用Wind标准格式，如"600519.SH"、"000001.SZ"
4. **数据单位**: 示例数据单位为亿元，Wind数据单位为元（程序自动转换）

### 常见问题

#### Wind数据获取失败
如果遇到Wind数据获取失败的情况：
1. 检查Wind终端是否正常运行
2. 确认网络连接正常
3. 验证是否有相应的数据权限
4. 使用`--sample`参数查看示例效果

#### 中文字体显示问题
如果图表中文字符显示异常：
1. 确保系统安装了中文字体
2. 程序已设置多种中文字体备选
3. 可以修改字体设置：`plt.rcParams['font.sans-serif'] = ['你的字体名']`

## 🔧 故障排除

### Wind连接问题
```bash
# 测试Wind基本连接
python simple_test.py
```

### 数据字段问题
```bash
# 测试不同字段
python test_wind_data.py
```

### 调试模式
```bash
# 查看详细调试信息
python debug_balance_chart.py
```

## 🎨 示例数据说明

程序内置了以下股票的示例数据：
- **600519.SH (贵州茅台)**: 白酒行业，存货和预收款较高
- **000001.SZ (平安银行)**: 银行业，无存货，现金和贷款较高
- **000002.SZ (万科A)**: 房地产行业，存货极高，长期借款较高

示例数据基于真实财务结构模拟，用于展示图表效果。

## 📈 扩展功能

可以根据需要扩展以下功能：
- 添加更多财务指标
- 支持多股票对比图表
- 添加时间序列分析
- 导出Excel格式数据
- 添加更多图表类型（饼图、折线图等）
- 集成到量化分析框架

## 📚 技术支持

### 参考文档
1. Wind API文档
2. 字段映射文件：`d:\pythonProject\数据源\md\winds\merged_fields_fixed.txt`
3. Wind数据获取指南：`d:\pythonProject\数据源\md\winds\Wind数据获取完整指南.md`

### 程序架构
```
财务分析程序
├── 数据获取层
│   ├── Wind API接口 (WSS/WSD)
│   └── 示例数据生成
├── 数据处理层
│   ├── 字段映射
│   ├── 数据清洗
│   └── 格式转换
└── 可视化层
    ├── 图表生成
    ├── 样式设置
    └── 文件输出
```

## 📞 联系方式

如有问题或建议，请：
1. 检查本文档的故障排除部分
2. 查看程序输出的错误信息
3. 参考Wind官方文档
4. 使用测试程序进行调试

---

**更新日志**:
- v1.0: 基础版本，支持Wind数据获取
- v2.0: 添加示例数据支持
- v3.0: 最终版本，智能降级和多股票支持
