import requests
from datetime import datetime, UTC
from models import db, Target, crawler, crawler_html, crawler_js, crawler_resource, crawler_form
from urllib.parse import urlparse, urljoin
import logging
import json
import random
import os
from reconnaissance.scanner.html_parser import HtmlParser

# 配置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_user_agents():
    """加載 User-Agent 列表"""
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        ua_file = os.path.join(current_dir, 'user_agent.txt')
        with open(ua_file, 'r') as f:
            return [line.strip() for line in f if line.strip()]
    except Exception as e:
        logger.error(f"加載 User-Agent 文件時出錯：{str(e)}")
        return ['Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36']

def get_random_user_agent():
    """獲取隨機 User-Agent"""
    user_agents = load_user_agents()
    return random.choice(user_agents)

def fetch_js_content(url, base_url=None):
    """獲取 JS 文件內容"""
    try:
        if not url.startswith(('http://', 'https://')):
            if base_url:
                url = urljoin(base_url, url)
            else:
                logger.error(f"無法解析相對路徑 JS URL: {url}")
                return None

        headers = {
            'User-Agent': get_random_user_agent(),
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive'
        }

        response = requests.get(url, headers=headers, timeout=10, verify=False)
        response.raise_for_status()
        
        # 檢查內容類型
        content_type = response.headers.get('content-type', '').lower()
        if 'javascript' in content_type or url.endswith(('.js', '.jsx')):
            logger.info(f"[+] 成功獲取 JS 內容：{url}")
            return response.text
        else:
            # 如果內容類型不匹配但 URL 以 .js 結尾，仍然返回內容
            if url.endswith(('.js', '.jsx')):
                logger.warning(f"[!] URL 內容類型不匹配但仍返回內容：{url} (Content-Type: {content_type})")
                return response.text
            logger.warning(f"[!] URL 返回非 JavaScript 內容：{url} (Content-Type: {content_type})")
            return None

    except Exception as e:
        logger.error(f"獲取 JS 內容時出錯：{str(e)}")
        return None

def scan_normal_website(url, target_id):
    """掃描普通網站的入口函數"""
    try:
        # 創建爬蟲記錄
        crawl = crawler(target_id=target_id)
        db.session.add(crawl)
        db.session.commit()
        
        # 準備請求頭
        headers = {
            'User-Agent': get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        # 發送請求
        response = requests.get(url, headers=headers, timeout=10, verify=False)
        response.raise_for_status()
        
        # 使用 HTML 解析器
        parser = HtmlParser(base_url=url)
        parser.parse(response.text)
        
        # 保存 HTML 內容
        html_record = crawler_html(
            crawler_id=crawl.id,
            html_content=response.text,
            html_url=url
        )
        db.session.add(html_record)
        
        # 保存表單
        for form in parser.forms:
            form_record = crawler_form(
                crawler_id=crawl.id,
                form_data=json.dumps(form),
                form_type=form['method'],
                form_url=form['action'] or url
            )
            db.session.add(form_record)
        
        # 保存 JS 文件
        for script in parser.scripts:
            if script.get('url'):
                # 獲取 JS 內容
                js_content = fetch_js_content(script['url'], url)
                if js_content:
                    logger.info(f"[+] 成功獲取 JS 內容：{script['url']}")
                else:
                    js_content = f"// Failed to fetch JS content from: {script['url']}"
                    logger.warning(f"[!] 無法獲取 JS 內容：{script['url']}")

                js_record = crawler_js(
                    crawler_id=crawl.id,
                    js_content=js_content,
                    js_url=script['url']
                )
                db.session.add(js_record)
            elif script.get('content'):  # 內聯 JavaScript
                js_record = crawler_js(
                    crawler_id=crawl.id,
                    js_content=script['content'],
                    js_url=url + "#inline-js"
                )
                db.session.add(js_record)
                logger.info(f"[+] 保存內聯 JavaScript: {url}#inline-js")
        
        # 保存 CSS 文件
        for style in parser.styles:
            css_record = crawler_resource(
                crawler_id=crawl.id,
                resource_url=style['url'],
                resource_type='css',
                resource_data=f"/* CSS URL: {style['url']} */"
            )
            db.session.add(css_record)
        
        # 保存其他資源（圖片等）
        for image in parser.images:
            resource_record = crawler_resource(
                crawler_id=crawl.id,
                resource_url=image['url'],
                resource_type='image',
                resource_data=json.dumps(image)
            )
            db.session.add(resource_record)
            
        # 更新爬蟲完成時間和摘要信息
        crawl.completed_at = datetime.now(UTC)
        crawl.summary = json.dumps(parser.get_summary())
        db.session.commit()
        
        logger.info(f"成功掃描網站 {url}")
        return True, "掃描完成"
        
    except requests.exceptions.RequestException as e:
        error_message = f"請求錯誤：{str(e)}"
        logger.error(error_message)
        if crawl:
            crawl.error_message = error_message
            crawl.completed_at = datetime.now(UTC)
            db.session.commit()
        return False, error_message
        
    except Exception as e:
        error_message = f"掃描過程出錯：{str(e)}"
        logger.error(error_message)
        if crawl:
            crawl.error_message = error_message
            crawl.completed_at = datetime.now(UTC)
            db.session.commit()
        return False, error_message

def main(url, user_id=None):
    """主函數"""
    try:
        # 檢查 URL 格式
        if not url.startswith(('http://', 'https://')):
            url = 'http://' + url
            
        # 解析域名
        domain = urlparse(url).netloc
        if not domain:
            return False, "無效的 URL 格式"
            
        # 查找目標
        target = Target.query.filter_by(target_ip=url).first()
        if not target:
            logger.error(f"找不到目標：{url}")
            return False, "目標不存在"
            
        # 執行掃描
        return scan_normal_website(url, target.id)
        
    except Exception as e:
        error_message = f"執行過程出錯：{str(e)}"
        logger.error(error_message)
        return False, error_message
