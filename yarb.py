#!/usr/bin/python3

import os
import json
import time
import asyncio
import schedule
import pyfiglet
import argparse
import datetime
# from datetime import datetime
import requests
import json
import listparser
import feedparser
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from bot import *
from utils import *

import requests
requests.packages.urllib3.disable_warnings()

today = datetime.datetime.now().strftime("%Y-%m-%d")


def update_today(data: list=[]):
    """更新today"""
    root_path = Path(__file__).absolute().parent
    data_path = root_path.joinpath('temp_data.json')
    today_path = root_path.joinpath('today.md')
    archive_path = root_path.joinpath(f'archive/{today.split("-")[0]}/{today}.md')

    if not data and data_path.exists():
        with open(data_path, 'r') as f1:
            data = json.load(f1)

    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with open(today_path, 'w+') as f1, open(archive_path, 'w+') as f2:
        content = f'# 每日安全资讯（{today}）\n\n'
        for item in data:
            if not isinstance(item, dict):
                continue
                
            # 确保每个item都是字典类型，并且只处理有效数据
            try:
                for feed, articles in item.items():
                    if not isinstance(articles, dict):
                        continue
                        
                    content += f'- {feed}\n'
                    for title, url in articles.items():
                        if isinstance(url, str):
                            content += f'  - [{title}]({url})\n'
                        elif isinstance(url, dict) and 'url' in url:
                            content += f'  - [{title}]({url["url"]})\n'
            except Exception as e:
                console.print(f"处理数据时出错: {str(e)}", style="bold red")
                continue
                
        f1.write(content)
        f2.write(content)


def analyze_iot_articles(data: list=[], proxy_url='', config=None):
    """分析IoT相关漏洞文章并创建专用文档"""
    if not data:
        return
    
    # 获取OpenAI API密钥
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key and config and 'llm' in config and config['llm']['enabled']:
        api_key = os.getenv(config['llm']['secrets']) or config['llm']['key']
    
    if not api_key:
        console.print("未设置OPENAI_API_KEY环境变量，跳过IoT漏洞分析", style="bold yellow")
        return
    
    # 获取OpenAI API基础URL
    base_url = os.getenv('OPENAI_BASE_URL')
    if not base_url and config and 'llm' in config and 'base_url' in config['llm']:
        base_url = config['llm']['base_url']
    
    console.print("开始分析IoT相关漏洞文章...", style="bold blue")
    
    # 获取IoT关键词列表
    iot_keywords = []
    if config and 'keywords' in config and 'iot_keywords' in config['keywords']:
        iot_keywords = config['keywords']['iot_keywords']
    
    # 初始化LLM分析器
    model = config['llm'].get('model') if config and 'llm' in config else None
    analyzer = LLMAnalyzer(api_key, proxy_url, iot_keywords, base_url, model)
    
    # IoT相关文章结果列表
    iot_articles = {}
    
    # 计算文章总数的安全方法
    total_articles = 0
    for item in data:
        if isinstance(item, dict):
            for feed, articles in item.items():
                if isinstance(articles, dict):
                    total_articles += len(articles)
    
    # 创建进度条
    with progress:
        task = progress.add_task("分析文章...", total=total_articles)
        
        for item in data:
            if not isinstance(item, dict):
                continue
                
            for feed, articles in item.items():
                if not isinstance(articles, dict):
                    continue
                    
                for title, url in articles.items():
                    # 分析文章
                    is_iot, summary = analyzer.analyze_article(title, url)
                    
                    if is_iot:
                        console.print(f"\n[+] 发现IoT相关漏洞文章: {title}", style="bold green")
                        if feed not in iot_articles:
                            iot_articles[feed] = {}
                        iot_articles[feed][title] = {"url": url, "summary": summary}
                    
                    progress.update(task, advance=1)
    
    # 如果找到IoT相关文章，创建专用文档
    if iot_articles:
        root_path = Path(__file__).absolute().parent
        iot_path = root_path.joinpath(f'iot_vulnerabilities_{today}.md')
        iot_archive_path = root_path.joinpath(f'archive/iot/{today.split("-")[0]}/{today}.md')
        
        # 确保归档目录存在
        iot_archive_path.parent.mkdir(parents=True, exist_ok=True)


        # 获取当前日期
        current_date = datetime.datetime.now()

        # 格式化日期为 "2025年5月19日"
        formatted_date = current_date.strftime("%Y年%m月%d日")
        
        zsxq_content = ""
        with open(iot_path, 'w+') as f1, open(iot_archive_path, 'w+') as f2:
            content = f'# IoT设备安全漏洞资讯（{today}）\n\n'
            for feed, articles in iot_articles.items():
                content += f'## {feed}\n\n'
                for title, info in articles.items():
                    content += f'### [{title}]({info["url"]})\n\n'
                    content += f'{info["summary"]}\n\n'
                    zsxq_content += f'{info["summary"]}\n\n'
                    content += '---\n\n'
            
            f1.write(content)
            f2.write(content)
        

        bark_key = config.get('bark', {}).get('device_key', '') if config else ''
        if not bark_key or not config.get('bark', {}).get('enabled', False):
            console.print("Bark未配置或未启用，跳过推送", style="bold yellow")
            return iot_articles
        url = f"https://api.day.app/{bark_key}"

        # 定义请求头
        headers = {
            "Content-Type": "application/json; charset=utf-8"
        }

        # 定义请求体
        data = {
            "body": f'{zsxq_content}',
            "title": f"{formatted_date}IoT设备安全漏洞资讯\n\n",
            "badge": 1,
            "sound": "birdsong",
            "icon": "https://day.app/assets/images/avatar.jpg",
            "group": "zsxq"
        }

        # 发送 POST 请求
        response = requests.post(url, headers=headers, json=data, timeout=30)

        # 打印响应状态码和内容
        # print(f"Status Code: {response.status_code}")
        console.print(f"已推送至Bark，response Body: {response.text}")
        
            
        console.print(f"IoT设备安全漏洞文档已生成: {iot_path}", style="bold green")
        # 保存原始数据
        iot_data_path = root_path.joinpath(f'iot_data_{today}.json')
        with open(iot_data_path, 'w+') as f:
            f.write(json.dumps(iot_articles, indent=4, ensure_ascii=False))
            
        return iot_articles
    else:# Exception as e:
        #print(e)
        console.print("未发现IoT相关漏洞文章", style="bold yellow")
        return None


