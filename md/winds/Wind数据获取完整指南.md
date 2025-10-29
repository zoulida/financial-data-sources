# Wind数据获取完整指南

## 📋 概述

本指南提供了使用Wind API获取金融数据的完整方法，包括WSD（时间序列数据）和WSS（截面数据）的使用方法，以及所有2997个可用字段的详细映射。
注意：如果wss数据获取不到，可试试昨天日期获取wsd数据

> **📌 字段查找提示**: 本指南展示了主要字段类别，完整的2997个字段映射请参考同目录下的 `md/winds/merged_fields_fixed.txt` 文档。

## 🚀 快速开始

### 环境准备
```python
from WindPy import w
import pandas as pd
```

### 基本使用流程
1. 初始化Wind接口：`w.start()`
2. 调用数据接口：`w.wsd()` 或 `w.wss()`
3. 检查错误：`if data.ErrorCode != 0`
4. 处理数据：转换为DataFrame
5. 关闭接口：`w.stop()`

## 📊 API接口说明

### WSD (Wind Series Data) - 时间序列数据
用于获取历史时间序列数据，如股价、成交量等。

**基本语法：**
```python
data = w.wsd(
    codes="股票代码",           # 如: "000001.SZ"
    fields="字段列表",          # 如: "close,volume,amt"
    beginTime="开始日期",       # 如: "20240101"
    endTime="结束日期",         # 如: "20241231"
    options="可选参数"          # 如: "Period=W;Days=Trading"
)
```

### WSS (Wind Series Snapshot) - 截面数据
用于获取特定时点的截面数据，如基本信息、估值指标等。

**基本语法：**
```python
data = w.wss(
    codes="股票代码列表",       # 如: ["000001.SZ", "000002.SZ"]
    fields="字段列表",          # 如: "sec_name,pe_ttm,pb_mrq"
    options="可选参数"          # 如: "tradeDate=20241201"
)
```

## 🔧 常用参数说明

### WSD常用options
- `Period=W`: 周数据
- `Period=M`: 月数据  
- `Period=Q`: 季数据
- `Days=Trading`: 仅交易日
- `Fill=Previous`: 前向填充
- `PriceAdj=F`: 不复权
- `PriceAdj=B`: 后复权
- `PriceAdj=FQ`: 前复权

### WSS常用options
- `tradeDate=20241201`: 指定交易日期
- `unit=1`: 数据单位
- `rptDate=20241201`: 报告期日期
- `currencyType=`: 币种类型

## 💻 代码示例

### 示例1：获取股票历史行情数据
```python
from WindPy import w
import pandas as pd

# 初始化Wind接口
w.start()

# 获取平安银行历史行情数据
data = w.wsd(
    codes="000001.SZ",
    fields="close,open,high,low,volume,amt,pct_chg,turn",
    beginTime="2024-01-01",
    endTime="2024-12-31",
    options="Days=Trading"
)

# 检查错误
if data.ErrorCode != 0:
    print(f"错误代码: {data.ErrorCode}")
    print(f"错误信息: {data.Data}")
else:
    # 转换为DataFrame
    df = pd.DataFrame(data.Data, columns=data.Fields, index=data.Times)
    df.index.name = 'Date'
    print("数据获取成功")
    print(df.head())

# 关闭Wind接口
w.stop()
```

### 示例2：获取多只股票的基本信息
```python
from WindPy import w
import pandas as pd

# 初始化Wind接口
w.start()

# 获取多只股票基本信息
data = w.wss(
    codes=["000001.SZ", "000002.SZ", "600000.SH"],
    fields="sec_name,comp_name,industry_sw,pe_ttm,pb_mrq,val_mv_ARD",
    options="tradeDate=20241201"
)

# 检查错误
if data.ErrorCode != 0:
    print(f"错误代码: {data.ErrorCode}")
else:
    # 转换为DataFrame
    df = pd.DataFrame(data.Data, columns=data.Fields, index=data.Codes)
    df.index.name = 'Code'
    print("数据获取成功")
    print(df)

# 关闭Wind接口
w.stop()
```

