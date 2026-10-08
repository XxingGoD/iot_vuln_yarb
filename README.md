# yarb (Yet Another Rss Bot)

一个方便获取每日安全资讯的爬虫和推送程序。支持导入 opml 文件，因此也可以订阅其他任何 RSS 源。

**懒人福音，每日自动更新，点击右上角 Watch 即可：[每日安全资讯](./today.md)，[历史存档](./archive)**

- [yarb (Yet Another Rss Bot)](#yarb-yet-another-rss-bot)
  - [安装](#安装)
  - [运行](#运行)
    - [本地搭建](#本地搭建)
    - [Github Actions](#github-actions)
  - [IoT设备漏洞分析](#iot设备漏洞分析)
  - [订阅源](#订阅源)
  - [关注我们](#关注我们)

## 安装

```sh
$ git clone https://github.com/VulnTotal-Team/yarb.git
$ cd yarb && ./install.sh
```
`install.sh` 会自动创建 `cqhttp/` 目录，再下载并解压 QQ 机器人程序；首次安装不需要手动创建该目录。


## 运行

### 本地搭建

编辑配置文件 `config.json`，启用所需的订阅源和机器人（key 也可以通过环境变量传入），最好启用代理。

```sh
$ ./yarb.py --help                            
usage: yarb.py [-h] [--update] [--cron CRON] [--config CONFIG] [--test] [--no-llm]
optional arguments:
  -h, --help       show this help message and exit
  --update         Update RSS config file
  --cron CRON      Execute scheduled tasks every day (eg:"11:00")
  --config CONFIG  Use specified config file
  --test           Test bot
  --no-llm         Disable LLM analysis for IoT vulnerabilities

# 单次任务
$ ./yarb.py

# 每日定时任务
$ nohup ./yarb.py --cron 11:00 > run.log 2>&1 &
```

### Github Actions

利用 Github Actions 提供的服务，你只需要 fork 本项目，在 Settings 中添加 secrets，即可完成部署。

`build` 任务显式声明 `contents: write`，用于提交并推送每日资讯，无需为所有任务开放仓库写入权限。

启用 IoT 的 LLM 分析时，在 Settings → Secrets and variables → Actions 中添加 `OPENAI_API_KEY`，并在 `config.json` 中配置对应服务的 `llm.base_url` 和 `llm.model`。工作流会将 Secret 传入程序；不要把真实 API 密钥提交到仓库。

目前支持的推送机器人及对应的 secrets：

- [邮件机器人](https://service.mail.qq.com/cgi-bin/help?subtype=1&&id=28&&no=1001256)
  - `MAIL_KEY`（需要申请授权码，订阅较多时推荐）
  - `MAIL_RECEIVER`（可选，接收人，以","分隔）
- [飞书群机器人](https://open.feishu.cn/document/ukTMukTMukTM/ucTM5YjL3ETO24yNxkjN)：`FEISHU_KEY`
- [企业微信群机器人](https://developer.work.weixin.qq.com/document/path/91770)：`WECOM_KEY`
- [钉钉群机器人](https://open.dingtalk.com/document/robots/custom-robot-access)：`DINGTALK_KEY`（机器人安全设置可以使用"自定义关键词"，设置为"Yarb"）
- [QQ群机器人](https://github.com/Mrs4s/go-cqhttp)：`QQ_KEY`（需要关闭登录设备锁）
- [Telegram机器人](https://core.telegram.org/bots/api): `TELEGRAM_KEY`（需要代理）

## IoT设备漏洞分析

本工具新增了基于LLM的IoT设备漏洞分析功能，能够自动分析RSS文章是否与IoT/物联网设备相关的安全漏洞，并生成专门的汇总文档。

### 功能特点

1. 自动分析每篇RSS文章，判断是否为IoT/物联网/智能家居/网络设备/安全设备相关的漏洞文章
2. 生成独立的markdown文档，汇总IoT相关漏洞文章及其摘要
3. 支持关键词预过滤，减少API调用
4. 支持自定义IoT相关关键词
5. 支持自定义OpenAI API基础URL，可使用国内镜像或自建API服务
6. 支持HTTP和SOCKS代理，方便国内用户访问API

### 使用方法

1. 在`config.json`中配置OpenAI API密钥和基础URL、模型（默认Qwen2.5-32B-Instruct）:

```json
    "llm": {
        "enabled": true,
        "secrets": "OPENAI_API_KEY",
        "key": "sk-xxxx",
        "base_url": "https://api.siliconflow.cn/v1/",
        "model": "LoRA/Qwen/Qwen2.5-32B-Instruct"
    }
```

也可以通过环境变量设置:

```sh
export OPENAI_API_KEY="您的OpenAI API密钥"
export OPENAI_BASE_URL="您的自定义API基础URL"
```

2. 配置代理(可选)：

```json
"proxy": {
    "url": "http://127.0.0.1:7890",  // HTTP代理
    "llm": true                      // 是否为LLM启用代理
}
```

也支持SOCKS代理：

```json
"proxy": {
    "url": "socks5://127.0.0.1:7890", // SOCKS代理
    "llm": true
}
```

3. 自定义API基础URL适用于：
   - 国内OpenAI API镜像服务
   - 自建的OpenAI兼容API服务
   - 地区特定的OpenAI端点

4. 可以在`config.json`的`keywords.iot_keywords`部分自定义IoT相关关键词，用于预过滤

5. 如果需要禁用LLM分析功能，可以使用`--no-llm`参数:

```sh
./yarb.py --no-llm
```

6. 推送配置，新增支持bark的推送（一款接收消息的IOS应用）

```
    "bark": {
        "enabled": true,
        "device_key": "bark_key_here"
    }
```

7. 兼容性说明：
   - 本工具支持标准OpenAI API和兼容的API服务
   - 对于非标准响应格式，会自动尝试多种方式解析
   - 如果标准方法失败，会尝试直接HTTP请求方式作为备选

分析完成后，会在工作目录下生成`iot_vulnerabilities_YYYY-MM-DD.md`文件，包含所有IoT相关漏洞文章的链接和摘要。

## 订阅源

推荐订阅源：

- [CustomRSS](rss/CustomRSS.opml)

其他订阅源：

- [CyberSecurityRSS](https://github.com/zer0yu/CyberSecurityRSS)
- [Chinese-Security-RSS](https://github.com/zhengjim/Chinese-Security-RSS)
- [awesome-security-feed](https://github.com/mrtouch93/awesome-security-feed)
- [安全技术公众号](https://github.com/ttttmr/wechat2rss)
- [SecWiki 安全聚合](https://www.sec-wiki.com/opml/index)
- [Hacking8 安全信息流](https://i.hacking8.com/)

非安全订阅源：

- [中文独立博客列表](https://github.com/timqian/chinese-independent-blogs)

添加自定义订阅有两种方法：

1. 在 `config.json` 中添加本地或远程仓库：

```json
{
  "rss": {
      "CustomRSS": {
          "enabled": true,
          "filename": "CustomRSS.opml"
      },
      "CyberSecurityRSS": {
          "enabled": true,
          "url": "https://raw.githubusercontent.com/zer0yu/CyberSecurityRSS/master/CyberSecurityRSS.opml",
          "filename": "CyberSecurityRSS.opml"
      },
```

2. 在 `rss/CustomRSS.opml` 中添加链接：

```opml
<?xml version="1.0" encoding="UTF-8"?>
<opml version="2.0">
<head><title>CustomRSS</title></head>
<body>
<outline type="rss" xmlUrl="https://forum.butian.net/Rss" text="奇安信攻防社区" title="奇安信攻防社区" htmlUrl="https://forum.butian.net" />
</body>
</opml>
```

## 关注我们

[VulnTotal安全](https://github.com/VulnTotal-Team)致力于分享高质量原创文章和开源工具，包括物联网/汽车安全、移动安全、网络攻防等。

GNU General Public License v3.0

[![Stargazers over time](https://starchart.cc/VulnTotal-Team/yarb.svg)](https://starchart.cc/VulnTotal-Team/yarb)
