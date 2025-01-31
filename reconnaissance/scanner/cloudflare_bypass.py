import requests
import json
import logging
from datetime import datetime, UTC
from models import db, crawler_html, crawler_js, crawler_resource, crawler_form, crawler
import random
import os
from reconnaissance.scanner.html_parser import HtmlParser

# 配置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CloudflareBypass:
    def __init__(self):
        self.flaresolverr_url = "http://localhost:8191/v1"
        self.session = requests.Session()
    
    def _get_random_user_agent(self):
        """從文件中隨機獲取 User-Agent"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        ua_file = os.path.join(current_dir, 'user_agent.txt')
        try:
            with open(ua_file, 'r') as f:
                user_agents = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                return random.choice(user_agents)
        except Exception as e:
            logger.error(f"讀取 User-Agent 文件出錯：{str(e)}")
            return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    def fetch_js_content(self, js_url):
        """使用 FlareSolverr 獲取 JS 文件內容"""
        try:
            payload = {
                "cmd": "request.get",
                "url": js_url,
                "maxTimeout": 60000,
                "headers": {
                    "User-Agent": self._get_random_user_agent(),
                    "Accept": "*/*",
                    "Accept-Language": "en-US,en;q=0.5",
                    "Accept-Encoding": "gzip, deflate, br"
                }
            }

            response = self.session.post(self.flaresolverr_url, json=payload)
            data = response.json()

            if data.get("status") == "ok":
                return data["solution"]["response"]
            else:
                logger.error(f"獲取 JS 內容失敗：{data.get('message', '未知錯誤')}")
                return None

        except Exception as e:
            logger.error(f"獲取 JS 內容時出錯：{str(e)}")
            return None

    def make_request(self, url, crawler_id):
        """使用 FlareSolverr 發送請求並繞過 Cloudflare"""
        try:
            if not url:
                raise ValueError("URL 不能為空")

            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url

            payload = {
                "cmd": "request.get",
                "url": url,
                "maxTimeout": 60000,
                "headers": {
                    "User-Agent": self._get_random_user_agent()
                }
            }

            # 發送請求到 FlareSolverr
            logger.info(f"[*] 正在發送請求到 FlareSolverr: {url}")
            response = self.session.post(self.flaresolverr_url, json=payload)
            data = response.json()

            if data.get("status") == "ok":
                # 獲取響應內容
                html_content = data["solution"]["response"]
                
                # 使用 HTML 解析器
                parser = HtmlParser(base_url=url)
                parser.parse(html_content)
                
                # 保存 HTML 內容
                html_record = crawler_html(
                    crawler_id=crawler_id,
                    html_content=html_content,
                    html_url=url
                )
                db.session.add(html_record)

                # 保存 JS 文件
                for script in parser.scripts:
                    if script.get('url'):
                        # 獲取 JS 內容
                        js_content = self.fetch_js_content(script['url'])
                        if js_content:
                            logger.info(f"[+] 成功獲取 JS 內容：{script['url']}")
                        else:
                            js_content = f"// Failed to fetch JS content from: {script['url']}"
                            logger.warning(f"[!] 無法獲取 JS 內容：{script['url']}")

                        js_record = crawler_js(
                            crawler_id=crawler_id,
                            js_content=js_content,
                            js_url=script['url']
                        )
                        db.session.add(js_record)
                    elif script.get('content'):  # 內聯 JavaScript
                        js_record = crawler_js(
                            crawler_id=crawler_id,
                            js_content=script['content'],
                            js_url=url + "#inline-js"
                        )
                        db.session.add(js_record)

                # 保存 CSS 文件
                for style in parser.styles:
                    if style.get('url'):
                        css_record = crawler_resource(
                            crawler_id=crawler_id,
                            resource_url=style['url'],
                            resource_type='css',
                            resource_data=f"/* CSS URL: {style['url']} */"
                        )
                        db.session.add(css_record)

                # 保存表單
                for form in parser.forms:
                    form_record = crawler_form(
                        crawler_id=crawler_id,
                        form_data=json.dumps(form),
                        form_type=form['method'],
                        form_url=form['action'] or url
                    )
                    db.session.add(form_record)
                    
                # 保存其他資源（圖片等）
                for image in parser.images:
                    resource_record = crawler_resource(
                        crawler_id=crawler_id,
                        resource_url=image['url'],
                        resource_type='image',
                        resource_data=json.dumps(image)
                    )
                    db.session.add(resource_record)

                # 保存掃描摘要
                crawl = db.session.query(crawler).get(crawler_id)
                if crawl:
                    crawl.summary = json.dumps(parser.get_summary())
                    crawl.completed_at = datetime.now(UTC)

                db.session.commit()
                logger.info(f"[√] 成功繞過 Cloudflare 並抓取 {url}")
                return True, "請求成功"
            else:
                error_msg = f"FlareSolverr 請求失敗：{data.get('message', '未知錯誤')}"
                logger.error(f"[×] {error_msg}")
                return False, error_msg

        except ValueError as e:
            error_msg = f"URL 格式錯誤：{str(e)}"
            logger.error(f"[×] {error_msg}")
            return False, error_msg
        except requests.exceptions.RequestException as e:
            error_msg = f"請求錯誤：{str(e)}"
            logger.error(f"[×] {error_msg}")
            return False, error_msg
        except Exception as e:
            error_msg = f"處理過程出錯：{str(e)}"
            logger.error(f"[×] {error_msg}")
            return False, error_msg

def bypass_cloudflare(url, crawler_id):
    """Cloudflare 繞過的入口函數"""
    try:
        bypass = CloudflareBypass()
        return bypass.make_request(url, crawler_id)
    except Exception as e:
        error_msg = f"Cloudflare 繞過失敗：{str(e)}"
        logger.error(error_msg)
        return False, error_msg 