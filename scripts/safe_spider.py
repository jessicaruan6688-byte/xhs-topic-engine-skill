#!/usr/bin/env python3
"""安全版小红书爬虫 - 专为选题研究设计"""

import sys
import time
import random
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from spider.spider import Data_Spider
from xhs_utils.common_util import init, load_env

OUTPUT_DIR = Path.home() / "xhs-topic-engine-skill/scripts/data"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def safe_delay(min_sec=3, max_sec=6):
    time.sleep(random.uniform(min_sec, max_sec))

def search_and_extract(keywords, max_notes_per_keyword=10, max_comments=20):
    init()
    spider = Data_Spider()
    cookies = load_env()
    
    if not cookies:
        print("❌ Cookie未配置！")
        return {}
    
    print(f"✅ Cookie已加载（长度: {len(cookies)}）")
    
    all_results = {}
    
    for keyword in keywords:
        print(f"\n{'='*60}")
        print(f"🔍 搜索关键词: {keyword}")
        print(f"{'='*60}")
        
        success, msg, notes = spider.xhs_apis.search_some_note(
            query=keyword,
            require_num=max_notes_per_keyword * 2,
            cookies_str=cookies,
            sort_type_choice=1,
            note_type=0,
        )
        
        if not success or not notes:
            print(f"⚠️ 搜索失败: {msg}")
            continue
        
        notes = [n for n in notes if n.get('model_type') == 'note']
        print(f"✅ 找到 {len(notes)} 篇笔记")
        
        keyword_results = []
        
        for i, note_summary in enumerate(notes[:max_notes_per_keyword], 1):
            note_id = note_summary.get('id', '') or note_summary.get('note_id', '')
            xsec_token = note_summary.get('xsec_token', '')
            
            if not note_id:
                continue
            
            note_url = f"https://www.xiaohongshu.com/explore/{note_id}?xsec_token={xsec_token}"
            print(f"\n  📄 [{i}] 笔记: {note_id}")
            
            try:
                # 获取笔记详情
                success, msg, note_info = spider.xhs_apis.get_note_info(
                    url=note_url,
                    cookies_str=cookies,
                )
                
                if not success or not note_info:
                    print(f"     ⚠️ 详情失败: {msg}")
                    continue
                
                note_data = note_info.get('data', {}).get('items', [{}])[0] if isinstance(note_info, dict) else {}
                
                if not note_data:
                    print(f"     ⚠️ 数据为空")
                    continue
                
                note_card = note_data.get('note_card', {})
                interact = note_card.get('interact_info', {})
                user = note_card.get('user', {})
                
                result = {
                    "note_id": note_id,
                    "title": note_card.get('title', ''),
                    "desc": note_card.get('desc', ''),
                    "likes": interact.get('liked_count', '0'),
                    "collects": interact.get('collected_count', '0'),
                    "comments_count": interact.get('comment_count', '0'),
                    "shares": interact.get('share_count', '0'),
                    "author": user.get('nickname', ''),
                    "author_id": user.get('user_id', ''),
                    "tags": [t.get('name', '') for t in note_card.get('tag_list', [])],
                    "time": note_card.get('time', ''),
                    "url": note_url,
                    "comments_sample": [],
                }
                
                print(f"     ✅ {result['title'][:40]}...")
                print(f"     👍 {result['likes']} | ⭐ {result['collects']} | 💬 {result['comments_count']}")
                
                # 获取评论
                if max_comments > 0 and int(str(result['comments_count'] or 0)) > 0:
                    print(f"     💬 获取评论...")
                    try:
                        success_c, msg_c, comments_data = spider.xhs_apis.get_note_all_comments(
                            note_id=note_id,
                            xsec_token=xsec_token,
                            cookies_str=cookies,
                            crawl_interval=2,
                        )
                        
                        if success_c and comments_data:
                            comments_list = []
                            for c in comments_data[:max_comments]:
                                comments_list.append({
                                    "user": c.get('user_info', {}).get('nickname', ''),
                                    "text": c.get('content', ''),
                                    "likes": c.get('like_count', '0'),
                                    "replies": len(c.get('sub_comments', [])),
                                })
                            
                            result["comments_sample"] = comments_list
                            print(f"     ✅ {len(comments_list)} 条评论")
                        else:
                            print(f"     ⚠️ 无评论")
                    except Exception as e:
                        print(f"     ⚠️ 评论异常: {e}")
                
                keyword_results.append(result)
                
                if i < len(notes[:max_notes_per_keyword]):
                    safe_delay(3, 6)
                
            except Exception as e:
                print(f"     ❌ 异常: {e}")
                continue
        
        all_results[keyword] = keyword_results
        
        if keyword != keywords[-1]:
            print(f"\n⏸️ 休息 10-15 秒...")
            safe_delay(10, 15)
    
    # 保存
    timestamp = datetime.now().strftime('%m%d_%H%M')
    output_file = OUTPUT_DIR / f"spider_results_{timestamp}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    
    # 汇总
    print("\n" + "="*60)
    print("📋 爬取完成")
    print("="*60)
    total = 0
    for kw, results in all_results.items():
        print(f"\n【{kw}】{len(results)} 篇")
        total += len(results)
        for i, r in enumerate(results[:3], 1):
            comment_count = len(r.get('comments_sample', []))
            print(f"  {i}. {r['title'][:40]} | 👍{r['likes']} | 💬{comment_count}")
    
    print(f"\n总计: {total} 篇")
    print(f"保存: {output_file}")
    print("="*60)
    
    return all_results

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--keywords", "-k", nargs="+", default=["毕业生求职"])
    parser.add_argument("--max-notes", "-n", type=int, default=10)
    parser.add_argument("--max-comments", "-c", type=int, default=20)
    args = parser.parse_args()
    
    print(f"🎯 安全爬虫启动")
    print(f"   关键词: {', '.join(args.keywords)}")
    print(f"   每关键词: {args.max_notes} 篇")
    print(f"   每笔记评论: {args.max_comments} 条")
    print()
    
    search_and_extract(args.keywords, args.max_notes, args.max_comments)
