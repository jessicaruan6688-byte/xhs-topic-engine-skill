#!/usr/bin/env python3
"""
小红书数据收集器 - v4（长会话版）
=================================
解决频繁登录问题：
- 一次启动浏览器，批量搜索多个关键词
- 浏览器保持开着，cookie 不会过期
- 所有数据提取完成后统一关闭

网页版限制说明：
- 搜索页 ✅ 可以拿到标题、作者、点赞、部分正文摘要
- 详情页 ❌ 小红书网页版要求App扫码，正文和评论拿不到
- 对策：从搜索页卡片提取尽可能多的信息
"""

import os, sys, json, time, random
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

SCREENSHOT_DIR = Path.home() / "xhs-topic-engine-skill/scripts/screenshots"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR = Path.home() / "xhs-topic-engine-skill/scripts/data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE = DATA_DIR / "browser_state.json"

def screenshot(page, name_prefix, full_page=False):
    timestamp = datetime.now().strftime("%m%d_%H%M%S")
    filename = f"{name_prefix}_{timestamp}.jpg"
    filepath = SCREENSHOT_DIR / filename
    page.screenshot(path=str(filepath), type="jpeg", quality=70, full_page=full_page)
    size_kb = filepath.stat().st_size / 1024
    print(f"📸 截图: {filename} ({size_kb:.0f} KB)")
    return str(filepath)

def human_delay(min_sec=2, max_sec=5):
    time.sleep(random.uniform(min_sec, max_sec))

def safe_scroll(page, pixels=None):
    if pixels is None: pixels = random.randint(300, 800)
    page.evaluate(f"window.scrollBy(0, {pixels})")
    human_delay(1, 3)

def is_logged_in(page):
    try:
        popup_texts = ["登录后查看", "手机号登录", "可用小红书或微信扫码", "登录/注册"]
        for text in popup_texts:
            el = page.query_selector(f'text={text}')
            if el and el.is_visible(): return False
        
        logged_indicators = ['.avatar', '[class*="avatar"]', '.message-icon', '[class*="message"]', 'img[src*="avatar"]']
        for sel in logged_indicators:
            el = page.query_selector(sel)
            if el and el.is_visible():
                src = el.get_attribute('src') or ''
                if 'default' not in src.lower(): return True
        
        if '/login' in page.url or '/signin' in page.url: return False
    except: pass
    return False

def auto_wait_login(page, max_wait_sec=180, check_interval=10):
    print("\n" + "="*50)
    print("⏳ 等待登录... (最长 {} 秒)".format(max_wait_sec))
    print("="*50)
    print("请在小红书弹出的登录框中完成登录")
    print("  方式1: 用小红书APP扫码")
    print("  方式2: 用手机号+验证码")
    print("="*50)
    screenshot(page, "login_waiting")
    
    waited = 0
    while waited < max_wait_sec:
        time.sleep(check_interval)
        waited += check_interval
        try:
            page.reload(wait_until="networkidle", timeout=15000)
        except: pass
        
        if is_logged_in(page):
            print(f"✅ 登录成功！用时 {waited} 秒")
            return True
        remaining = max_wait_sec - waited
        if remaining > 0:
            print(f"   等待中...剩余 {remaining} 秒")
    
    print("❌ 等待超时")
    return False

# ============================================================
# 核心：从搜索页提取尽可能多的信息
# ============================================================

