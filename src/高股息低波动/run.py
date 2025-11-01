"""快速启动脚本 - 提供简单的命令行界面."""

from pathlib import Path
from main import HighDividendLowVolatilitySelector


def run_with_default_settings() -> None:
    """使用默认设置运行筛选."""
    print("使用默认设置运行高股息低波动股票筛选...")
    print("- 前100只股票")
    print("- 输出到 data/ 目录")
    print()
    
    selector = HighDividendLowVolatilitySelector(top_n=100)
    result = selector.run()
    
    print("\n筛选完成！请查看 data/ 目录中的结果文件。")


def run_with_custom_settings() -> None:
    """使用自定义设置运行筛选."""
    print("=" * 80)
    print("高股息低波动股票筛选 - 自定义设置")
    print("=" * 80)
    
    # 获取用户输入
    try:
        top_n = int(input("\n请输入要选取的股票数量 [默认100]: ") or "100")
        output_dir = input("请输入输出目录路径 [默认./data]: ") or "./data"
        
        print(f"\n配置:")
        print(f"  - 选取数量: {top_n}")
        print(f"  - 输出目录: {output_dir}")
        
        confirm = input("\n确认运行？[y/n]: ")
        if confirm.lower() != "y":
            print("已取消")
            return
        
        # 运行筛选
        output_path = Path(output_dir)
        selector = HighDividendLowVolatilitySelector(
            output_dir=output_path, top_n=top_n
        )
        result = selector.run()
        
        print(f"\n筛选完成！请查看 {output_dir} 目录中的结果文件。")
        
    except KeyboardInterrupt:
        print("\n\n操作已取消")
    except Exception as e:
        print(f"\n错误: {e}")


def main() -> None:
    """主菜单."""
    print("=" * 80)
    print("高股息低波动股票筛选系统")
    print("=" * 80)
    print("\n请选择运行模式:")
    print("1. 快速运行（默认设置）")
    print("2. 自定义设置")
    print("0. 退出")
    
    choice = input("\n请输入选项 [1]: ") or "1"
    
    if choice == "1":
        run_with_default_settings()
    elif choice == "2":
        run_with_custom_settings()
    elif choice == "0":
        print("再见！")
    else:
        print("无效选项")


if __name__ == "__main__":
    main()

