from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import json
from flask import current_app
import logging

class UrlClassifier:
    def __init__(self, base_url):
        self.base_url = base_url
        self.form_urls = []
        self.image_urls = []
        self.normal_urls = []
        self.parsed_base = urlparse(base_url)
        self.logger = logging.getLogger(__name__)
        
    def normalize_url(self, url):
        """標準化URL"""
        if not url:
            return None
        try:
            if url.startswith('//'):
                url = 'https:' + url
            elif not url.startswith(('http://', 'https://')):
                url = urljoin(self.base_url, url)
            return url
        except Exception:
            return None
            
    def process_html(self, html_content):
        """處理 HTML 內容並分類 URL"""
        try:
            self.logger.info("開始解析 HTML 內容")
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 打印 HTML 內容的前 1000 個字符用於調試
            self.logger.debug(f"HTML 內容預覽: {html_content[:1000]}")
            
            # 處理表單
            forms = soup.find_all('form')
            self.logger.info(f"找到 {len(forms)} 個表單")
            for form in forms:
                form_url = self.normalize_url(form.get('action', ''))
                if form_url:
                    inputs = []
                    for input_tag in form.find_all(['input', 'textarea', 'select']):
                        inputs.append({
                            'name': input_tag.get('name', ''),
                            'type': input_tag.get('type', 'text')
                        })
                    self.form_urls.append({
                        'url': form_url,
                        'method': form.get('method', 'GET').upper(),
                        'inputs': inputs
                    })
                    self.logger.debug(f"處理表單: {form_url}")

            # 處理圖片
            images = soup.find_all(['img', 'source', 'picture'])
            self.logger.info(f"找到 {len(images)} 個圖片")
            for img in images:
                img_url = self.normalize_url(img.get('src') or img.get('data-src'))
                if img_url:
                    self.image_urls.append({
                        'url': img_url,
                        'alt': img.get('alt', ''),
                        'title': img.get('title', '')
                    })
                    self.logger.debug(f"處理圖片: {img_url}")

            # 處理一般鏈接
            links = soup.find_all(['a', 'link'])
            self.logger.info(f"找到 {len(links)} 個鏈接")
            for link in links:
                href = self.normalize_url(link.get('href'))
                if href:
                    self.normal_urls.append({
                        'url': href,
                        'text': link.get_text(strip=True) or '',
                        'title': link.get('title', ''),
                        'type': 'link' if link.name == 'a' else 'resource'
                    })
                    self.logger.debug(f"處理鏈接: {href}")

            # 處理腳本和其他資源
            resources = soup.find_all(['script', 'link'])
            self.logger.info(f"找到 {len(resources)} 個資源")
            for resource in resources:
                resource_url = self.normalize_url(resource.get('src') or resource.get('href'))
                if resource_url:
                    self.normal_urls.append({
                        'url': resource_url,
                        'text': '',
                        'title': '',
                        'type': resource.name
                    })
                    self.logger.debug(f"處理資源: {resource_url}")

            # 記錄找到的 URL 數量
            self.logger.info("分類結果統計:")
            self.logger.info(f"- 表單數量: {len(self.form_urls)}")
            self.logger.info(f"- 圖片數量: {len(self.image_urls)}")
            self.logger.info(f"- 鏈接數量: {len(self.normal_urls)}")

        except Exception as e:
            self.logger.error(f"處理 HTML 時發生錯誤: {str(e)}")
            self.logger.exception(e)  # 打印完整的錯誤堆棧
            
    def get_classified_urls(self):
        """獲取分類後的URL結果"""
        return {
            'form_urls': self.form_urls,
            'image_urls': self.image_urls,
            'normal_urls': self.normal_urls
        }
        
    def to_json(self):
        """將分類結果轉換為JSON格式
        
        Returns:
            str: JSON字符串
        """
        return json.dumps(self.get_classified_urls(), ensure_ascii=False, indent=2) 