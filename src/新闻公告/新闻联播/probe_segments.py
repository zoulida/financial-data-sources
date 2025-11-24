import re
import requests
from bs4 import BeautifulSoup

url = "https://tv.cctv.com/2025/11/23/VIDEMPuReKz4VIuVS6UqpoKK251123.shtml"
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"}

r = requests.get(url, headers=headers, timeout=15)
html = r.text
print("状态:", r.status_code, "页面长度:", len(html))

# 直接在HTML中找 VIDE*.shtml
patterns = [
    r'https?://tv\.cctv\.com/\d{4}/\d{2}/\d{2}/VIDE[\w]+\.shtml',
    r'//tv\.cctv\.com/\d{4}/\d{2}/\d{2}/VIDE[\w]+\.shtml',
    r'/\d{4}/\d{2}/\d{2}/VIDE[\w]+\.shtml',
]
found = []
for pat in patterns:
    found += re.findall(pat, html)
print("正则直接命中数量:", len(found))
for i, h in enumerate(found[:10], 1):
    if h.startswith('//'):
        h = 'https:' + h
    elif h.startswith('/'):
        h = 'https://tv.cctv.com' + h
    print(i, h)

# 再用BeautifulSoup遍历所有a标签
soup = BeautifulSoup(html, 'html.parser')
links = []
for a in soup.find_all('a', href=True):
    href = a['href'].strip()
    if href.startswith('//'):
        href = 'https:' + href
    elif href.startswith('/'):
        href = 'https://tv.cctv.com' + href
    if re.search(r'/\d{4}/\d{2}/\d{2}/VIDE[\w]+\.shtml$', href):
        links.append(href)
print("a标签过滤命中数量:", len(links))
for i, h in enumerate(links[:10], 1):
    print(i, h)
