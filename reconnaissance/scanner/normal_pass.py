import requests
from datetime import datetime, UTC
from models import db, Target, crawler, crawler_html, crawler_js, crawler_resource, crawler_form
from urllib.parse import urlparse
import logging
import json
from bs4 import BeautifulSoup
import re
import random
import os
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

def extract_forms(html_content, url):
    """提取頁面中的表單信息"""
    forms = []
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        for form in soup.find_all('form'):
            form_data = {
                'action': form.get('action', ''),
                'method': form.get('method', 'get'),
                'inputs': [{'name': input.get('name', ''), 
                          'type': input.get('type', '')} 
                         for input in form.find_all('input')]
            }
            forms.append({
                'form_data': json.dumps(form_data),
                'form_type': form.get('method', 'get'),
                'form_url': url
            })
    except Exception as e:
        logger.error(f"提取表單時出錯：{str(e)}")
    return forms

def extract_js_links(html_content):
    """提取頁面中的 JavaScript 文件"""
    js_files = []
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        for script in soup.find_all('script', src=True):
            js_files.append(script['src'])
    except Exception as e:
        logger.error(f"提取 JS 文件時出錯：{str(e)}")
    return js_files

def extract_css_links(html_content):
    """提取頁面中的 CSS 文件"""
    css_files = []
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        for link in soup.find_all('link', rel='stylesheet'):
            css_files.append(link.get('href', ''))
    except Exception as e:
        logger.error(f"提取 CSS 文件時出錯：{str(e)}")
    return css_files

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
        
        # 保存 HTML 內容
        html_record = crawler_html(
            crawler_id=crawl.id,
            html_content=response.text,
            html_url=url
        )
        db.session.add(html_record)
        
        # 提取並保存表單
        forms = extract_forms(response.text, url)
        for form_data in forms:
            form_record = crawler_form(
                crawler_id=crawl.id,
                form_data=form_data['form_data'],
                form_type=form_data['form_type'],
                form_url=form_data['form_url']
            )
            db.session.add(form_record)
        
        # 提取並保存 JS 文件
        js_files = extract_js_links(response.text)
        for js_url in js_files:
            js_record = crawler_js(
                crawler_id=crawl.id,
                js_content=f"// JS URL: {js_url}",
                js_url=js_url
            )
            db.session.add(js_record)
        
        # 提取並保存 CSS 文件
        css_files = extract_css_links(response.text)
        for css_url in css_files:
            css_record = crawler_resource(
                crawler_id=crawl.id,
                resource_url=css_url,
                resource_type='css',
                resource_data=f"/* CSS URL: {css_url} */"
            )
            db.session.add(css_record)
        
        # 更新爬蟲完成時間
        crawl.completed_at = datetime.now(UTC)
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