def update_rss(rss: dict, proxy_url=''):
    """更新订阅源文件"""
    proxy = {'http': proxy_url, 'https': proxy_url} if proxy_url else {'http': None, 'https': None}

    (key, value), = rss.items()
    rss_path = root_path.joinpath(f'rss/{value["filename"]}')

    result = None
    if url := value.get('url'):
        r = requests.get(value['url'], proxies=proxy)
        if r.status_code == 200:
            with open(rss_path, 'w+') as f:
                f.write(r.text)
            print(f'[+] 更新完成：{key}')
            result = {key: rss_path}
        elif rss_path.exists():
            print(f'[-] 更新失败，使用旧文件：{key}')
            result = {key: rss_path}
        else:
            print(f'[-] 更新失败，跳过：{key}')
    else:
        print(f'[+] 本地文件：{key}')

    return result


def parseThread(conf: dict, url: str, proxy_url=''):
    """获取文章线程"""
    def filter(title: str):
        """过滤文章"""
        for i in conf['exclude']:
            if i in title:
                return False
        return True

    proxy = {'http': proxy_url, 'https': proxy_url} if proxy_url else {'http': None, 'https': None}
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.75 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'Accept-Language': 'zh-CN,zh;q=0.9',
    }

    title = ''
    result = {}
    try:
        r = requests.get(url, timeout=10, headers=headers, verify=False, proxies=proxy)
        r = feedparser.parse(r.content)

       
        # print(r)
        title = r.feed.title
        for entry in r.entries:
            d = entry.get('published_parsed') or entry.get('updated_parsed')

            # print(d)
            if(not d):
                d = (r.feed.updated_parsed)
            yesterday = datetime.date.today()# + datetime.timedelta(-1)
            pubday = datetime.date(d[0], d[1], d[2])
            # print(pubday, yesterday)
            if (pubday == yesterday or datetime.date.today()+datetime.timedelta(-1) == pubday) and filter(entry.title):
                item = {entry.title: entry.link}
                # print(item)
                result |= item
        console.print(f'[+] {title}\t{url}\t{len(result.values())}/{len(r.entries)}\tpublic day: {pubday}', style='bold green')
    except Exception as e:
        console.print(f'[-] failed: {url}', style='bold red')
        print(e)
    return title, result