def extract_search_results(page):
    """
    从搜索结果页提取笔记数据。
    小红书网页版限制：详情页需要App扫码，所以搜索页能拿多少拿多少。
    """
    results = []
    try:
        safe_scroll(page, 400)
        human_delay(1, 2)
        
        # 找所有含笔记链接的 a 标签
        all_links = page.query_selector_all('a[href*="/explore/"], a[href*="/discovery/"]')
        print(f"   找到 {len(all_links)} 个笔记链接")
        
        seen_links = set()
        
        for link_el in all_links[:30]:
            try:
                href = link_el.get_attribute('href')
                if not href or href in seen_links: continue
                seen_links.add(href)
                
                full_url = href if href.startswith('http') else f"https://www.xiaohongshu.com{href}"
                note_id = href.split('/')[-1]
                
                # 向上找父容器
                parent = link_el
                container = None
                for _ in range(5):
                    if not parent: break
                    parent = parent.query_selector('xpath=..')
                    if not parent: break
                    # 检查这个容器是否够大（包含标题、作者等信息）
                    text = parent.inner_text()
                    if len(text) > 20:
                        container = parent
                        break
                
                if not container:
                    container = link_el
                
                # 提取标题
                title = ""
                for tsel in ['h3', 'h4', '.title', '[class*="title"]', 'span']:
                    el = container.query_selector(tsel)
                    if el:
                        text = el.inner_text().strip()
                        if 5 < len(text) < 200:
                            title = text
                            break
                
                # 如果没找到标题，尝试从容器文本里找最长的那行
                if not title:
                    lines = [l.strip() for l in container.inner_text().split('\n') if len(l.strip()) > 5]
                    if lines:
                        title = max(lines, key=len)[:100]
                
                # 提取作者
                author = ""
                for asel in ['.author', '[class*="author"]', '.name', '[class*="nickname"]', '[class*="user"]']:
                    el = container.query_selector(asel)
                    if el:
                        author = el.inner_text().strip()
                        break
                
                # 提取点赞数
                likes = "0"
                for lsel in ['.like', '[class*="like"]', '.count', '[class*="count"]', '[class*="interact"]']:
                    el = container.query_selector(lsel)
                    if el:
                        txt = el.inner_text().strip()
                        if any(c.isdigit() for c in txt):
                            likes = txt
                            break
                
                # 提取正文摘要（搜索页卡片上常有的简短描述）
                summary = ""
                for ssel in ['.desc', '[class*="desc"]', '.summary', '[class*="summary"]', 'p']:
                    el = container.query_selector(ssel)
                    if el:
                        text = el.inner_text().strip()
                        if 10 < len(text) < 500 and text != title:
                            summary = text
                            break
                
                # 提取发布时间
                publish_time = ""
                for tsel in ['.time', '[class*="time"]', '.date', '[class*="date"]', '[class*="publish"]']:
                    el = container.query_selector(tsel)
                    if el:
                        publish_time = el.inner_text().strip()
                        break
                
                # 提取封面图URL
                cover_url = ""
                img_el = container.query_selector('img')
                if img_el:
                    cover_url = img_el.get_attribute('src') or img_el.get_attribute('data-src') or ""
                
                if title and len(title) > 5:
                    results.append({
                        "title": title,
                        "author": author,
                        "likes": likes,
                        "link": full_url,
                        "note_id": note_id,
                        "summary": summary,
                        "publish_time": publish_time,
                        "cover_url": cover_url,
                    })
            except:
                continue
                
    except Exception as e:
        print(f"❌ 提取失败: {e}")
    
    # 去重
    unique = []
    seen = set()
    for r in results:
        if r["link"] not in seen and r["link"]:
            seen.add(r["link"])
            unique.append(r)
    
    return unique

def search_keyword(page, keyword):
    """搜索单个关键词并提取数据"""
    print(f"\n{'='*60}")
    print(f"🔍 搜索: {keyword}")
    print(f"{'='*60}")
    
    search_url = f"https://www.xiaohongshu.com/search_result?keyword={quote(keyword)}"
    page.goto(search_url, wait_until="networkidle", timeout=30000)
    human_delay(3, 5)
    screenshot(page, f"search_{keyword[:10]}")
    
    if not is_logged_in(page):
        print("⚠️ 搜索页需要登录")
        if not auto_wait_login(page, max_wait_sec=120):
            return []
        page.goto(search_url, wait_until="networkidle", timeout=30000)
        human_delay(3, 5)
    
    safe_scroll(page, 600)
    human_delay(2, 3)
    
    results = extract_search_results(page)
    print(f"✅ 提取到 {len(results)} 条")
    
    return results

