# 小红书职场选题引擎（XHS Topic Engine）

一个 Claude Code Skill，专为小红书**职场/毕业生求职**赛道设计，集**热点发现、竞品拆解、内容生成、数据获取**于一体。

## 解决什么问题

| 问题 | 解决方案 |
|------|----------|
| 下周发什么？ | 7天热点发现管线（评论区信号 + 搜索趋势） |
| 竞品在做什么？ | 50博主拆解管线（标题公式、逐字稿、私域打法） |
| 怎么写才像活人？ | 3种内容框架 + 活人感润色管线 |
| 数据从哪来？ | 浏览器自动化 + API逆向（Spider_XHS）双轨制 |

## 安装

### 方法1：GitHub 安装（推荐）

```bash
claude install github:jessicaruan6688-byte/xhs-topic-engine-skill
```

### 方法2：手动安装

```bash
git clone https://github.com/jessicaruan6688-byte/xhs-topic-engine-skill.git
mkdir -p ~/.claude/skills/
cp -r xhs-topic-engine-skill ~/.claude/skills/
```

安装完成后，在 Claude Code 对话中输入「小红书选题」「帮我找选题」「研究博主」等关键词即可触发。

## 前置依赖

### 必须
- Python 3.9+
- Claude Code CLI

### 数据获取依赖（按需安装）

**方案A：浏览器自动化（日常扫热点，低风险）**
```bash
pip install playwright
playwright install chromium
```

**方案B：API 逆向 Spider_XHS（深度拆爆款，中风险）**
```bash
# 1. 克隆 Spider_XHS（必须放在 ~/Spider_XHS）
git clone https://github.com/JoeanAmier/Spider_XHS.git ~/Spider_XHS
cd ~/Spider_XHS
pip install -r requirements.txt

# 2. 先登录小红书网页版
# 必须使用小红书小号，严禁主号
# 打开 https://www.xiaohongshu.com 并完成登录

# 3. 配置 Cookie
# F12 → Application → Cookies → a1
# 写入 ~/Spider_XHS/.env：COOKIE=a1=xxx;

# 4. 将本 skill 的 safe_spider.py 复制到 Spider_XHS 目录
cp ~/.claude/skills/xhs-topic-engine-skill/scripts/safe_spider.py ~/Spider_XHS/
```

> **安全警告**：Spider_XHS 必须先登录小红书网页版，并且只能使用小红书小号，严禁主号。safe_spider.py 已内置随机 3-6 秒延迟，每关键词后休息 10-15 秒。

## 快速开始

### Step 1：填写账号画像

编辑 `references/account-profile.md`，填入你的真实经历、人设定位、红线清单。Skill 会根据这个文件生成个性化内容。如果暂时不想填，也能输出通用内容。

### Step 2：跑一轮数据

**日常扫热点（浏览器自动化）：**
```bash
cd ~/.claude/skills/xhs-topic-engine-skill/scripts
python3 xhs_data_collector.py -k "毕业生求职" "面试技巧" "谈薪话术" -n 15
```

**深度拆爆款（API逆向）：**
```bash
# 先确认 Chrome 里登录的是小红书小号
cd ~/Spider_XHS
python3 safe_spider.py -k "毕业生求职" "面试技巧" -n 10 -c 20
```

数据会保存在 `scripts/data/` 目录下。

### Step 3：生成选题报告

```bash
cd ~/.claude/skills/xhs-topic-engine-skill/scripts
python3 generate_full_report.py
```

报告输出到 `scripts/data/综合选题报告_YYYYMMDD_HHMM.md`。

### Step 4：让 Claude 写内容

```
→ 用选题引擎，写一篇关于"面试被问空窗期怎么回答"的笔记
→ 帮我改一下这段话，让它像人写的
→ 研究一下 @某某博主 最近7天的内容
```

## 目录结构

```
xhs-topic-engine-skill/
├── SKILL.md                          # Skill 主逻辑（Claude 读取）
├── README.md                         # 本文件
├── .gitignore
├── references/
│   ├── account-profile.md            # 账号画像（用户必填）
│   ├── competitor-deep-dive.md       # 50博主拆解框架
│   ├── content-frameworks.md         # 3种内容框架
│   ├── data-collection-guide.md      # 数据获取技术指南
│   ├── human-voice-principles.md     # 活人感写作原则
│   └── topic-discovery.md            # 7天选题方法论
└── scripts/
    ├── xhs_data_collector.py         # 浏览器自动化采集
    ├── safe_spider.py                # API逆向采集（需复制到 ~/Spider_XHS）
    ├── topic_miner.py                # 单关键词选题分析
    └── generate_full_report.py       # 多关键词综合报告生成
```

## 工作流示例

```
每周日晚上：
  1. 跑 safe_spider.py 抓 5 个关键词的数据
  2. 运行 generate_full_report.py 生成选题报告
  3. 把 TOP5 选题丢给 Claude，按 content-frameworks.md 的框架写初稿
  4. 用 human-voice-principles.md 润色
  5. 排期发布（建议周三/周四晚8点）
```

## 安全与合规

- **必须用小号跑爬虫**。存在签名逆向，有账号风险。
- **限速运行**。safe_spider.py 已内置随机延迟，请勿修改降低。
- **仅用于个人选题研究**。禁止大规模爬取、数据贩卖。

## License

MIT
