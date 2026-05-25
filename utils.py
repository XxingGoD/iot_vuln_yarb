from rich import print
from rich.console import Console
from rich.progress import Progress
import os
import requests
from bs4 import BeautifulSoup
import openai
import time
import re

console = Console()
progress = Progress()

class Pattern:
    @staticmethod
    def create(length: int=8192):
        pattern = ''
        parts = ['A', 'a', '0']
        while len(pattern) != length:
            pattern += parts[len(pattern) % 3]
            if len(pattern) % 3 == 0:
                parts[2] = chr(ord(parts[2]) + 1)
                if parts[2] > '9':
                    parts[2] = '0'
                    parts[1] = chr(ord(parts[1]) + 1)
                    if parts[1] > 'z':
                        parts[1] = 'a'
                        parts[0] = chr(ord(parts[0]) + 1)
                        if parts[0] > 'Z':
                            parts[0] = 'A'
        return pattern

    @staticmethod
    def offset(value: str, length: int=8192):
        return Pattern.create(length).index(value)

class LLMAnalyzer:
    def __init__(self, api_key=None, proxy_url='', iot_keywords=None, base_url=None, model=None):
        """初始化LLM分析器"""
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        
        # 处理代理URL
        self.proxy_url = proxy_url
        self.proxy = None
        if proxy_url:
            # 根据代理类型设置不同的代理格式
            if proxy_url.startswith('socks'):
                # SOCKS代理不需要设置requests代理
                self.proxy = None
                os.environ['ALL_PROXY'] = proxy_url
                console.print(f"使用SOCKS代理: {proxy_url}", style="bold blue")
            else:
                # HTTP代理
                self.proxy = {'http': proxy_url, 'https': proxy_url}
                console.print(f"使用HTTP代理: {proxy_url}", style="bold blue")
        else:
            self.proxy = {'http': None, 'https': None}
        
        self.iot_keywords = iot_keywords or []
        self.base_url = base_url or os.getenv('OPENAI_BASE_URL')
        self.model = model or 'LoRA/Qwen/Qwen2.5-32B-Instruct'
        
        if self.api_key:
            openai.api_key = self.api_key
            # 设置自定义base_url
            if self.base_url:
                console.print(f"使用自定义OpenAI API基础URL: {self.base_url}", style="bold blue")
                openai.base_url = self.base_url
    
    def extract_article_content(self, url):
        """从URL提取文章内容"""
        retry_count = 0
        max_retries = 3
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
        
        while retry_count < max_retries:
            try:
                console.print(f"\n正在尝试提取文章内容 ({retry_count+1}/{max_retries}): {url}", style="bold blue")
                response = requests.get(url, timeout=10, proxies=self.proxy, headers=headers)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    # 移除脚本和样式元素
                    for script in soup(["script", "style"]):
                        script.extract()
                    
                    # 获取文本内容
                    text = soup.get_text(separator='\n', strip=True)
                    
                    # 限制内容长度，防止token过多
                    max_length = 4000
                    if len(text) > max_length:
                        text = text[:max_length] + "..."
                    
                    # if("mp.weixin.qq.com" in url):
                    #     print(text)
                    return text
                else:
                    console.print(f"\nHTTP错误 ({response.status_code}), 重试中...", style="bold yellow")
            except Exception as e:
                console.print(f"\n提取文章内容失败 (尝试 {retry_count+1}/{max_retries}): {str(e)}", style="bold yellow")
            
            # 增加重试次数并等待
            retry_count += 1
            if retry_count < max_retries:
                time.sleep(2)  # 延迟2秒后重试
        
        # 所有重试都失败后
        console.print(f"提取文章内容最终失败: {url}", style="bold red")
        return "无法获取文章内容"
    
    def keyword_prefilter(self, title, content):
        """使用关键词预过滤，减少不必要的API调用"""
        if not self.iot_keywords:
            return True  # 如果没有关键词列表，默认通过
        
        # 合并标题和内容的前1000个字符进行检查
        text_to_check = (title + " " + content[:1000]).lower()
        
        # 检查是否包含关键词
        for keyword in self.iot_keywords:
            if re.search(r'\b' + re.escape(keyword.lower()) + r'\b', text_to_check):
                return True
        
        return False
    
    def analyze_article(self, title, url, content=None):
        """使用LLM分析文章内容，判断是否为IoT相关漏洞文章"""
        if not content:
            console.print(f"\n开始提取文章内容: {url}", style="bold blue")
            content = self.extract_article_content(url)

            # 如果无法提取内容，跳过分析
            if content == "无法获取文章内容":
                console.print(f"\n跳过分析，因为无法获取内容: {url}", style="bold yellow")
                return False, None
        
        # 使用关键词预过滤
        # if not self.keyword_prefilter(title, content):
        #     return False, None
        
        try:
            # 路由器/摄像头
            # 逆向分析过程等
            prompt = f"""
            请分析以下文章，判断是否是关于IoT(物联网)/路由器/摄像头/智能家居/网络设备/安全设备等硬件设备相关的固件分析、漏洞分析、漏洞复现文章。
            如果是，请提供一个简短的文章摘要（不超过100字），概述文章的主要内容。

            返回的内容格式为：
            【文章URL链接】：URL
            【文章标题】：标题
            【文章摘要】：摘要
            
            例如：
            【文章URL链接】：https://mp.weixin.qq.com/s/1234567890
            【文章标题】：小米路由器漏洞分析
            【文章摘要】：小米路由器存在多个漏洞，包括远程代码执行漏洞和拒绝服务漏洞，攻击者可以利用这些漏洞获取管理员权限，甚至控制路由器。


            如果不是，请回答"不相关"，无需回答其他多余内容。
            
            以下是提供给你的信息：
            文章标题: {title}
            文章URL: {url}
            文章内容:
            {content}
            """
            
            retry_count = 0
            max_retries = 3
            while retry_count < max_retries:
                try:
                    response = openai.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": "你是一个安全分析专家，专注于分析IoT设备相关的安全漏洞文章。"},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.1,
                        max_tokens=4096
                    )
                    req = response.choices[0]
                    console.print(req, style="bold blue")
                    result = req.message.content.strip()

                    
                    if "不相关" in result or 'Request error occurred' in result:
                        return False, None
                    else:
                        return True, result
                except Exception as e:
                    console.print(f"API调用失败，重试中({retry_count+1}/{max_retries}): {e}", style="bold yellow")
                    retry_count += 1
                    time.sleep(2)
            
            console.print(f"分析文章失败: {url}", style="bold red")
            return False, None
        except Exception as e:
            console.print(f"分析文章失败: {url}", style="bold red")
            console.print(e)
            return False, None
