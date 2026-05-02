#!/usr/bin/env python3
"""综合选题报告生成器 - 多关键词聚合分析"""

import json
import re
import argparse
from datetime import datetime
from pathlib import Path
from collections import Counter

SCRIPT_DIR = Path(__file__).parent.resolve()
DATA_DIR = SCRIPT_DIR / "data"

def find_latest_spider_results():
    files = sorted(DATA_DIR.glob("spider_results_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None

def parse_likes(val):
    if val is None:
        return 0
    s = str(val).strip()
    if not s:
        return 0
    if "万" in s:
        try:
            return int(float(s.replace("万", "")) * 10000)
        except:
            return 0
    try:
        return int(s)
    except:
        return 0

def classify_title(title):
    if any(w in title for w in ["个", "招", "步", "法", "招", "式", "款", "套", "合集", "清单", "大全", "盘点"]):
        return "清单/合集型"
    if any(w in title for w in ["我", "朋友", "同事", "亲历", "亲身经历", "从", "到", "终于", "心得", "逆袭", "上岸", "拿到"]):
        return "真实经历型"
    if any(w in title for w in ["教你", "怎么", "如何", "攻略", "指南", "技巧", "话术", "秘籍", "手把手"]):
        return "教程/攻略型"
    if any(w in title for w in ["VS", "对比", "还是", "or", "哪个", "A还是B", "区别", "差距"]):
        return "对比/选择型"
    if any(w in title for w in ["震惊", "绝了", "救命", "哭死", "焦虑", "迷茫", "慌", "崩溃", "后悔", "千万别", "避雷", "陷阱", "坑"]):
        return "情绪/警示型"
    if any(w in title for w in ["春招", "秋招", "校招", "补录", "时间线", "信息差", "名单", "更新", "流出", "刚开", "速冲", "快"]):
        return "信息差/时效型"
    return "其他"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", "-f", help="JSON数据文件路径（默认取最新的 spider_results_*.json）")
    parser.add_argument("--output", "-o", help="输出报告路径")
    args = parser.parse_args()

    data_file = Path(args.file) if args.file else find_latest_spider_results()
    if not data_file or not data_file.exists():
        print("❌ 找不到数据文件。请先运行 safe_spider.py 采集数据。")
        print(f"   期望位置: {DATA_DIR}/spider_results_*.json")
        return

    output_file = Path(args.output) if args.output else DATA_DIR / f"综合选题报告_{datetime.now().strftime('%m%d_%H%M')}.md"

    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    all_notes = []
    for keyword, notes in data.items():
        for note in notes:
            note['_keyword'] = keyword
            all_notes.append(note)

    total = len(all_notes)
    for note in all_notes:
        note['_likes'] = parse_likes(note.get('likes'))
        note['_collects'] = parse_likes(note.get('collects'))
        note['_comments'] = parse_likes(note.get('comments_count'))

    valid_notes = [n for n in all_notes if n['_likes'] > 0 or n['_collects'] > 0 or n.get('title')]
    high_engagement = sorted([n for n in valid_notes if n['_likes'] >= 100], key=lambda x: x['_likes'], reverse=True)

    # 内容类型分布
    type_dist = Counter()
    for note in valid_notes:
        type_dist[classify_title(note.get('title', ''))] += 1

    # 痛点词提取
    pain_keywords = [
        "找不到工作", "0 offer", "零offer", "迷茫", "焦虑", "被拒", "裁员", "裸辞",
        "面试", "谈薪", "背调", "空窗期", "转行", "985", "二本", "大专", "双非",
        "996", "加班", "领导", "同事", "PUA", "内耗", "没经验", "应届生", "毕业生",
        "校招", "春招", "秋招", "补录", "压薪", "工资", "薪资", "简历", "模板",
        "话术", "技巧", "信息差", "国企", "央企", "互联网", "大厂", "外企"
    ]
    pain_counter = Counter()
    pain_examples = {}
    for note in valid_notes:
        title = note.get('title', '')
        desc = note.get('desc', '')
        text = title + " " + desc
        for pk in pain_keywords:
            if pk in text:
                pain_counter[pk] += 1
                if pk not in pain_examples:
                    pain_examples[pk] = note

    # 标题关键词
    title_words = Counter()
    for note in valid_notes:
        title = note.get('title', '')
        words = re.findall(r'[一-龥]{2,6}', title)
        for w in words:
            if len(w) >= 2 and w not in ['这是', '一个', '今天', '刚刚', '已经', '可以', '我们', '他们', '没有', '因为', '所以']:
                title_words[w] += 1

    # 标签统计
    tag_counter = Counter()
    for note in valid_notes:
        for t in note.get('tags', []):
            if t:
                tag_counter[t] += 1

    report = f"""# 小红书职场选题综合报告（毕业生赛道）

> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}
> 数据来源：Spider_XHS API 逆向采集
> 采集关键词：毕业生求职、面试技巧、谈薪话术、简历模板、校招
> 总样本数：{total} 篇笔记

---

## 一、爆款笔记 TOP 榜（可直接对标）

"""

    for i, note in enumerate(high_engagement[:15], 1):
        title = note.get('title', '无标题') or '无标题'
        author = note.get('author', '未知')
        likes = note['_likes']
        collects = note['_collects']
        comments = note['_comments']
        keyword = note['_keyword']
        url = note.get('url', '')
        report += f"""### {i}. {title}
- **互动数据**：👍 {likes} | ⭐ {collects} | 💬 {comments}
- **来源关键词**：{keyword}
- **博主**：@{author}
- **链接**：{url}
- **可复用角度**：__________

"""

    report += "\n## 二、内容类型分布\n\n"
    for ctype, count in type_dist.most_common():
        pct = count / len(valid_notes) * 100 if valid_notes else 0
        report += f"- **{ctype}**：{count} 篇（{pct:.0f}%）\n"

    report += "\n## 三、高频痛点词（选题金矿）\n\n"
    for kw, count in pain_counter.most_common(20):
        ex_title = pain_examples[kw].get('title', '')[:30]
        report += f"- **{kw}**：出现 {count} 次（例：{ex_title}…）\n"

    report += "\n## 四、高频标题关键词\n\n"
    for w, c in title_words.most_common(20):
        report += f"- **{w}**：{c} 次\n"

    report += "\n## 五、热门标签\n\n"
    for t, c in tag_counter.most_common(15):
        report += f"- **{t}**：{c} 次\n"

    report += """
## 六、7天选题建议（可直接执行）

### 优先级 A：信息差型（数据验证高互动）
1. 《春招结束才发现，这20家国企还在偷偷补录》
2. 《半导体/快消26校招时间线流出，5月这些岗位刚开》
3. 《往届生也能投！五一后慢慢投的校招名单》

### 优先级 B：清单工具型（收藏率高）
4. 《不要再花钱买简历模板了！这5个网站HR自己都在用》
5. 《谈薪时千万别傻乎乎亮出底线，这3句话让我多拿了3W》
6. 《面试被问空窗期？5种满分回答模板直接抄》

### 优先级 C：真实经历型（信任感强，易出粉）
7. 《02年大专生在上海找到10K工作，我的5条心得》
8. 《从被拒20次到拿到大厂offer，我做对了这一件事》
9. 《HR说月薪2万，入职才发现1万是绩效：谈薪避坑实录》

### 优先级 D：情绪共鸣型（传播率高）
10. 《毕业生找不到工作很焦虑？你不是一个人》
11. 《同事总爱打探工资，真的很没边界感》
12. 《二本应届生出路：拒绝学历羞耻后，我拿到了3个offer》

---

## 七、评论区挖掘清单（下一步手动操作）

请打开以下笔记链接，手动记录评论区高赞内容：

"""

    for note in high_engagement[:8]:
        title = note.get('title', '')[:30]
        report += f"- [ ] [{title}...]({note.get('url','')})\n"

    report += """
评论区信号提取模板：
```
笔记：__________
├─ 最高赞评论：__________（__赞）
├─ 高频关键词：__________
├─ 争议点：A派____ vs B派____
├─ 用户求助：__________
└─ → 选题信号：__________
```

---

*报告生成完毕。建议每周跑一次数据，追踪关键词热度变化。*
"""

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"✅ 报告已生成: {output_file}")
    print(f"📊 总样本: {total}")
    print(f"🔥 高赞笔记(>100赞): {len(high_engagement)} 篇")
    print(f"📌 痛点词: {len(pain_counter)} 个")
    print(f"🏷️ 标签: {len(tag_counter)} 个")

if __name__ == "__main__":
    main()
