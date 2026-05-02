#!/usr/bin/env python3
"""
CDP 版本 - 连接用户已有的浏览器实例
========================================
如果用户已经在 Chrome 里登录了小红书，用这个脚本连接现有浏览器

使用方法：
1. 用户需要先启动 Chrome 远程调试模式：
   open -a "Google Chrome" --args --remote-debugging-port=9222
   
2. 在小红书网页版完成登录

3. 运行此脚本
"""

import os
import sys
import json
import time
import random
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote

SCREENSHOT_DIR = Path.home() / "xhs-topic-engine-skill/scripts/screenshots"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

DATA_DIR = Path.home() / "xhs-topic-engine-skill/scripts/data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

def screenshot(page, name_prefix):
    timestamp = datetime.now().strftime("%m%d_%H%M%S")
    filename = f"{name_prefix}_{timestamp}.jpg"
    filepath = SCREENSHOT_DIR / filename
    page.screenshot(path=str(filepath), type="jpeg", quality=70, full_page=False)
    size_kb = filepath.stat().st_size / 1024
    print(f"📸 截图: {filename} ({size_kb:.0f} KB)")
    return str(filepath)

def human_delay(min_sec=1, max_sec=3):
    time.sleep(random.uniform(min_sec, max_sec))

def run_cdp_collection(keyword="毕业生求职", max_notes=5):
    from playwright.sync_api import sync_playwright
    
    print("🔗 尝试连接已有浏览器 (localhost:9222)...")
    print("   如果失败，请确保 Chrome 已启动远程调试:")
    print("   open -a 'Google Chrome' --args --remote-debugging-port=9222")
    
    with sync_playwright() as p:
        try:
            # 连接已有浏览器
            browser = p.chromium.connect_over_cdp("http://localhost:9222")
            print(f"✅ 已连接！浏览器版本: {browser.version}")
            
            # 获取已有页面或新建
            contexts = browser.contexts
            if contexts:
                context = contexts[0]
                pages = context.pages
                if pages:
                    page = pages[0]
                    print(f"✅ 使用已有页面: {page.url[:60]}")
                else:
                    page = context.new_page()
            else:
                context = browser.new_context()
                page = context.new_page()
            
            # 访问小红书
            print("🌐 访问小红书...")
            page.goto("https://www.xiaohongshu.com", wait_until="networkidle", timeout=30000)
            human_delay(2, 4)
            screenshot(page, "cdp_homepage")
            
            # 检查是否登录
            try:
                # 看右上角是否有消息/通知图标（已登录特征）
                msg_icon = page.query_selector('.message-icon, [class*="message"], .notify-icon')
                avatar = page.query_selector('.avatar, [class*="avatar"]')
                
                if avatar or msg_icon:
                    print("✅ 检测到登录状态！")
                else:
                    print("⚠️ 未检测到登录，可能需要在小红书网页版手动登录")
                    return
            except Exception as e:
                print(f"⚠️ 登录检测出错: {e}")
            
            # 搜索关键词
            search_url = f"https://www.xiaohongshu.com/search_result?keyword={quote(keyword)}"
            print(f"🔍 搜索: {keyword}")
            page.goto(search_url, wait_until="networkidle", timeout=30000)
            human_delay(2, 4)
            screenshot(page, "cdp_search")
            
            # 提取笔记数据
            print("📊 提取搜索结果...")
            notes = []
            
            # 尝试多种选择器
            selectors = [
                '.note-item',
                '[class*="note-item"]',
                '.search-result-item',
                '.feeds-page .note',
            ]
            
            cards = []
            for sel in selectors:
                cards = page.query_selector_all(sel)
                if cards:
                    print(f"   使用选择器: {sel} (找到 {len(cards)} 条)")
                    break
            
            for i, card in enumerate(cards[:max_notes]):
                try:
                    # 提取标题
                    title = ""
                    for tsel in ['.title', '[class*="title"]', 'h3', 'h4']:
                        el = card.query_selector(tsel)
                        if el:
                            title = el.inner_text().strip()
                            break
                    
                    # 提取作者
                    author = ""
                    for asel in ['.author', '[class*="author"]', '.name', '[class*="nickname"]']:
                        el = card.query_selector(asel)
                        if el:
                            author = el.inner_text().strip()
                            break
                    
                    # 提取点赞
                    likes = "0"
                    for lsel in ['.like-count', '[class*="like"]', '.count']:
                        el = card.query_selector(lsel)
                        if el:
                            likes = el.inner_text().strip()
                            break
                    
                    # 提取链接
                    link = ""
                    a_el = card.query_selector('a')
                    if a_el:
                        href = a_el.get_attribute('href')
                        link = href if href.startswith('http') else f"https://www.xiaohongshu.com{href}"
                    
                    if title:
                        notes.append({
                            "title": title,
                            "author": author,
                            "likes": likes,
                            "link": link,
                            "index": i + 1,
                        })
                        print(f"   [{i+1}] {title[:40]} | 👍{likes} | @{author}")
                except Exception as e:
                    print(f"   ⚠️ 第{i+1}条提取失败: {e}")
            
            # 保存数据
            if notes:
                output_file = DATA_DIR / f"cdp_search_{keyword}_{datetime.now().strftime('%m%d_%H%M')}.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(notes, f, ensure_ascii=False, indent=2)
                print(f"\n💾 数据保存: {output_file}")
            else:
                print("\n⚠️ 未提取到任何笔记数据")
                print("   可能原因: 1) 小红书改版选择器变了 2) 需要滚动加载 3) 反爬拦截")
            
            print("\n✅ 收集完成！截图保存在: screenshots/")
            
        except Exception as e:
            print(f"\n❌ CDP 连接失败: {e}")
            print("   请检查:")
            print("   1. Chrome 是否已启动远程调试 (port 9222)")
            print("   2. 是否有其他程序占用了 9222 端口")
            print("   3. Chrome 版本是否与 Playwright 兼容")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--keyword", "-k", default="毕业生求职")
    parser.add_argument("--max-notes", "-n", type=int, default=10)
    args = parser.parse_args()
    
    run_cdp_collection(args.keyword, args.max_notes)
