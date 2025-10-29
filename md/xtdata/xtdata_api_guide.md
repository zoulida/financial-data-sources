# XtQuant.XtData 行情模块 API 指南

## 📋 概述

`xtdata` 是 `xtquant` 库中提供行情相关数据的核心模块，专为量化交易者设计，提供精简直接的数据需求。作为 Python 库，`xtdata` 可灵活集成到各种策略脚本中。

> **📌 重要提示**: 本指南包含了xtdata模块的主要字段和接口。如需查找更详细的字段信息或最新更新，请参考官方文档：[http://dict.thinktrader.net/nativeApi/xtdata.html?id=nOY9mc](http://dict.thinktrader.net/nativeApi/xtdata.html?id=nOY9mc)

### 主要功能
- **行情数据**：历史和实时的 K 线和分笔数据
- **财务数据**：完整的财务报表数据
- **合约基础信息**：股票、期货、期权等合约信息
- **板块和行业分类**：行业板块分类信息

## 🚀 快速开始

### 环境准备
```python
from xtquant import xtdata
import pandas as pd
import numpy as np
```

### 基本使用流程
1. **初始化**：设置 Token，初始化行情模块
2. **订阅数据**：订阅实时行情或下载历史数据
3. **获取数据**：通过接口获取所需数据
4. **数据处理**：转换为 DataFrame 进行后续分析

## 📊 核心接口说明

### 1. 行情数据接口

#### 1.1 订阅单股行情
```python
xtdata.subscribe_quote(stock_list, period, count)
```

**参数说明**：
- `stock_list` (list): 合约代码列表，如 `['000001.SZ', '000002.SZ']`
- `period` (str): 数据周期，支持 `1m`、`5m`、`1d`、`tick`、`10m`、`15m`、`30m`、`1h`、`1w`
- `count` (int): 订阅的数量

**示例**：
```python
# 订阅平安银行和万科A的日K线数据
xtdata.subscribe_quote(['000001.SZ', '000002.SZ'], '1d', 2)
```

#### 1.2 获取行情数据
```python
xtdata.get_market_data_ex(
    field_list=[], 
    stock_list=[], 
    period='1d', 
    start_time='', 
    end_time='', 
    count=-1, 
    dividend_type='none', 
    fill_data=True
)
```

**参数说明**：
- `field_list` (list): 数据字段列表，详情见下方字段说明
- `stock_list` (list): 合约代码列表
- `period` (str): 数据周期
- `start_time` (str): 数据起始时间，格式为 `%Y%m%d` 或 `%Y%m%d%H%M%S`
- `end_time` (str): 数据结束时间，格式为 `%Y%m%d` 或 `%Y%m%d%H%M%S`
- `count` (int): 数据个数，默认为 `-1` 表示获取所有数据
- `dividend_type` (str): 除权方式，可选 `'none'`、`'front'`、`'back'`
- `fill_data` (bool): 是否填充数据，默认 `True`

**返回值**：
- `period` 为 K 线周期时：返回字典，键为字段名，值为 `pd.DataFrame`
- `period` 为 `tick` 分笔周期时：返回字典，键为合约代码，值为 `np.ndarray`

**示例**：
```python
# 获取平安银行最近30天的日K线数据
data = xtdata.get_market_data_ex(
    field_list=['open', 'high', 'low', 'close', 'volume', 'amount'],
    stock_list=['000001.SZ'],
    period='1d',
    count=30
)
```

### 2. 财务数据接口

#### 2.1 获取财务数据
```python
xtdata.get_financial_data(stock_list, report_type, field_list, start_time, end_time)
```

**参数说明**：
- `stock_list` (list): 合约代码列表
- `report_type` (str): 财务报表类型
  - `'Balance'`: 资产负债表
  - `'Income'`: 利润表
  - `'CashFlow'`: 现金流量表
- `field_list` (list): 数据字段列表
- `start_time` (str): 数据起始时间，格式为 `%Y%m%d`
- `end_time` (str): 数据结束时间，格式为 `%Y%m%d`

**示例**：
```python
# 获取平安银行2023年资产负债表数据
balance_data = xtdata.get_financial_data(
    stock_list=['000001.SZ'],
    report_type='Balance',
    field_list=['totalAssets', 'totalLiabilities', 'totalEquity'],
    start_time='20230101',
    end_time='20231231'
)
```

### 3. 基础信息接口

#### 3.1 获取合约基础信息
```python
xtdata.get_instrument_detail(stock_code)
```

**参数说明**：
- `stock_code` (str): 合约代码

**返回值**：返回字典，包含合约的基础信息

**示例**：
```python
# 获取平安银行基础信息
info = xtdata.get_instrument_detail('000001.SZ')
print(f"股票名称: {info['InstrumentName']}")
print(f"交易所: {info['ExchangeID']}")
```

#### 3.2 下载历史数据
```python
xtdata.download_history_data(stock_list, period, start_time, end_time)
```

**参数说明**：
- `stock_list` (list): 合约代码列表
- `period` (str): 数据周期
- `start_time` (str): 开始时间
- `end_time` (str): 结束时间

#### 3.3 获取本地数据
```python
xtdata.get_local_data(field_list, stock_list, period, start_time, end_time)
```

**参数说明**：
- `field_list` (list): 字段列表
- `stock_list` (list): 合约代码列表
- `period` (str): 数据周期
- `start_time` (str): 开始时间
- `end_time` (str): 结束时间

#### 3.4 获取完整分笔数据
```python
xtdata.get_full_tick(stock_list, start_time, end_time)
```

**参数说明**：
- `stock_list` (list): 合约代码列表
- `start_time` (str): 开始时间
- `end_time` (str): 结束时间

#### 3.5 获取除权数据
```python
xtdata.get_divid_factors(stock_list, start_time, end_time)
```

**参数说明**：
- `stock_list` (list): 合约代码列表
- `start_time` (str): 开始时间
- `end_time` (str): 结束时间

#### 3.6 重新连接
```python
xtdata.reconnect(ip, port)
```

**参数说明**：
- `ip` (str): IP地址
- `port` (int): 端口号

## 📈 数据字段详解

> **📌 字段查找提示**: 本指南包含了xtdata模块的主要字段。如需查找其他字段或最新字段信息，请参考官方文档：[http://dict.thinktrader.net/nativeApi/xtdata.html?id=nOY9mc](http://dict.thinktrader.net/nativeApi/xtdata.html?id=nOY9mc)

### K 线数据字段

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `time` | int64 | 时间戳 |
| `open` | float64 | 开盘价 |
| `high` | float64 | 最高价 |
| `low` | float64 | 最低价 |
| `close` | float64 | 收盘价 |
| `volume` | float64 | 成交量（手） |
| `amount` | float64 | 成交额 |
| `settle` | float64 | 今结算价（期货） |
| `openInterest` | float64 | 持仓量（期货） |
| `preClose` | float64 | 前收盘价 |
| `suspendFlag` | int32 | 停牌标志，1表示停牌，0表示不停牌 |
| `lastPrice` | float64 | 最新价 |
| `lastSettlementPrice` | float64 | 前结算价（股票为0） |
| `settlementPrice` | float64 | 今结算价（股票为0） |
| `transactionNum` | int32 | 成交笔数（期货没有，单独计算） |
| `pvolume` | float64 | 原始成交总量（未经过股手转换） |

### 分笔数据字段（tick）

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `time` | int64 | 时间戳 |
| `stime` | str | 时间戳字符串形式 |
| `lastPrice` | float64 | 最新价 |
| `open` | float64 | 开盘价 |
| `high` | float64 | 最高价 |
| `low` | float64 | 最低价 |
| `lastClose` | float64 | 前收盘价 |
| `amount` | float64 | 成交总额 |
| `volume` | float64 | 成交总量（手） |
| `pvolume` | float64 | 原始成交总量（未经过股手转换） |
| `stockStatus` | int32 | 证券状态 |
| `openInterest` | float64 | 持仓量（股票表示状态，非股票为持仓量） |
| `transactionNum` | int32 | 成交笔数 |
| `lastSettlementPrice` | float64 | 前结算价（股票为0） |
| `settlementPrice` | float64 | 今结算价（股票为0） |
| `askPrice` | ndarray | 多档委卖价（1-10档） |
| `askVol` | ndarray | 多档委卖量（1-10档） |
| `bidPrice` | ndarray | 多档委买价（1-10档） |
| `bidVol` | ndarray | 多档委买量（1-10档） |
| `askPrice1` - `askPrice5` | float64 | 卖一价至卖五价 |
| `askVol1` - `askVol5` | float64 | 卖一量至卖五量 |
| `bidPrice1` - `bidPrice5` | float64 | 买一价至买五价 |
| `bidVol1` - `bidVol5` | float64 | 买一量至买五量 |

### 财务数据字段

#### 资产负债表（Balance）
- `m_anntime`: 披露日期
- `m_timetag`: 截止日期
- `internal_shoule_recv`: 内部应收款
- `fixed_capital_clearance`: 固定资产清理
- `should_pay_money`: 应付分保账款
- `settlement_payment`: 结算备付金
- `receivable_premium`: 应收保费
- `accounts_receivable_reinsurance`: 应收分保账款
- `reinsurance_contract_reserve`: 应收分保合同准备金
- `dividends_payable`: 应收股利
- `tax_rebate_for_export`: 应收出口退税
- `subsidies_receivable`: 应收补贴款
- `deposit_receivable`: 应收保证金
- `apportioned_cost`: 待摊费用
- `profit_and_current_assets_with_deal`: 待处理流动资产损益
- `current_assets_one_year`: 一年内到期的非流动资产
- `long_term_receivables`: 长期应收款
- `other_long_term_investments`: 其他长期投资
- `original_value_of_fixed_assets`: 固定资产原值
- `net_value_of_fixed_assets`: 固定资产净值
- `depreciation_reserves_of_fixed_assets`: 固定资产减值准备
- `productive_biological_assets`: 生产性生物资产
- `public_welfare_biological_assets`: 公益性生物资产
- `oil_and_gas_assets`: 油气资产
- `development_expenditure`: 开发支出
- `right_of_split_share_distribution`: 股权分置流通权
- `other_non_mobile_assets`: 其他非流动资产
- `handling_fee_and_commission`: 应付手续费及佣金
- `other_payables`: 其他应交款
- `margin_payable`: 应付保证金
- `internal_accounts_payable`: 内部应付款
- `advance_cost`: 预提费用
- `insurance_contract_reserve`: 保险合同准备金
- `broker_buying_and_selling_securities`: 代理买卖证券款
- `acting_underwriting_securities`: 代理承销证券款
- `international_ticket_settlement`: 国际票证结算
- `domestic_ticket_settlement`: 国内票证结算
- `deferred_income`: 递延收益
- `short_term_bonds_payable`: 应付短期债券
- `long_term_deferred_income`: 长期递延收益
- `undetermined_investment_losses`: 未确定的投资损失
- `quasi_distribution_of_cash_dividends`: 拟分配现金股利
- `provisions_not`: 预计负债
- `cust_bank_dep`: 吸收存款及同业存放
- `provisions`: 预计流动负债
- `less_tsy_stk`: 减:库存股
- `cash_equivalents`: 货币资金
- `loans_to_oth_banks`: 拆出资金
- `tradable_fin_assets`: 交易性金融资产
- `derivative_fin_assets`: 衍生金融资产
- `bill_receivable`: 应收票据
- `account_receivable`: 应收账款
- `advance_payment`: 预付款项
- `int_rcv`: 应收利息
- `other_receivable`: 其他应收款
- `red_monetary_cap_for_sale`: 买入返售金融资产
- `agency_bus_assets`: 以公允价值计量且其变动计入当期损益的金融资产
- `inventories`: 存货
- `other_current_assets`: 其他流动资产
- `total_current_assets`: 流动资产合计
- `loans_and_adv_granted`: 发放贷款及垫款
- `fin_assets_avail_for_sale`: 可供出售金融资产
- `held_to_mty_invest`: 持有至到期投资
- `long_term_eqy_invest`: 长期股权投资
- `invest_real_estate`: 投资性房地产
- `accumulated_depreciation`: 累计折旧
- `fix_assets`: 固定资产
- `constru_in_process`: 在建工程
- `construction_materials`: 工程物资
- `long_term_liabilities`: 长期负债
- `intang_assets`: 无形资产
- `goodwill`: 商誉
- `long_deferred_expense`: 长期待摊费用
- `deferred_tax_assets`: 递延所得税资产
- `total_non_current_assets`: 非流动资产合计
- `tot_assets`: 资产总计
- `shortterm_loan`: 短期借款
- `borrow_central_bank`: 向中央银行借款
- `loans_oth_banks`: 拆入资金
- `tradable_fin_liab`: 交易性金融负债
- `derivative_fin_liab`: 衍生金融负债
- `notes_payable`: 应付票据
- `accounts_payable`: 应付账款
- `advance_peceipts`: 预收账款
- `fund_sales_fin_assets_rp`: 卖出回购金融资产款
- `empl_ben_payable`: 应付职工薪酬
- `taxes_surcharges_payable`: 应交税费
- `int_payable`: 应付利息
- `dividend_payable`: 应付股利
- `other_payable`: 其他应付款
- `non_current_liability_in_one_year`: 一年内到期的非流动负债
- `other_current_liability`: 其他流动负债
- `total_current_liability`: 流动负债合计
- `long_term_loans`: 长期借款
- `bonds_payable`: 应付债券
- `longterm_account_payable`: 长期应付款
- `grants_received`: 专项应付款
- `deferred_tax_liab`: 递延所得税负债
- `other_non_current_liabilities`: 其他非流动负债
- `non_current_liabilities`: 非流动负债合计
- `tot_liab`: 负债合计
- `cap_stk`: 实收资本(或股本)
- `cap_rsrv`: 资本公积
- `specific_reserves`: 专项储备
- `surplus_rsrv`: 盈余公积
- `prov_nom_risks`: 一般风险准备
- `undistributed_profit`: 未分配利润
- `cnvd_diff_foreign_curr_stat`: 外币报表折算差额
- `tot_shrhldr_eqy_excl_min_int`: 归属于母公司股东权益合计
- `minority_int`: 少数股东权益
- `total_equity`: 所有者权益合计
- `tot_liab_shrhldr_eqy`: 负债和股东权益总计

#### 利润表（Income）
- `m_anntime`: 披露日期
- `m_timetag`: 截止日期
- `revenue_inc`: 营业收入
- `earned_premium`: 已赚保费
- `real_estate_sales_income`: 房地产销售收入
- `total_operating_cost`: 营业总成本
- `real_estate_sales_cost`: 房地产销售成本
- `research_expenses`: 研发费用
- `surrender_value`: 退保金
- `net_payments`: 赔付支出净额
- `net_withdrawal_ins_con_res`: 提取保险合同准备金净额
- `policy_dividend_expenses`: 保单红利支出
- `reinsurance_cost`: 分保费用
- `change_income_fair_value`: 公允价值变动收益
- `futures_loss`: 期货损益
- `trust_income`: 托管收益
- `subsidize_revenue`: 补贴收入
- `other_business_profits`: 其他业务利润
- `net_profit_excl_merged_int_inc`: 被合并方在合并前实现净利润
- `int_inc`: 利息收入
- `handling_chrg_comm_inc`: 手续费及佣金收入
- `less_handling_chrg_comm_exp`: 手续费及佣金支出
- `other_bus_cost`: 其他业务成本
- `plus_net_gain_fx_trans`: 汇兑收益
- `il_net_loss_disp_noncur_asset`: 非流动资产处置收益
- `inc_tax`: 所得税费用
- `unconfirmed_invest_loss`: 未确认投资损失
- `net_profit_excl_min_int_inc`: 归属于母公司所有者的净利润
- `less_int_exp`: 利息支出
- `other_bus_inc`: 其他业务收入
- `revenue`: 营业总收入
- `total_expense`: 营业成本
- `less_taxes_surcharges_ops`: 营业税金及附加
- `sale_expense`: 销售费用
- `less_gerl_admin_exp`: 管理费用
- `financial_expense`: 财务费用
- `less_impair_loss_assets`: 资产减值损失
- `plus_net_invest_inc`: 投资收益
- `incl_inc_invest_assoc_jv_entp`: 联营企业和合营企业的投资收益
- `oper_profit`: 营业利润
- `plus_non_oper_rev`: 营业外收入
- `less_non_oper_exp`: 营业外支出
- `tot_profit`: 利润总额
- `net_profit_incl_min_int_inc`: 净利润
- `net_profit_incl_min_int_inc_after`: 净利润(扣除非经常性损益后)
- `minority_int_inc`: 少数股东损益
- `s_fa_eps_basic`: 基本每股收益
- `s_fa_eps_diluted`: 稀释每股收益
- `total_income`: 综合收益总额
- `total_income_minority`: 归属于少数股东的综合收益总额
- `other_compreh_inc`: 其他收益

#### 现金流量表（CashFlow）
- `m_anntime`: 披露日期
- `m_timetag`: 截止日期
- `cash_received_ori_ins_contract_pre`: 收到原保险合同保费取得的现金
- `net_cash_received_rei_ope`: 收到再保险业务现金净额
- `net_increase_insured_funds`: 保户储金及投资款净增加额
- `Net`: 处置交易性金融资产净增加额
- `cash_for_interest`: 收取利息、手续费及佣金的现金
- `net_increase_in_repurchase_funds`: 回购业务资金净增加额
- `cash_for_payment_original_insurance`: 支付原保险合同赔付款项的现金
- `cash_payment_policy_dividends`: 支付保单红利的现金
- `disposal_other_business_units`: 处置子公司及其他收到的现金
- `cash_received_from_pledges`: 减少质押和定期存款所收到的现金
- `cash_paid_for_investments`: 投资所支付的现金
- `net_increase_in_pledged_loans`: 质押贷款净增加额
- `cash_paid_by_subsidiaries`: 取得子公司及其他营业单位支付的现金净额
- `increase_in_cash_paid`: 增加质押和定期存款所支付的现金
- `cass_received_sub_abs`: 其中子公司吸收现金
- `cass_received_sub_investments`: 其中:子公司支付给少数股东的股利、利润
- `minority_shareholder_profit_loss`: 少数股东损益
- `unrecognized_investment_losses`: 未确认的投资损失
- `ncrease_deferred_income`: 递延收益增加(减:减少)
- `projected_liability`: 预计负债
- `increase_operational_payables`: 经营性应付项目的增加
- `reduction_outstanding_amounts_less`: 已完工尚未结算款的减少(减:增加)
- `reduction_outstanding_amounts_more`: 已结算尚未完工款的增加(减:减少)
- `goods_sale_and_service_render_cash`: 销售商品、提供劳务收到的现金
- `net_incr_dep_cob`: 客户存款和同业存放款项净增加额
- `net_incr_loans_central_bank`: 向中央银行借款净增加额(万元)
- `net_incr_fund_borr_ofi`: 向其他金融机构拆入资金净增加额
- `tax_levy_refund`: 收到的税费与返还
- `cash_paid_invest`: 投资支付的现金
- `other_cash_recp_ral_oper_act`: 收到的其他与经营活动有关的现金
- `stot_cash_inflows_oper_act`: 经营活动现金流入小计
- `goods_and_services_cash_paid`: 购买商品、接受劳务支付的现金
- `net_incr_clients_loan_adv`: 客户贷款及垫款净增加额
- `net_incr_dep_cbob`: 存放中央银行和同业款项净增加额
- `handling_chrg_paid`: 支付利息、手续费及佣金的现金
- `cash_pay_beh_empl`: 支付给职工以及为职工支付的现金
- `pay_all_typ_tax`: 支付的各项税费
- `other_cash_pay_ral_oper_act`: 支付其他与经营活动有关的现金
- `stot_cash_outflows_oper_act`: 经营活动现金流出小计
- `net_cash_flows_oper_act`: 经营活动产生的现金流量净额
- `cash_recp_disp_withdrwl_invest`: 收回投资所收到的现金
- `cash_recp_return_invest`: 取得投资收益所收到的现金
- `net_cash_recp_disp_fiolta`: 处置固定资产、无形资产和其他长期投资收到的现金
- `other_cash_recp_ral_inv_act`: 收到的其他与投资活动有关的现金
- `stot_cash_inflows_inv_act`: 投资活动现金流入小计
- `cash_pay_acq_const_fiolta`: 购建固定资产、无形资产和其他长期投资支付的现金
- `stot_cash_outflows_inv_act`: 投资活动现金流出小计
- `net_cash_flows_inv_act`: 投资活动产生的现金流量净额
- `cash_recp_cap_contrib`: 吸收投资收到的现金
- `cash_recp_borrow`: 取得借款收到的现金
- `proc_issue_bonds`: 发行债券收到的现金
- `other_cash_recp_ral_fnc_act`: 收到其他与筹资活动有关的现金
- `stot_cash_inflows_fnc_act`: 筹资活动现金流入小计
- `cash_prepay_amt_borr`: 偿还债务支付现金
- `cash_pay_dist_dpcp_int_exp`: 分配股利、利润或偿付利息支付的现金
- `other_cash_pay_ral_fnc_act`: 支付其他与筹资的现金
- `stot_cash_outflows_fnc_act`: 筹资活动现金流出小计
- `net_cash_flows_fnc_act`: 筹资活动产生的现金流量净额
- `eff_fx_flu_cash`: 汇率变动对现金的影响
- `net_incr_cash_cash_equ`: 现金及现金等价物净增加额
- `cash_cash_equ_beg_period`: 期初现金及现金等价物余额
- `cash_cash_equ_end_period`: 期末现金及现金等价物余额
- `net_profit`: 净利润
- `plus_prov_depr_assets`: 资产减值准备
- `depr_fa_coga_dpba`: 固定资产折旧、油气资产折耗、生产性物资折旧
- `amort_intang_assets`: 无形资产摊销
- `amort_lt_deferred_exp`: 长期待摊费用摊销
- `decr_deferred_exp`: 待摊费用的减少
- `incr_acc_exp`: 预提费用的增加
- `loss_disp_fiolta`: 处置固定资产、无形资产和其他长期资产的损失
- `loss_scr_fa`: 固定资产报废损失
- `loss_fv_chg`: 公允价值变动损失
- `fin_exp`: 财务费用
- `invest_loss`: 投资损失
- `decr_deferred_inc_tax_assets`: 递延所得税资产减少
- `incr_deferred_inc_tax_liab`: 递延所得税负债增加
- `decr_inventories`: 存货的减少
- `decr_oper_payable`: 经营性应收项目的减少
- `others`: 其他
- `im_net_cash_flows_oper_act`: 经营活动产生现金流量净额
- `conv_debt_into_cap`: 债务转为资本
- `conv_corp_bonds_due_within_1y`: 一年内到期的可转换公司债券
- `fa_fnc_leases`: 融资租入固定资产
- `end_bal_cash`: 现金的期末余额
- `less_beg_bal_cash`: 现金的期初余额
- `plus_end_bal_cash_equ`: 现金等价物的期末余额
- `less_beg_bal_cash_equ`: 现金等价物的期初余额
- `im_net_incr_cash_cash_equ`: 现金及现金等价物的净增加额
- `tax_levy_refund`: 收到的税费返还

#### 主要指标（PershareIndex）
- `s_fa_ocfps`: 每股经营活动现金流量
- `s_fa_bps`: 每股净资产
- `s_fa_eps_basic`: 基本每股收益
- `s_fa_eps_diluted`: 稀释每股收益
- `s_fa_undistributedps`: 每股未分配利润
- `s_fa_surpluscapitalps`: 每股资本公积金
- `adjusted_earnings_per_share`: 扣非每股收益
- `du_return_on_equity`: 净资产收益率
- `sales_gross_profit`: 销售毛利率
- `inc_revenue_rate`: 主营收入同比增长
- `du_profit_rate`: 净利润同比增长
- `inc_net_profit_rate`: 归属于母公司所有者的净利润同比增长
- `adjusted_net_profit_rate`: 扣非净利润同比增长
- `inc_total_revenue_annual`: 营业总收入滚动环比增长
- `inc_net_profit_to_shareholders_annual`: 归属净利润滚动环比增长
- `adjusted_profit_to_profit_annual`: 扣非净利润滚动环比增长
- `equity_roe`: 加权净资产收益率
- `net_roe`: 摊薄净资产收益率
- `total_roe`: 摊薄总资产收益率
- `gross_profit`: 毛利率
- `net_profit`: 净利率
- `actual_tax_rate`: 实际税率
- `pre_pay_operate_income`: 预收款 / 营业收入
- `sales_cash_flow`: 销售现金流 / 营业收入
- `gear_ratio`: 资产负债比率
- `inventory_turnover`: 存货周转率
- `m_anntime`: 公告日
- `m_timetag`: 报告截止日

#### 股本表（Capital）
- `total_capital`: 总股本
- `circulating_capital`: 已上市流通A股
- `restrict_circulating_capital`: 限售流通股份
- `m_timetag`: 报告截止日
- `m_anntime`: 公告日

#### 十大股东/十大流通股东（Top10holder/Top10flowholder）
- `declareDate`: 公告日期
- `endDate`: 截止日期
- `name`: 股东名称
- `type`: 股东类型
- `quantity`: 持股数量
- `reason`: 变动原因
- `ratio`: 持股比例
- `nature`: 股份性质
- `rank`: 持股排名

#### 股东数（Holdernum）
- `declareDate`: 公告日期
- `endDate`: 截止日期
- `shareholder`: 股东总数
- `shareholderA`: A股东户数
- `shareholderB`: B股东户数
- `shareholderH`: H股东户数
- `shareholderFloat`: 已流通股东户数
- `shareholderOther`: 未流通股东户数

### 合约基础信息字段

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `ExchangeID` | str | 合约市场代码 |
| `InstrumentID` | str | 合约代码 |
| `InstrumentName` | str | 合约名称 |
| `Abbreviation` | str | 合约名称的拼音简写 |
| `ProductID` | str | 合约的品种ID（期货） |
| `ProductName` | str | 合约的品种名称（期货） |
| `UnderlyingCode` | str | 标的合约 |
| `ExtendName` | str | 扩位名称 |
| `ExchangeCode` | str | 交易所代码 |
| `RzrkCode` | str | rzrk代码 |
| `UniCode` | str | 统一规则代码 |
| `CreateDate` | str | 上市日期（期货） |
| `OpenDate` | str | IPO日期（股票） |
| `ExpireDate` | str | 退市日或者到期日 |
| `PreClose` | float | 前收盘价格 |
| `SettlementPrice` | float | 前结算价格 |
| `UpStopPrice` | float | 当日涨停价 |
| `DownStopPrice` | float | 当日跌停价 |
| `FloatVolume` | float | 流通股本 |
| `TotalVolume` | float | 总股本 |
| `AccumulatedInterest` | float | 自上市付息日起的累积未付利息额（债券） |
| `LongMarginRatio` | float | 多头保证金率 |
| `ShortMarginRatio` | float | 空头保证金率 |
| `PriceTick` | float | 最小变价单位 |
| `VolumeMultiple` | int | 合约乘数（对期货以外的品种，默认是1） |
| `MainContract` | int | 主力合约标记，1、2、3分别表示第一主力合约，第二主力合约，第三主力合约 |
| `MaxMarketOrderVolume` | int | 市价单最大下单量 |
| `MinMarketOrderVolume` | int | 市价单最小下单量 |
| `MaxLimitOrderVolume` | int | 限价单最大下单量 |
| `MinLimitOrderVolume` | int | 限价单最小下单量 |
| `MaxMarginSideAlgorithm` | int | 上期所大单边的处理算法 |
| `DayCountFromIPO` | int | 自IPO起经历的交易日总数 |
| `LastVolume` | float | 昨日持仓量 |
| `InstrumentStatus` | int | 合约停牌状态 |
| `IsTrading` | int | 合约是否可交易 |
| `IsRecent` | int | 是否是近月合约 |
| `IsContinuous` | int | 是否是连续合约 |
| `bNotProfitable` | int | 是否非盈利状态 |
| `bDualClass` | int | 是否同股不同权 |
| `ContinueType` | int | 连续合约类型 |
| `secuCategory` | int | 证券分类 |
| `secuAttri` | int | 证券属性 |
| `MaxMarketSellOrderVolume` | int | 市价卖单最大单笔下单量 |
| `MinMarketSellOrderVolume` | int | 市价卖单最小单笔下单量 |
| `MaxLimitSellOrderVolume` | int | 限价卖单最大单笔下单量 |
| `MinLimitSellOrderVolume` | int | 限价卖单最小单笔下单量 |
| `MaxFixedBuyOrderVol` | int | 盘后定价委托数量的上限（买） |
| `MinFixedBuyOrderVol` | int | 盘后定价委托数量的下限（买） |
| `MaxFixedSellOrderVol` | int | 盘后定价委托数量的上限（卖） |
| `MinFixedSellOrderVol` | int | 盘后定价委托数量的下限（卖） |
| `HSGTFlag` | int | 标识港股是否为沪港通或深港通标的证券。沪港通:0-非标的，1-标的，2-历史标的；深港通:0-非标的，3-标的，4-历史标的，5-是沪港通也是深港通 |
| `BondParValue` | float | 债券面值 |
| `QualifiedType` | int | 投资者适当性管理分类 |
| `PriceTickType` | int | 价差类别（港股用），1-股票，3-债券，4-期权，5-交易所买卖基金 |
| `tradingStatus` | int | 交易状态 |
| `OptUnit` | int | 期权合约单位 |
| `MarginUnit` | float | 期权单位保证金 |
| `OptUndlCode` | str | 期权标的证券代码或可转债正股标的证券代码 |
| `OptUndlMarket` | str | 期权标的证券市场或可转债正股标的证券市场 |
| `OptLotSize` | int | 期权整手数 |
| `OptExercisePrice` | float | 期权行权价或可转债转股价 |
| `NeeqExeType` | int | 全国股转转让类型，1-协议转让方式，2-做市转让方式，3-集合竞价+连续竞价转让方式（当前全国股转并未实现），4-集合竞价转让 |
| `OptExchFixedMargin` | float | 交易所期权合约保证金不变部分 |
| `OptExchMiniMargin` | float | 交易所期权合约最小保证金 |
| `Ccy` | str | 币种 |
| `IbSecType` | str | IB安全类型，期货或股票 |
| `OptUndlRiskFreeRate` | float | 期权标的无风险利率 |
| `OptUndlHistoryRate` | float | 期权标的历史波动率 |
| `EndDelivDate` | str | 期权行权终止日 |
| `RegisteredCapital` | float | 注册资本（单位:百万） |
| `MaxOrderPriceRange` | float | 最大有效申报范围 |
| `MinOrderPriceRange` | float | 最小有效申报范围 |
| `VoteRightRatio` | float | 同股同权比例 |
| `m_nMinRepurchaseDaysLimit` | int | 最小回购天数 |
| `m_nMaxRepurchaseDaysLimit` | int | 最大回购天数 |
| `DeliveryYear` | int | 交割年份 |
| `DeliveryMonth` | int | 交割月 |
| `ContractType` | int | 标识期权，1-过期，2-当月，3-下月，4-下季，5-隔季，6-隔下季 |
| `ProductTradeQuota` | float | 期货品种交易配额 |
| `ContractTradeQuota` | float | 期货合约交易配额 |
| `ProductOpenInterestQuota` | float | 期货品种持仓配额 |
| `ContractOpenInterestQuota` | float | 期货合约持仓配额 |
| `ChargeType` | int | 期货和期权手续费方式，0-未知，1-按元/手，2-按费率 |
| `ChargeOpen` | float | 开仓手续费率，-1表示没有 |
| `ChargeClose` | float | 平仓手续费率，-1表示没有 |
| `ChargeTodayOpen` | float | 开今仓（日内开仓）手续费率，-1表示没有 |
| `ChargeTodayClose` | float | 平今仓（日内平仓）手续费率，-1表示没有 |
| `OptionType` | int | 期权类型，-1为非期权，0为期权认购，1为期权认沽 |
| `OpenInterestMultiple` | float | 交割月持仓倍数 |

## 💻 完整使用示例

### 示例1：获取股票历史K线数据
```python
from xtquant import xtdata
import pandas as pd

# 初始化（需要先设置Token）
# xtdata.set_token('your_token_here')

# 获取平安银行最近100天的日K线数据
data = xtdata.get_market_data_ex(
    field_list=['open', 'high', 'low', 'close', 'volume', 'amount', 'preClose'],
    stock_list=['000001.SZ'],
    period='1d',
    count=100
)

# 转换为DataFrame
df = data['close'].T  # 转置，行为时间，列为股票
print(df.head())
```

### 示例2：获取多只股票的实时分笔数据
```python
# 订阅多只股票的分笔数据
xtdata.subscribe_quote(['000001.SZ', '000002.SZ', '600000.SH'], 'tick', 3)

# 获取分笔数据
tick_data = xtdata.get_market_data_ex(
    field_list=['time', 'lastPrice', 'volume', 'amount'],
    stock_list=['000001.SZ', '000002.SZ', '600000.SH'],
    period='tick',
    count=100
)

# 处理分笔数据
for stock_code, data in tick_data.items():
    print(f"{stock_code} 最新价: {data['lastPrice'][-1]}")
```

### 示例3：获取财务数据并分析
```python
# 获取多只股票的财务数据
financial_data = xtdata.get_financial_data(
    stock_list=['000001.SZ', '000002.SZ', '600000.SH'],
    report_type='Income',
    field_list=['totalRevenue', 'operatingProfit', 'netProfit'],
    start_time='20230101',
    end_time='20231231'
)

# 分析净利润
net_profit = financial_data['netProfit']
print("各公司净利润:")
print(net_profit)
```

## ⚠️ 重要注意事项

> **📌 官方文档**: 如需查找更详细的接口说明、字段列表或最新更新，请参考官方文档：[http://dict.thinktrader.net/nativeApi/xtdata.html?id=nOY9mc](http://dict.thinktrader.net/nativeApi/xtdata.html?id=nOY9mc)

### 1. 订阅限制
- 订阅有最大数量限制，超出限制可能导致数据重复或错误
- 如需订阅超过定义上限，可联系官方购买 VIP 服务

### 2. 数据获取方式
- **实时数据**：需要先订阅，再获取
- **历史数据**：可直接获取，建议先下载到本地

### 3. 时间格式要求
- 日期格式：`%Y%m%d`，如 `20240101`
- 日期时间格式：`%Y%m%d%H%M%S`，如 `20240101143000`

### 4. 数据权限
- 确保有相应的数据权限
- 部分数据可能需要特定的订阅权限

### 5. 性能优化
- 批量获取数据比单个获取更高效
- 合理设置 `count` 参数，避免获取过多不必要的数据

## 🔧 常用工具函数

### 数据转换工具
```python
def kline_to_dataframe(data_dict, stock_code):
    """将K线数据转换为DataFrame"""
    df = pd.DataFrame()
    for field, values in data_dict.items():
        if stock_code in values.columns:
            df[field] = values[stock_code]
    return df

def tick_to_dataframe(tick_data, stock_code):
    """将分笔数据转换为DataFrame"""
    if stock_code in tick_data:
        return pd.DataFrame(tick_data[stock_code])
    return pd.DataFrame()
```

### 数据验证工具
```python
def validate_data(data, required_fields):
    """验证数据是否包含必需字段"""
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        print(f"缺少字段: {missing_fields}")
        return False
    return True
```

## 📚 版本更新记录

- **2020-09-01**: 初稿
- **2020-09-07**: 添加获取除权数据的接口 `get_divid_factors`
- **2020-09-13**: 添加财务数据接口
- **2020-11-23**: 修正合约基础信息字段类型，添加数据字典
- **2021-07-20**: 添加新版下载数据接口
- **2021-12-30**: 调整数据字典，添加撤单信息区分说明
- **2022-06-27**: K线数据添加前收价、停牌标记字段
- **2022-09-30**: 添加交易日历相关接口
- **2023-01-04**: 添加千档行情获取
- **2023-01-31**: 可转债基础信息的下载和获取
- **2023-02-06**: 添加连接到指定IP端口的接口 `reconnect`
- **2023-02-07**: 支持QMT的本地Python模式
- **2023-03-27**: 新股申购信息获取
- **2023-04-13**: 本地Python模式下运行VBA函数
- **2023-07-27**: 文档部分描述修改
- **2023-08-21**: 数据接口支持投研版特色数据

## 📋 字段总结

### 支持的周期类型
- `1m`: 1分钟K线
- `5m`: 5分钟K线
- `10m`: 10分钟K线
- `15m`: 15分钟K线
- `30m`: 30分钟K线
- `1h`: 1小时K线
- `1d`: 日K线
- `1w`: 周K线
- `tick`: 分笔数据

### 常用字段组合

#### 基础行情字段
```python
basic_fields = ['time', 'open', 'high', 'low', 'close', 'volume', 'amount', 'preClose']
```

#### 完整K线字段
```python
kline_fields = ['time', 'open', 'high', 'low', 'close', 'volume', 'amount', 'preClose', 
                'settle', 'openInterest', 'suspendFlag', 'lastPrice', 'transactionNum']
```

#### 分笔数据字段
```python
tick_fields = ['time', 'stime', 'lastPrice', 'open', 'high', 'low', 'lastClose', 
               'amount', 'volume', 'pvolume', 'stockStatus', 'openInterest', 
               'transactionNum', 'askPrice1', 'askVol1', 'bidPrice1', 'bidVol1']
```

#### 财务数据常用字段
```python
# 资产负债表
balance_fields = ['totalAssets', 'totalLiabilities', 'totalEquity', 'currentAssets', 
                  'nonCurrentAssets', 'monetaryFunds', 'accountsReceivable', 'inventory']

# 利润表
income_fields = ['totalRevenue', 'operatingRevenue', 'operatingCost', 'operatingProfit', 
                 'netProfit', 'grossProfit', 'earningsPerShare']

# 现金流量表
cashflow_fields = ['operatingCashFlow', 'investingCashFlow', 'financingCashFlow', 
                   'netCashFlow', 'cashAndCashEquivalentsAtEnd']
```

## 🔍 数据获取最佳实践

### 1. 数据获取策略
- **历史数据**: 使用 `download_history_data` 先下载到本地，再用 `get_local_data` 获取
- **实时数据**: 使用 `subscribe_quote` 订阅，再用 `get_market_data_ex` 获取
- **分笔数据**: 使用 `get_full_tick` 获取完整分笔数据

### 2. 性能优化建议
- 批量获取数据比单个获取更高效
- 合理设置时间范围，避免获取过多不必要的数据
- 使用本地数据接口提高获取速度
- 根据需求选择合适的字段，避免获取无用数据

### 3. 错误处理
```python
try:
    data = xtdata.get_market_data_ex(field_list, stock_list, period, count=100)
    if data and len(data) > 0:
        print("数据获取成功")
    else:
        print("数据为空")
except Exception as e:
    print(f"数据获取失败: {e}")
```

---

**使用提示**: 将此文档提供给Cursor AI时，AI将能够根据您的需求自动选择合适的接口和参数，生成相应的xtdata数据获取代码。所有参数含义和字段说明都已详细包含在此文档中，确保数据获取的完整性和准确性。

**官方文档**: 如需查找更详细的字段信息、接口说明或最新更新，请参考官方文档：[http://dict.thinktrader.net/nativeApi/xtdata.html?id=nOY9mc](http://dict.thinktrader.net/nativeApi/xtdata.html?id=nOY9mc)