## 📈 完整字段映射表

**重要提示**: 本指南包含了Wind API支持的所有2997个字段映射。如需查找特定字段，请参考同目录下的 `./merged_fields_fixed.txt` 文档，该文档包含完整的字段列表。

以下是按类别分组的主要字段映射：

### 【1】基本资料字段
```
证券简称 -> sec_name
同公司B股简称 -> bsharename
证券英文简称 -> sec_englishname
上市日期 -> ipo_date
交易所中文名称 -> exchange_cn
交易所英文简称 -> exch_eng
上市板 -> mkt
证券存续状态 -> sec_status
戴帽摘帽时间 -> riskadmonition_date
摘牌日期 -> delist_date
发行币种 -> issuecurrencycode
交易币种 -> curr
交易结算模式 -> fund_settlementmode
每股面值 -> parvalue
每手股数 -> lotsize
交易单位 -> tunit
上市地所属国家或地区代码 -> country
发布机构 -> crm_issuer
基期 -> basedate
基点 -> basevalue
成份个数 -> numberofconstituents
成份个数（支持历史） -> numberofconstituents2
最早成份日期 -> firstdayofconstituents
加权方式 -> methodology
证券简介 -> repo_briefing
发布日期 -> launchdate
证券曾用名 -> prename
证券简称（支持历史） -> sec_name1
上市地点 -> exch_city
跟踪标的基金代码 -> trackedbyfunds
上级行业指数代码 -> superiorcode
Wind代码 -> windcode
证券代码 -> trade_code
股票种类 -> stockclass
发行制度 -> ipo_issuingsystem
所属上市标准 -> liststd
北交所准入标准 -> featuredliststd
是否属于重要指数成份 -> compindex2
所属概念板块 -> concept
所属热门概念 -> hotconcept
所属最新概念 -> latestconcept
所属规模风格类型 -> scalestyle
是否融资融券标的 -> marginornot
是否沪港通买入标的 -> SHSC
是否深港通买入标的 -> SHSC2
纳入港股通日期 -> hksc_date
是否并行代码 -> parallelcode
证券类型 -> sec_type
证券类型（细类） -> sec_type_de
是否借壳上市 -> backdoor
借壳上市日期 -> backdoordate
是否上市（挂牌） -> list
是否属于风险警示板 -> riskwarning
指数分类(Wind) -> windtype
指数风格 -> officialstyle
所属产业链板块 -> chain
所属大宗商品概念板块 -> largecommodity
是否属于指数成份 -> compindex3
每份DR代表股份数 -> RO
已发行DR数量 -> share_dr
基础证券Wind代码 -> underlyingwindcode2
存托机构 -> depositarybank
公司中文名称 -> comp_name
公司英文名称 -> comp_name_eng
企业所有制性质 -> nature1
金融机构类型 -> institutiontype
企业规模 -> corpscale
上市公司（银行）类型 -> banktype
成立日期 -> founddate1
注册资本 -> regcapital
注册资本币种 -> regcapitalcur
法定代表人 -> chairman
法定代表人（支持历史） -> legalrepresentative
会计年结日 -> fiscaldate
经营范围 -> business
公司简介 -> briefing
主营产品类型 -> majorproducttype
主营产品名称 -> majorproductname
员工总数 -> employee
母公司员工人数 -> employee_pc
所属行政区划 -> administrativedivision
所属行政区划代码 -> admincode
所属证监会辖区 -> csrcjurisdiction
省份 -> province
城市 -> city
注册地址 -> address
注册地所在国家或地区 -> area
办公地址 -> office
邮编 -> zipcode
公司电话 -> phone
公司传真 -> fax
公司电子邮件地址 -> email
公司网站 -> website
信息披露人 -> discloser
信息指定披露媒体 -> media
统一社会信用代码 -> registernumber
公司发行债券一览 -> relatedbond
组织机构代码 -> organizationcode
记账本位币 -> report_cur
是否上市公司 -> listingornot1
是否上市公司 -> listingornot
单一债务主体中文简称 -> issuershortened
主要产品及业务 -> mainproduct
公司曾用名 -> compprename
是否发行可转债 -> cbissueornot
是否IPO时尚未盈利 -> earning
是否存在投票权差异 -> vote
是否专精特新企业 -> zjtxornot
是否企业本身为专精特新 -> zjtxitselfornot
是否高新技术企业 -> gxjsornot
是否企业的参控股公司为专精特新企业 -> ckgzjtxornot
是否VIE结构 -> vieornot
是否SPAC上市 -> spacornot
所属Wind行业名称(2024) -> wicsname2024
所属Wind行业代码(2024) -> wicscode2024
所属Wind行业指数代码 -> indexcode_wind
所属Wind行业指数代码（港股） -> indexcode_wind_hk
所属Wind主题行业名称 -> thematicindustry_wind
所属Wind主题行业指数代码 -> indexcode_windthematic
所属中上协行业名称 -> industry_csrc2023
所属中上协行业代码 -> industry_csrccode2023
所属申万行业名称(2014) -> industry_sw
所属申万行业代码(2014) -> industry_swcode
所属申万行业原始代码(2014) -> industry_sworigincode
所属申万行业指数代码 -> indexcode_sw
所属申万行业名称(2021) -> industry_sw_2021
所属申万行业代码(2021) -> industry_swcode_2021
所属申万行业原始代码(2021) -> industry_sworigincode_2021
所属申万行业名称（港股）(2014) -> industry_sw_hk
所属申万行业代码（港股）(2014) -> industry_swcode_hk
所属申万行业名称（港股）(2021) -> industry_sw_2021_hk
所属申万行业代码（港股）(2021) -> industry_swcode_2021_hk
所属中信行业名称 -> industry_citic
所属中信行业代码 -> industry_citiccode
所属中信行业原始代码 -> industry_citicorigincode
所属中信行业指数代码 -> indexcode_citic
所属中信风格指数代码 -> styleindexcode_citic
所属中信风格指数名称 -> styleindexname_citic
所属中信证券港股通指数代码（港股） -> indexcode_citic_hk
所属中信证券港股通指数名称（港股） -> indexname_citic_hk
所属中信行业名称（港股） -> industry_citic_hk
所属中信行业代码（港股） -> industry_citiccode_hk
所属恒生行业名称 -> industry_HS
所属恒生综合行业指数名称 -> indexname_hs
```

