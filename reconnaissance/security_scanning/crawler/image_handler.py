import os
import hashlib
from urllib.parse import urljoin, urlparse
import requests
from flask import current_app
import json

class ImageHandler:
    def __init__(self, base_url):
        self.base_url = base_url
        self.processed_images = []
        
    def process_url(self, img_url):
        """處理圖片URL
        
        Args:
            img_url: 原始圖片URL
            
        Returns:
            tuple: (處理後的URL, 文件名) 或 (None, None) 如果URL無效
        """
        try:
            if not img_url:
                return None, None
                
            # 跳過數據 URL
            if img_url.startswith('data:'):
                return None, None
                
            # 處理相對URL
            img_url = urljoin(self.base_url, img_url)
            
            # 檢查URL是否有效
            if not img_url.startswith(('http://', 'https://')):
                return None, None
                
            # 獲取圖片文件名
            img_filename = os.path.basename(urlparse(img_url).path)
            if not img_filename:
                img_filename = hashlib.md5(img_url.encode()).hexdigest()[:12] + '.jpg'
                
            return img_url, img_filename
            
        except Exception as e:
            current_app.logger.warning(f"處理圖片URL時發生錯誤: {str(e)}")
            return None, None
            
    def get_info(self, img_url, timeout=3):
        """獲取圖片信息
        
        Args:
            img_url: 圖片URL
            timeout: 請求超時時間（秒）
            
        Returns:
            dict: 圖片信息，包含大小、類型等
        """
        try:
            session = requests.Session()
            img_response = session.head(img_url, verify=False, timeout=timeout)
            
            info = {
                'size': int(img_response.headers.get('content-length', '0')),
                'type': img_response.headers.get('content-type', 'unknown'),
                'last_modified': img_response.headers.get('last-modified', None)
            }
            return info
            
        except requests.exceptions.Timeout:
            current_app.logger.warning(f"獲取圖片信息超時: {img_url}")
            return None
        except requests.exceptions.RequestException as e:
            current_app.logger.warning(f"獲取圖片信息失敗: {img_url}, 錯誤: {str(e)}")
            return None
            
    def process_image(self, img_element):
        """處理圖片元素
        
        Args:
            img_element: BeautifulSoup的img標籤元素
            
        Returns:
            dict: 處理結果
        """
        try:
            # 處理URL
            img_url, img_filename = self.process_url(img_element.get('src'))
            if not img_url:
                return None
                
            # 獲取圖片信息
            info = self.get_info(img_url)
            if not info or info['size'] > 10 * 1024 * 1024:  # 大於10MB的圖片跳過
                if info:
                    current_app.logger.warning(f"圖片過大，已跳過: {img_url}")
                return None
                
            # 構建結果
            result = {
                'url': img_url,
                'filename': img_filename,
                'size': info['size'],
                'type': info['type'],
                'alt': img_element.get('alt', ''),
                'title': img_element.get('title', ''),
                'last_modified': info['last_modified']
            }
            
            self.processed_images.append(result)
            return result
            
        except Exception as e:
            current_app.logger.warning(f"處理圖片時發生錯誤: {str(e)}")
            return None
            
    def get_processed_images(self):
        """獲取所有已處理的圖片信息
        
        Returns:
            list: 圖片信息列表
        """
        return self.processed_images
        
    def to_json(self):
        """將處理結果轉換為JSON格式
        
        Returns:
            str: JSON字符串
        """
        return json.dumps(self.processed_images, ensure_ascii=False, indent=2) 