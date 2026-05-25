import requests
from bs4 import BeautifulSoup

url = "https://mp.weixin.qq.com/s?__biz=MjM5NTc2MDYxMw==&mid=2458593264&idx=1&sn=677156abb956ed47c5886b74f930f289&subscene=0"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://mp.weixin.qq.com/",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
    "Cache-Control": "max-age=0",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "TE": "Trailers"
}

response = requests.get(url, timeout=10, headers=headers)

if response.status_code == 200:
    soup = BeautifulSoup(response.text, 'html.parser')
    # 移除脚本和样式元素
    for script in soup(["script", "style"]):
        script.extract()
    
    # 获取文本内容
    text = soup.get_text(separator='\n', strip=True)
    print(text)
else:
    print(f"HTTP错误 ({response.status_code})")