### 【6】市场行情字段
```
前收盘价 -> pre_close
交易所前收盘价 -> pre_close_exch
开盘价 -> open
最高价 -> high
最低价 -> low
收盘价 -> close
正股收盘价 -> dq_stockclose
成交量 -> volume
成交量（含大宗交易） -> volume_btin
成交额 -> amt
成交额（含大宗交易） -> amount_btin
成交笔数 -> dealnum
盘后成交量 -> volume_aht
盘后成交额 -> amount_aht
涨跌 -> chg
涨跌幅 -> pct_chg
振幅 -> swing
均价 -> vwap
复权因子 -> adjfactor
收盘价（支持定点复权） -> close2
换手率 -> turn
换手率（基准.自由流通股本） -> free_turn_n
换手率（基准.流通市值） -> dq_amtturnover
持仓量 -> oi
持仓量变化 -> oi_chg
持仓量（商品指数） -> oi_index
持仓量变化（商品指数） -> oichange
持仓额（不计保证金） -> oiamount_nomargin
持仓额 -> oiamount
前结算价 -> pre_settle
结算价 -> settle
结算价（支持复权） -> dq_settle
涨跌（收盘价） -> dq_change_close
涨跌（结算价） -> chg_settlement
涨跌幅（收盘价） -> pctchange_close
涨跌幅（结算价） -> pct_chg_settlement
最近交易日期 -> lastradeday_s
最早交易日期 -> firstradeday_s
市场最近交易日 -> last_trade_day
相对发行价涨跌 -> rel_ipo_chg
相对发行价涨跌幅 -> rel_ipo_pct_chg
交易状态 -> trade_status
总市值 -> val_mv_ARD
流通市值 -> val_mvc
连续停牌天数 -> susp_days
停牌原因 -> susp_reason
涨跌停状态 -> maxupordown
涨停价 -> maxup
跌停价 -> maxdown
贵金属现货特殊时点价 -> dq_price_premetals
升贴水 -> discount
升贴水率 -> discount__ratio
开盘价（不前推） -> open3
最高价（不前推） -> high3
最低价（不前推） -> low3
收盘价（不前推） -> close3
所属指数权重 -> indexweight
结算价（不前推） -> settle3
持仓量（不前推） -> oi3
收盘价(23：30) -> close_FX
收盘价（美元） -> close_usd
AH股溢价率 -> premiumrate_ah
交收方向（黄金现货） -> direction_gold
交收量（黄金现货） -> dquantity_gold
收盘价（夜盘） -> close_night
夜盘收盘价（支持复权） -> dq_close_night
换手率（基准.自由流通股本） -> free_turn
开盘集合竞价成交价 -> open_auction_price
开盘集合竞价成交量 -> open_auction_volume
开盘集合竞价成交额 -> open_auction_amount
周最高价 -> wq_high
周最低价 -> wq_low
周涨跌幅 -> wq_pctchange
周换手率 -> wq_turn
周成交量 -> wq_volume
周成交额 -> wq_amount
月涨跌幅 -> mq_pctchange
月换手率 -> mq_turn
月成交量 -> mq_volume
月成交额 -> mq_amount
年涨跌幅 -> yq_pctchange
年换手率 -> yq_turn
年成交量 -> yq_volume
年成交额 -> yq_amount
```

