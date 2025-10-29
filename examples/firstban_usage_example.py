"""
firstBan 模块使用示例
展示如何在 Cursor 中正确导入和使用 firstBan 模块
"""
# 现在可以直接导入 firstBan 模块，无需额外配置
# Cursor 已经通过 .vscode/settings.json 配置好了路径

# 示例1: 导入整个模块
# import firstban

# 示例2: 导入特定子模块
# from firstban import data_processor
# from firstban import utils

# 示例3: 导入特定函数或类
# from firstban.data_processor import process_data
# from firstban.utils import helper_function

# 示例4: 使用别名导入
# import firstban as fb
# from firstban import data_processor as dp

print("✅ firstBan 模块路径配置完成！")
print("现在可以在任何 Python 文件中直接导入 firstBan 模块")
print("\n使用方法:")
print("1. import firstban")
print("2. from firstban import your_module")
print("3. from firstban.your_module import your_function")

# 如果您知道具体的模块名，可以取消注释下面的代码进行测试
# try:
#     # 替换为实际的模块名
#     # from firstban import your_actual_module
#     print("✅ 模块导入成功！")
# except ImportError as e:
#     print(f"❌ 导入失败: {e}")
#     print("请检查模块名是否正确")
