"""
网络连接和接口诊断脚本
用于调试数据获取失败的原因
"""
import requests
import re
import time
from datetime import datetime, timedelta


def test_baidu_interface():
    """测试百度接口"""
    print("="*50)
    print("测试百度搜索接口")
    print("="*50)
    
    keyword = "央行降准"
    
    # 计算时间范围
    t_end = datetime.now()
    t_start = t_end - timedelta(hours=1)
    
    params = {
        'tn': 'news',
        'rtt': '1',
        'bsst': '1',
        'bt': t_start.strftime('%Y%m%d%H%M'),
        'et': t_end.strftime('%Y%m%d%H%M'),
        'word': keyword
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        print(f"请求URL: https://news.baidu.com/ns")
        print(f"请求参数: {params}")
        print(f"请求头: {headers}")
        
        response = requests.get(
            'https://news.baidu.com/ns',
            params=params,
            headers=headers,
            timeout=10
        )
        
        print(f"响应状态码: {response.status_code}")
        print(f"响应头: {dict(response.headers)}")
        print(f"响应内容长度: {len(response.text)}")
        
        # 检查响应内容
        if response.status_code == 200:
            html = response.text
            print(f"响应内容前500字符: {html[:500]}")
            
            # 尝试不同的正则表达式
            patterns = [
                r'找到相关新闻约.*?(\d[\d,]*)',
                r'共找到.*?(\d[\d,]*)',
                r'约.*?(\d[\d,]*)',
                r'(\d[\d,]*)条相关新闻',
                r'(\d[\d,]*)个结果'
            ]
            
            for i, pattern in enumerate(patterns, 1):
                match = re.search(pattern, html)
                if match:
                    print(f"模式{i}匹配成功: {match.group(1)}")
                    break
            else:
                print("所有正则表达式都未匹配到结果")
                
                # 查找包含数字的文本
                numbers = re.findall(r'\d+', html)
                print(f"页面中的数字: {numbers[:20]}")  # 显示前20个数字
        else:
            print(f"请求失败，状态码: {response.status_code}")
            
    except Exception as e:
        print(f"请求异常: {e}")


def test_sogou_interface():
    """测试搜狗接口"""
    print("\n" + "="*50)
    print("测试搜狗搜索接口")
    print("="*50)
    
    keyword = "央行降准"
    
    # 计算时间范围
    ts_end = int(time.time())
    ts_start = ts_end - 3600
    
    params = {
        'query': keyword,
        'type': '2',
        'tsn': '2',
        'inter_time': f'{ts_start},{ts_end}'
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        print(f"请求URL: https://news.sogou.com/news")
        print(f"请求参数: {params}")
        print(f"请求头: {headers}")
        
        response = requests.get(
            'https://news.sogou.com/news',
            params=params,
            headers=headers,
            timeout=10
        )
        
        print(f"响应状态码: {response.status_code}")
        print(f"响应头: {dict(response.headers)}")
        print(f"响应内容长度: {len(response.text)}")
        
        if response.status_code == 200:
            html = response.text
            print(f"响应内容前500字符: {html[:500]}")
            
            # 尝试不同的正则表达式
            patterns = [
                r'共约.*?(\d[\d,]*)',
                r'约.*?(\d[\d,]*)',
                r'(\d[\d,]*)条结果',
                r'(\d[\d,]*)个结果'
            ]
            
            for i, pattern in enumerate(patterns, 1):
                match = re.search(pattern, html)
                if match:
                    print(f"模式{i}匹配成功: {match.group(1)}")
                    break
            else:
                print("所有正则表达式都未匹配到结果")
                
                # 查找包含数字的文本
                numbers = re.findall(r'\d+', html)
                print(f"页面中的数字: {numbers[:20]}")
        else:
            print(f"请求失败，状态码: {response.status_code}")
            
    except Exception as e:
        print(f"请求异常: {e}")


def test_weibo_interface():
    """测试微博接口"""
    print("\n" + "="*50)
    print("测试微博统计接口")
    print("="*50)
    
    keyword = "央行降准"
    
    params = {
        'containerid': f'100103type=1&q={requests.utils.quote(keyword)}',
        'page_type': 'searchall'
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1'
    }
    
    try:
        print(f"请求URL: https://m.weibo.cn/api/container/getIndex")
        print(f"请求参数: {params}")
        print(f"请求头: {headers}")
        
        response = requests.get(
            'https://m.weibo.cn/api/container/getIndex',
            params=params,
            headers=headers,
            timeout=10
        )
        
        print(f"响应状态码: {response.status_code}")
        print(f"响应头: {dict(response.headers)}")
        print(f"响应内容长度: {len(response.text)}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"JSON解析成功")
                print(f"数据结构: {list(data.keys()) if isinstance(data, dict) else type(data)}")
                
                if 'data' in data:
                    print(f"data字段: {list(data['data'].keys()) if isinstance(data['data'], dict) else type(data['data'])}")
                    
                    if 'cards' in data['data']:
                        cards = data['data']['cards']
                        print(f"cards数量: {len(cards)}")
                        
                        if cards:
                            print(f"第一个card结构: {list(cards[0].keys()) if isinstance(cards[0], dict) else type(cards[0])}")
            except Exception as e:
                print(f"JSON解析失败: {e}")
                print(f"响应内容前500字符: {response.text[:500]}")
        else:
            print(f"请求失败，状态码: {response.status_code}")
            print(f"响应内容: {response.text[:500]}")
            
    except Exception as e:
        print(f"请求异常: {e}")


def test_network_connectivity():
    """测试网络连接"""
    print("="*50)
    print("测试网络连接")
    print("="*50)
    
    test_urls = [
        "https://www.baidu.com",
        "https://news.baidu.com",
        "https://www.sogou.com",
        "https://news.sogou.com",
        "https://m.weibo.cn"
    ]
    
    for url in test_urls:
        try:
            response = requests.get(url, timeout=5)
            print(f"✓ {url}: {response.status_code}")
        except Exception as e:
            print(f"✗ {url}: {e}")


def main():
    """主函数"""
    print("网络接口诊断工具")
    print(f"诊断时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 测试网络连接
    test_network_connectivity()
    
    # 测试各个接口
    test_baidu_interface()
    test_sogou_interface()
    test_weibo_interface()
    
    print("\n" + "="*50)
    print("诊断完成")
    print("="*50)


if __name__ == "__main__":
    main()