def run_batch(keywords, notes_per_keyword=10):
    """
    批量搜索多个关键词，在一个浏览器会话内完成。
    避免频繁登录。
    """
    from playwright.sync_api import sync_playwright
    
    storage_state = None
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE) as f:
                storage_state = json.load(f)
            print("💾 加载浏览器状态")
        except:
            pass
    
    all_data = {}
    
    with sync_playwright() as p:
        print("🚀 启动浏览器（保持打开直到所有搜索完成）...")
        browser = p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox']
        )
        
        if storage_state:
            context = browser.new_context(
                viewport={'width': 1280, 'height': 800},
                storage_state=storage_state,
            )
        else:
            context = browser.new_context(
                viewport={'width': 1280, 'height': 800},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            )
        
        page = context.new_page()
        
        try:
            # 首页登录检查
            print("🌐 打开小红书...")
            page.goto("https://www.xiaohongshu.com", wait_until="networkidle", timeout=30000)
            human_delay(2, 4)
            screenshot(page, "01_homepage")
            
            if not is_logged_in(page):
                print("⚠️ 需要登录")
                if not auto_wait_login(page, max_wait_sec=180):
                    browser.close()
                    return
                # 保存登录状态
                storage = context.storage_state()
                with open(STATE_FILE, 'w') as f:
                    json.dump(storage, f)
                print("💾 登录状态已保存")
            else:
                print("✅ 已登录")
            
            # 批量搜索
            for keyword in keywords:
                results = search_keyword(page, keyword)
                all_data[keyword] = results
                
                # 保存中间结果
                output_file = DATA_DIR / f"search_{keyword}_{datetime.now().strftime('%m%d_%H%M')}.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(results, f, ensure_ascii=False, indent=2)
                
                # 关键词之间休息，模拟真人
                if keyword != keywords[-1]:
                    print(f"\n⏸️ 休息 10-15 秒，准备下一个关键词...")
                    human_delay(10, 15)
            
            # 汇总保存
            summary_file = DATA_DIR / f"batch_summary_{datetime.now().strftime('%m%d_%H%M')}.json"
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(all_data, f, ensure_ascii=False, indent=2)
            
            # 输出汇总
            print("\n" + "="*60)
            print("📋 批量搜索完成")
            print("="*60)
            total = 0
            for kw, results in all_data.items():
                print(f"\n【{kw}】→ {len(results)} 条")
                total += len(results)
                for i, r in enumerate(results[:3], 1):
                    print(f"  {i}. {r['title'][:40]} | 👍{r.get('likes','0')} | @{r.get('author','')}")
            print(f"\n总计: {total} 条笔记")
            print(f"数据保存: {DATA_DIR}")
            print("="*60)
            
        except Exception as e:
            print(f"\n❌ 错误: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # 保存状态
            try:
                storage = context.storage_state()
                with open(STATE_FILE, 'w') as f:
                    json.dump(storage, f)
            except: pass
            
            print("\n🛑 数据收集完毕，浏览器即将关闭...")
            print("   如需继续搜索，重新运行脚本即可（会复用登录状态）")
            time.sleep(3)
            browser.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="小红书批量搜索工具")
    parser.add_argument("--keywords", "-k", nargs="+", default=["毕业生求职"],
                        help="搜索关键词列表，例如: -k 毕业生求职 面试技巧 谈薪话术")
    parser.add_argument("--per-keyword", "-n", type=int, default=15,
                        help="每个关键词提取多少条")
    args = parser.parse_args()
    
    print(f"🎯 批量搜索: {', '.join(args.keywords)}")
    print(f"   每个关键词最多: {args.per_keyword} 条")
    print(f"   预计总时长: {len(args.keywords) * 1} 分钟")
    print()
    
    run_batch(args.keywords, args.per_keyword)
