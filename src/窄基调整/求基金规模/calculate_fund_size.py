"""
指数基金规模汇总计算脚本
功能：按跟踪指数代码汇总基金规模，并添加指数名称
"""
import pandas as pd

def calculate_index_fund_size(excel_path, output_path=None):
    """
    计算每个跟踪指数的基金规模总和
    
    参数:
        excel_path: Excel文件路径
        output_path: 输出CSV文件路径，如果不指定则自动生成
    
    返回:
        pandas.DataFrame: 汇总结果
    """
    # 读取 Excel 文件
    df = pd.read_excel(excel_path, engine='openpyxl')
    
    # 从数据结构来看：
    # 索引2：跟踪指数代码
    # 索引3：跟踪指数名称
    # 索引4：当前规模(亿元)
    
    # 提取关键列
    df['跟踪指数代码'] = df.iloc[:, 2]
    df['跟踪指数名称'] = df.iloc[:, 3]
    df['当前规模'] = df.iloc[:, 4]
    
    # 显示前几行数据
    print("前5行数据:")
    print(df[['跟踪指数代码', '跟踪指数名称', '当前规模']].head())
    
    # 确保规模列为数值类型
    df['当前规模'] = pd.to_numeric(df['当前规模'], errors='coerce')
    
    # 删除规模为 NaN 的行
    df = df.dropna(subset=['当前规模'])
    
    print(f"\n有效数据行数: {len(df)}")
    
    # 创建代码和名称的映射（取第一次出现的作为标准名称）
    index_name_map = df.groupby('跟踪指数代码')['跟踪指数名称'].first().to_dict()
    
    # 按跟踪指数代码分组，对每个指数代码的基金规模求和
    result = df.groupby('跟踪指数代码')['当前规模'].sum().reset_index()
    
    # 添加指数名称
    result['跟踪指数名称'] = result['跟踪指数代码'].map(index_name_map)
    
    # 重命名和排序列
    result = result[['跟踪指数代码', '跟踪指数名称', '当前规模']]
    result.columns = ['跟踪指数代码', '跟踪指数名称', '基金规模(亿元)']
    
    # 按基金规模排序（从大到小）
    result = result.sort_values('基金规模(亿元)', ascending=False).reset_index(drop=True)
    
    print("\n结果预览（前20名）:")
    print(result.head(20))
    
    # 保存为 CSV
    if output_path is None:
        # 自动生成输出路径
        import os
        base_dir = os.path.dirname(excel_path)
        output_path = os.path.join(base_dir, '指数基金规模汇总.csv')
    
    try:
        result.to_csv(output_path, index=False, encoding='utf-8-sig')
        print(f"\n结果已保存到: {output_path}")
    except PermissionError:
        print(f"\n警告: 无法保存到 {output_path}")
        print("文件可能被其他程序（如Excel）打开，请关闭后重试")
        print("\n结果预览:")
        print(result)
    
    print(f"共 {len(result)} 个不同的跟踪指数")
    
    return result


if __name__ == "__main__":
    # 默认路径
    excel_path = r"src\窄基调整\求基金规模\被动指数型基金.xlsx"
    
    # 执行计算
    result = calculate_index_fund_size(excel_path)
    
    # 显示统计信息
    print("\n统计信息:")
    print(f"总规模: {result['基金规模(亿元)'].sum():.2f} 亿元")
    print(f"平均规模: {result['基金规模(亿元)'].mean():.2f} 亿元")
    print(f"最大规模: {result['基金规模(亿元)'].max():.2f} 亿元 ({result.iloc[0]['跟踪指数名称']})")
    print(f"最小规模: {result['基金规模(亿元)'].min():.2f} 亿元")

