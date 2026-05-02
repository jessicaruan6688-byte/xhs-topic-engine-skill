#!/usr/bin/env python3
"""选题挖掘机 - 评论区信号提取版"""

import json
import sys
from datetime import datetime
from pathlib import Path

DATA_DIR = Path.home() / "xhs-topic-engine-skill/scripts/data"

def analyze_titles(notes):
    """从标题中提取选题模式"""
    analysis = {
        "total_notes": len(notes),
        "high_engagement_notes": [],
        "title_patterns": {},
        "pain_points": [],
        "content_types": {"清单": 0, "故事": 0, "教程": 0, "对比": 0, "情绪": 0, "其他": 0},
    }
    
    for note in notes:
        if not isinstance(note, dict):
            continue
        title = note.get("title", "")
        likes_str = str(note.get("likes", "0")).strip()
        
        likes = 0
        try:
            likes = int(likes_str)
        except:
            if "万" in likes_str:
                likes = int(float(likes_str.replace("万", "")) * 10000)
        
        if likes > 1000:
            analysis["high_engagement_notes"].append({
                "title": title,
                "likes": likes,
                "author": str(note.get("author", "")).split('\n')[0],
            })
        
        if any(w in title for w in ["个", "招", "步", "法", "招", "式"]):
            analysis["content_types"]["清单"] += 1
            pattern = "清单型"
        elif any(w in title for w in ["我", "朋友", "同事", "亲历", "亲身经历"]):
            analysis["content_types"]["故事"] += 1
            pattern = "故事型"
        elif any(w in title for w in ["教你", "怎么", "如何", "攻略", "指南", "技巧"]):
            analysis["content_types"]["教程"] += 1
            pattern = "教程型"
        elif any(w in title for w in ["VS", "对比", "还是", "or", "哪个", "A还是B"]):
            analysis["content_types"]["对比"] += 1
            pattern = "对比型"
        elif any(w in title for w in ["震惊", "绝了", "救命", "哭死", "焦虑", "迷茫", "慌", "崩溃", "后悔"]):
            analysis["content_types"]["情绪"] += 1
            pattern = "情绪型"
        else:
            analysis["content_types"]["其他"] += 1
            pattern = "其他"
        
        analysis["title_patterns"][pattern] = analysis["title_patterns"].get(pattern, 0) + 1
        
        pain_keywords = [
            "找不到工作", "0offer", "迷茫", "焦虑", "被拒", "裁员", "裸辞",
            "面试", "谈薪", "背调", "空窗期", "转行", "985", "二本", "大专",
            "996", "加班", "领导", "同事", "PUA", "内耗", "没经验",
        ]
        for kw in pain_keywords:
            if kw in title:
                analysis["pain_points"].append({
                    "keyword": kw,
                    "title": title,
                    "likes": likes,
                })
    
    return analysis

def generate_topic_report(keyword, notes):
    analysis = analyze_titles(notes)
    
    report = f"""# 📊 小红书选题分析报告
## 关键词：{keyword}
## 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}

---

## 一、数据概览

- **总样本数**：{analysis['total_notes']} 篇笔记
- **高互动笔记**（点赞>1000）：{len(analysis['high_engagement_notes'])} 篇
- **内容类型分布**：
"""
    
    for ctype, count in analysis['content_types'].items():
        if count > 0:
            report += f"  - {ctype}：{count} 篇\n"
    
    report += "\n## 二、标题公式拆解\n\n"
    sorted_patterns = sorted(analysis['title_patterns'].items(), key=lambda x: x[1], reverse=True)
    for pattern, count in sorted_patterns:
        pct = count / analysis['total_notes'] * 100 if analysis['total_notes'] > 0 else 0
        report += f"- **{pattern}**：{count} 篇（{pct:.0f}%）\n"
    
    report += "\n## 三、高赞笔记分析（可直接复刻）\n\n"
    sorted_notes = sorted(analysis['high_engagement_notes'], key=lambda x: x['likes'], reverse=True)
    for i, note in enumerate(sorted_notes[:8], 1):
        report += f"""### {i}. {note['title']}
- 👍 点赞：{note['likes']}
- 👤 博主：@{note['author']}
- 💡 **可复用角度**：__________

"""
    
    report += "## 四、痛点词云（选题金矿）\n\n"
    pain_count = {}
    for p in analysis['pain_points']:
        pain_count[p['keyword']] = pain_count.get(p['keyword'], 0) + 1
    
    sorted_pains = sorted(pain_count.items(), key=lambda x: x[1], reverse=True)
    for kw, count in sorted_pains[:10]:
        report += f"- **{kw}**：出现 {count} 次\n"
    
    report += """
## 五、评论区挖掘建议（需手动操作）

### 步骤：
1. 打开以上高赞笔记的链接
2. 浏览评论区，记录：
   - 高赞评论（>50赞）的内容
   - 用户反复提到的关键词
   - 两派观点打架的争议点
   - "求模板""求带""我也一样"等高频回复

### 评论区信号提取模板：
```
笔记：__________
├─ 最高赞评论：__________（__赞）
├─ 高频关键词：__________
├─ 争议点：A派____ vs B派____
├─ 用户求助：__________
└─ → 选题信号：__________
```

## 六、7天选题建议

基于以上分析，建议以下选题（按优先级排序）：

1. 【工具清单型】__________（参考高赞清单型笔记）
2. 【真实经历型】__________（参考痛点词云）
3. 【选择题互动型】__________（参考争议点）

---

*报告生成完毕。建议配合手动评论区浏览，补充情感信号。*
"""
    
    return report

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", "-f", required=True, help="搜索结果的JSON文件路径")
    parser.add_argument("--output", "-o", help="输出报告路径")
    args = parser.parse_args()
    
    with open(args.file, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)
    
    # 处理两种数据格式
    all_notes = []
    keyword = "未知"
    
    if isinstance(raw_data, dict):
        # batch_summary 格式: {keyword: [notes]}
        for k, v in raw_data.items():
            keyword = k
            if isinstance(v, list):
                all_notes.extend(v)
    elif isinstance(raw_data, list):
        all_notes = raw_data
        keyword = Path(args.file).stem.replace('search_', '').split('_')[0]
    
    print(f"📊 分析关键词: {keyword}")
    print(f"📊 总样本数: {len(all_notes)}")
    
    report = generate_topic_report(keyword, all_notes)
    
    output_path = args.output or DATA_DIR / f"topic_report_{keyword}_{datetime.now().strftime('%m%d_%H%M')}.md"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(report)
    print(f"\n💾 报告已保存: {output_path}")

if __name__ == "__main__":
    main()