async def init_bot(conf: dict, proxy_url=''):
    """初始化机器人"""
    bots = []
    # print(conf.items)
    for name, v in conf.items():
        # print(name, v)
        if v['enabled']:
            key = os.getenv(v['secrets']) or v['key']

            if name == 'mail':
                receiver = os.getenv(v['secrets_receiver']) or v['receiver']
                bot = globals()[f'{name}Bot'](v['address'], key, receiver, v['from'], v['server'])
                bots.append(bot)
            elif name == 'qq':
                server = os.getenv(v['secrets_server']) or v['server']
                groups = os.getenv(v['secrets_group_id'])
                group_id = [group.strip() for group in groups.split(',') if group.strip()] if groups else v['group_id']
                bots.append(qqBot(group_id, server, key, proxy_url))
            elif name == 'telegram':
                bot = globals()[f'{name}Bot'](key, v['chat_id'], proxy_url)
                if await bot.test_connect():
                    bots.append(bot)
            else:
                bot = globals()[f'{name}Bot'](key, proxy_url)
                bots.append(bot)
    return bots


def init_rss(conf: dict, update: bool=False, proxy_url=''):
    """初始化订阅源"""
    rss_list = []
    enabled = [{k: v} for k, v in conf.items() if v['enabled']]
    for rss in enabled:
        if update:
            if rss := update_rss(rss, proxy_url):
                rss_list.append(rss)
        else:
            (key, value), = rss.items()
            rss_list.append({key: root_path.joinpath(f'rss/{value["filename"]}')})

    # 合并相同链接
    feeds = []
    # print(rss_list)
    for rss in rss_list:
        (_, value), = rss.items()
        try:
            rss = listparser.parse(open(value).read())
            for feed in rss.feeds:
                
                # 去掉最后面的/就无法获取到订阅
                url = feed.url.strip()#.rstrip('/')
                short_url = url.split('://')[-1].split('www.')[-1]
                check = [feed for feed in feeds if short_url in feed]
                if not check:
                    feeds.append(url)
        except Exception as e:
            console.print(f'[-] 解析失败：{value}', style='bold red')
            print(e)

    console.print(f'[+] {len(feeds)} feeds', style='bold yellow')
    return feeds


async def job(args):
    """定时任务"""
    print(f'{pyfiglet.figlet_format("yarb")}\n{today}')

    global root_path
    root_path = Path(__file__).absolute().parent
    if args.config:
        config_path = Path(args.config).expanduser().absolute()
    else:
        config_path = root_path.joinpath('config.json')
    with open(config_path) as f:
        conf = json.load(f)

    proxy_rss = conf['proxy']['url'] if conf['proxy']['rss'] else ''
    feeds = init_rss(conf['rss'], args.update, proxy_rss)

    # print(feeds)
    results = []
    if args.test:
        # 测试数据
        results.extend({f'test{i}': {Pattern.create(i*500): 'test'}} for i in range(1, 20))
    else:
        # 获取文章
        numb = 0
        tasks = []
        with ThreadPoolExecutor(100) as executor:
            tasks.extend(executor.submit(parseThread, conf['keywords'], url, proxy_rss) for url in feeds)
            for task in as_completed(tasks):
                title, result = task.result()
                if result:
                    numb += len(result.values())
                    results.append({title: result})
        console.print(f'[+] {len(results)} feeds, {numb} articles', style='bold yellow')

        temp_path = root_path.joinpath('temp_data.json')
        with open(temp_path, 'w+') as f:
            f.write(json.dumps(results, indent=4, ensure_ascii=False))
            console.print(f'[+] temp data: {temp_path}', style='bold yellow')

        # 分析IoT相关漏洞文章
        proxy_llm = None
        if conf['proxy'].get('llm', False):
            proxy_llm = conf['proxy']['url']
            console.print(f"使用代理URL for LLM: {proxy_llm}", style="bold blue")
            
        if not args.no_llm:
            iot_articles = analyze_iot_articles(results, proxy_llm, conf)
        
        # 更新today
        update_today(results)

    # 推送文章
    proxy_bot = conf['proxy']['url'] if conf['proxy']['bot'] else ''
    bots = await init_bot(conf['bot'], proxy_bot)
    # print(bots)
    for bot in bots:
        # print(bot)
        await bot.send(bot.parse_results(results))



def argument():
    parser = argparse.ArgumentParser()
    parser.add_argument('--update', help='Update RSS config file', action='store_true', required=False)
    parser.add_argument('--cron', help='Execute scheduled tasks every day (eg:"11:00")', type=str, required=False)
    parser.add_argument('--config', help='Use specified config file', type=str, required=False)
    parser.add_argument('--test', help='Test bot', action='store_true', required=False)
    parser.add_argument('--no-llm', help='Disable LLM analysis for IoT vulnerabilities', action='store_true', required=False)
    return parser.parse_args()

async def main():
    args = argument()
    if args.cron:
        schedule.every().day.at(args.cron).do(job, args)
        while True:
            schedule.run_pending()
            await asyncio.sleep(1)
    else:
        await job(args)

if __name__ == '__main__':
    asyncio.run(main())
