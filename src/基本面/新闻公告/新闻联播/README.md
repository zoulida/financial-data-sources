# 新闻联播文字版下载工具

这个工具用于自动下载央视《新闻联播》节目的文字版内容，方便用户获取每日新闻。

## 功能特点

- 自动获取当天或指定日期的《新闻联播》文字版
- 支持保存为TXT和JSON格式
- 自动处理网络错误和重试
- 支持命令行参数配置

## 依赖库

- requests
- beautifulsoup4

## 安装依赖

```bash
pip install requests beautifulsoup4
```

## 使用方法

### 作为命令行工具使用

下载当天的《新闻联播》：

```bash
python -m src.新闻公告.新闻联播.main
```

下载昨天的《新闻联播》：

```bash
python -m src.新闻公告.新闻联播.main --yesterday
```

下载指定日期的《新闻联播》：

```bash
python -m src.新闻公告.新闻联播.main --date 20251123
```

下载并获取所有新闻的详细内容（会花费较长时间）：

```bash
python -m src.新闻公告.新闻联播.main --details
```

指定输出目录：

```bash
python -m src.新闻公告.新闻联播.main --output "/path/to/save"
```

显示详细日志：

```bash
python -m src.新闻公告.新闻联播.main --verbose
```

### 作为Python模块使用

```python
from src.新闻公告.新闻联播.xwlb_downloader import XWLBDownloader

# 创建下载器实例
downloader = XWLBDownloader()

# 下载今天的新闻联播
news_data = downloader.download_daily_news()

# 下载指定日期的新闻联播
news_data = downloader.download_daily_news(date="20251123")

# 获取新闻列表
news_list = downloader.get_daily_news_list()

# 获取指定新闻的内容
news_url = "http://tv.cctv.com/2025/11/23/..."
news_content = downloader.get_news_content(news_url)
```

## 输出示例

下载成功后，会在指定目录中创建一个以日期命名的文件夹，其中包含：

- `news_data.json`: 包含完整新闻数据的JSON文件
- `news_content.txt`: 格式化的纯文本新闻内容
- `YYYYMMDD.md`: Markdown格式的新闻内容（参考GitHub项目格式）

如果使用 `--details` 参数，Markdown文件中还会包含所有新闻的详细内容。

## 注意事项

- 该工具仅供学习研究使用
- 请遵守相关网站的使用条款和规定
- 不要过于频繁地发送请求，以免给服务器造成负担