### 【7】证券分析字段
```
总市值1 -> ev
总市值2 -> mkt_cap_ard
总市值1（币种可选） -> ev3
总市值2（币种可选） -> mkt_cap_ard2
市盈率PE(LYR,加权) -> val_pe_wgt
市盈率PE(TTM) -> pe_ttm
市盈率PE(TTM,加权) -> val_pe_ttmwgt
发布方市盈率PE(TTM) -> val_pe_ttm_issuer
市盈率PE(TTM,剔除负值) -> val_pe_nonnegative
市盈率PE(TTM,中位数) -> val_pe_median
市盈率PE(TTM,扣除非经常性损益) -> val_pe_deducted_ttm
市盈率PE(LYR) -> pe_lyr
市净率PB(MRQ) -> pb_mrq
市净率PB(LF,内地) -> pb_lf
市净率PB(MRQ,海外) -> pb_mrq_gsd
发布方市净率PB(LF) -> val_pb_If_issuer
市净率PB(LYR) -> pb_lyr
市销率PS(TTM) -> ps_ttm
市销率PS(TTM,加权) -> val_ps_ttmwgt
市销率PS(LYR) -> ps_lyr
市现率PCF(经营现金流TTM) -> pcf_ocf_ttm
市现率PCF(经营现金流TTM,加权) -> val_pcf_ocfttmwgt
市现率PCF(现金净流量TTM) -> pcf_ncf_ttm
市现率PCF(经营性净现金流LYR) -> pcf_ocflyr
市现率PCF(现金净流量LYR) -> pcf_nflyr
股息率（报告期） -> dividendyield
股息率（近12个月） -> dividendyield2
股息率TTM -> val_dividendyield3
股息率TTM(剔除特别派息) -> val_dividendyield4
发布方股息率（近12个月） -> val_dividendyield2_issuer
预测PE -> pe_est
预测PEG -> est_peg
预测PB -> estpb
企业价值（含货币资金） -> ev1
企业价值（剔除货币资金） -> ev2
企业倍数(EV/EBITDA) -> ev2_to_ebitda
企业倍数2(EV/EBITDA) -> val_evtoebitda2
总市值（不可回测） -> mkt_cap
总市值（证监会算法） -> mkt_cap_CSRC
自由流通市值 -> mkt_freeshares
流通市值（含限售股） -> mkt_cap_float
A股市值（含限售股） -> mkt_cap_ashare2
A股市值（不含限售股） -> mkt_cap_ashare
B股市值（含限售股，交易币种） -> val_bshrmarketvalue4
B股市值（含限售股，折人民币） -> val_bshrmarketvalue3
B股市值（不含限售股，交易币种） -> val_bshrmarketvalue2
B股市值（不含限售股，折人民币） -> val_bshrmarketvalue
市盈率PE -> pe
市净率PB -> pb
市销率PS -> ps
市现率PCF(现金净流量) -> pcf_ncf
市现率PCF(经营现金流) -> pcf_ocf
历史PEG -> peg
```

