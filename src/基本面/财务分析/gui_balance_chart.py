"""
Wind资产负债表图表生成器 - GUI版本
提供图形界面，方便用户选择股票和报告期
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import subprocess
import sys
import os
from datetime import datetime, date
import calendar

class BalanceChartGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Wind资产负债表图表生成器")
        self.root.geometry("500x400")
        self.root.resizable(False, False)
        
        # 设置窗口居中
        self.center_window()
        
        # 创建界面
        self.create_widgets()
        
    def center_window(self):
        """窗口居中显示"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    
    def create_widgets(self):
        """创建界面组件"""
        # 主标题
        title_frame = tk.Frame(self.root)
        title_frame.pack(pady=20)
        
        title_label = tk.Label(title_frame, text="Wind资产负债表图表生成器", 
                           font=("微软雅黑", 16, "bold"))
        title_label.pack()
        
        # 股票代码输入
        stock_frame = tk.Frame(self.root)
        stock_frame.pack(pady=15, padx=20, fill='x')
        
        tk.Label(stock_frame, text="股票代码:", font=("微软雅黑", 12)).pack(side='left', padx=(0, 10))
        
        self.stock_entry = tk.Entry(stock_frame, font=("微软雅黑", 12), width=15)
        self.stock_entry.pack(side='left')
        self.stock_entry.insert(0, "600519.SH")
        self.stock_entry.select_range(0, tk.END)
        
        tk.Label(stock_frame, text="(如: 600519.SH, 000001.SZ)", 
                font=("微软雅黑", 9), fg="gray").pack(side='left', padx=(10, 0))
        
        # 报告期选择
        date_frame = tk.Frame(self.root)
        date_frame.pack(pady=15, padx=20, fill='x')
        
        tk.Label(date_frame, text="报告期:", font=("微软雅黑", 12)).pack(side='left', padx=(0, 10))
        
        self.date_var = tk.StringVar()
        self.date_combo = ttk.Combobox(date_frame, textvariable=self.date_var, 
                                    font=("微软雅黑", 12), width=20, state="readonly")
        self.date_combo.pack(side='left')
        
        # 生成报告期选项
        self.generate_date_options()
        self.date_combo.current(0)  # 默认选择最新日期
        
        # 数据源选择
        source_frame = tk.Frame(self.root)
        source_frame.pack(pady=15, padx=20, fill='x')
        
        tk.Label(source_frame, text="数据源:", font=("微软雅黑", 12)).pack(side='left', padx=(0, 10))
        
        self.source_var = tk.StringVar(value="wind")
        wind_radio = tk.Radiobutton(source_frame, text="Wind真实数据", 
                                 variable=self.source_var, value="wind",
                                 font=("微软雅黑", 11))
        wind_radio.pack(side='left', padx=(0, 20))
        
        sample_radio = tk.Radiobutton(source_frame, text="示例数据", 
                                  variable=self.source_var, value="sample",
                                  font=("微软雅黑", 11))
        sample_radio.pack(side='left')
        
        # 按钮区域
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=30)
        
        generate_btn = tk.Button(button_frame, text="生成图表", 
                           command=self.generate_chart,
                           font=("微软雅黑", 12, "bold"),
                           bg="#4CAF50", fg="white",
                           width=12, height=2,
                           relief=tk.RAISED, bd=2)
        generate_btn.pack(side='left', padx=(0, 20))
        
        help_btn = tk.Button(button_frame, text="使用帮助", 
                         command=self.show_help,
                         font=("微软雅黑", 12),
                         bg="#2196F3", fg="white",
                         width=12, height=2,
                         relief=tk.RAISED, bd=2)
        help_btn.pack(side='left', padx=(0, 20))
        
        exit_btn = tk.Button(button_frame, text="退出程序", 
                          command=self.root.quit,
                          font=("微软雅黑", 12),
                          bg="#f44336", fg="white",
                          width=12, height=2,
                          relief=tk.RAISED, bd=2)
        exit_btn.pack(side='left')
        
        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_bar = tk.Label(self.root, textvariable=self.status_var, 
                           relief=tk.SUNKEN, anchor=tk.W,
                           font=("微软雅黑", 9))
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def generate_date_options(self):
        """生成报告期选项（当年、去年和前年的每个季月最后一天）"""
        current_year = datetime.now().year
        last_year = current_year - 1
        two_years_ago = current_year - 2
        
        dates = []
        
        # 当年的季度末
        for quarter in [3, 6, 9, 12]:
            last_day = calendar.monthrange(current_year, quarter)[1]
            date_str = f"{current_year}-{quarter:02d}-{last_day:02d}"
            display_str = f"{current_year}年Q{quarter//4+1} ({date_str})"
            dates.append((date_str, display_str))
        
        # 去年的季度末
        for quarter in [3, 6, 9, 12]:
            last_day = calendar.monthrange(last_year, quarter)[1]
            date_str = f"{last_year}-{quarter:02d}-{last_day:02d}"
            display_str = f"{last_year}年Q{quarter//4+1} ({date_str})"
            dates.append((date_str, display_str))
        
        # 前年的季度末
        for quarter in [3, 6, 9, 12]:
            last_day = calendar.monthrange(two_years_ago, quarter)[1]
            date_str = f"{two_years_ago}-{quarter:02d}-{last_day:02d}"
            display_str = f"{two_years_ago}年Q{quarter//4+1} ({date_str})"
            dates.append((date_str, display_str))
        
        # 设置下拉菜单
        date_values = [item[0] for item in dates]
        display_values = [item[1] for item in dates]
        
        self.date_combo['values'] = display_values
        self.date_options = dict(zip(display_values, date_values))
    
    def generate_chart(self):
        """生成图表"""
        try:
            # 获取输入值
            stock_code = self.stock_entry.get().strip()
            selected_display = self.date_var.get()
            report_date = self.date_options.get(selected_display)
            use_sample = self.source_var.get() == "sample"
            
            # 验证输入
            if not stock_code:
                messagebox.showerror("错误", "请输入股票代码！")
                self.stock_entry.focus()
                return
            
            if not report_date:
                messagebox.showerror("错误", "请选择报告期！")
                return
            
            # 更新状态
            self.status_var.set("正在生成图表...")
            self.root.update()
            
            # 构建命令
            script_path = os.path.join(os.path.dirname(__file__), "final_balance_chart.py")
            
            if use_sample:
                cmd = [sys.executable, script_path, "--sample"]
            else:
                cmd = [sys.executable, script_path, stock_code, report_date]
            
            # 执行程序
            self.status_var.set("正在执行财务数据获取和图表生成...")
            self.root.update()
            
            result = subprocess.run(cmd, capture_output=True, text=True, 
                               encoding='utf-8', cwd=os.path.dirname(__file__))
            
            if result.returncode == 0:
                self.status_var.set("图表生成成功！")
                messagebox.showinfo("成功", 
                                f"资产负债表图表已生成！\n\n"
                                f"股票: {stock_code}\n"
                                f"报告期: {report_date}\n"
                                f"数据源: {'示例数据' if use_sample else 'Wind真实数据'}\n\n"
                                f"图表文件已保存在程序目录中。")
            else:
                error_msg = result.stderr if result.stderr else result.stdout
                self.status_var.set("生成失败")
                messagebox.showerror("错误", 
                                f"图表生成失败！\n\n错误信息:\n{error_msg}")
        
        except Exception as e:
            self.status_var.set("发生异常")
            messagebox.showerror("异常", f"程序执行时发生异常：\n{str(e)}")
    
    def show_help(self):
        """显示帮助信息"""
        help_text = """
Wind资产负债表图表生成器 - 使用说明

【股票代码格式】
• 上海股票：600519.SH
• 深圳股票：000001.SZ
• 北京股票：430047.BJ

【报告期说明】
• 季度末：3月31日、6月30日、9月30日、12月31日
• 程序自动生成当年、去年和前年的季度末选项
• 总共12个选项：3年 × 4个季度
• Wind数据需要指定报告期才能获取

【数据源说明】
• Wind真实数据：从Wind API获取真实财务数据
  - 需要Wind终端登录和相应权限
  - 数据准确但可能获取失败
• 示例数据：使用模拟的财务数据
  - 基于真实财务结构
  - 稳定可靠，适合演示

【输出说明】
• 生成PNG格式的资产负债表柱状图
• 资产类科目显示为蓝色
• 负债类科目显示为红色
• 图表包含数值标签和图例

【故障排除】
• 如果Wind数据获取失败，请：
  1. 检查Wind终端是否登录
  2. 确认数据权限
  3. 选择示例数据模式
        """
        
        messagebox.showinfo("使用帮助", help_text)

def main():
    """主程序"""
    root = tk.Tk()
    app = BalanceChartGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