**注意**: 由于字段数量庞大（共2997个），这里仅展示了主要类别的部分字段。完整的字段列表请参考原始文档 `src/winds/merged_fields_fixed.txt`。

### 其他重要字段类别
- **【8】账务数据**: 包含各种财务比率和指标
- **【9】财务报表**: 包含资产负债表、利润表、现金流量表等详细科目
- **【10】财务报表**: 现金流量表补充数据
- **【11】权益事件**: 分红、配股、IPO等权益相关事件
- **【12】投资组合**: 基金资产配置相关数据
- **【13】量化因子**: 各种量化分析因子
- **【14】其他**: 技术指标和其他辅助数据

## ⚠️ 注意事项

1. **字段查找**: 优先参考本指南中的字段映射表，如需查找其他字段，请直接查看同目录下的 `./merged_fields_fixed.txt` 文档（包含全部2997个字段）
2. **错误处理**: 每次调用后都要检查 `ErrorCode` 是否为0
3. **资源管理**: 使用完毕后调用 `w.stop()` 关闭Wind接口
4. **数据格式**: Wind返回的数据结构包含 `Data`, `Codes`, `Fields`, `Times` 等字段
5. **日期格式**: 支持多种日期格式，如 "20240101", "2024-01-01", "-5D" 等
6. **股票代码**: 使用Wind标准代码格式，如 "000001.SZ", "600000.SH"
7. **数据权限**: 确保有相应的Wind数据权限

## 🔍 数据后处理建议

```python
import pandas as pd

# 将Wind数据转换为DataFrame
df = pd.DataFrame(data.Data, columns=data.Fields, index=data.Times)
df.index.name = 'Date'

# 或者按股票代码组织数据
df_dict = {}
for i, code in enumerate(data.Codes):
    df_dict[code] = pd.DataFrame(
        [row[i] for row in data.Data], 
        columns=data.Fields, 
        index=data.Times
    )

# 数据清洗
df = df.dropna()  # 删除缺失值
df = df[df['volume'] > 0]  # 过滤无成交数据

# 计算技术指标
df['ma5'] = df['close'].rolling(5).mean()  # 5日均线
df['ma20'] = df['close'].rolling(20).mean()  # 20日均线
```

## 📞 技术支持

如遇到问题，请检查：
1. Wind接口是否正确初始化
2. 股票代码格式是否正确
3. 字段名称是否拼写正确
4. 是否有相应的数据权限
5. 网络连接是否正常

## 📋 完整字段文档

本指南包含了Wind API支持的所有2997个字段的完整映射。如需查看特定字段的详细信息，请参考：

- **完整字段列表**: `src/winds/merged_fields_fixed.txt`
- **字段总数**: 2997个
- **分类数量**: 14个主要类别
- **覆盖范围**: 基本资料、市场行情、财务数据、技术指标、量化因子等

---

**使用提示**: 将此文档提供给Cursor AI时，AI将能够根据您的需求自动选择合适的字段和参数，生成相应的Wind数据获取代码。所有2997个字段的映射关系都已包含在此文档中，确保数据获取的完整性和准确性。
