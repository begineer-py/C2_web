import requests
from bs4 import BeautifulSoup
from models import crawler, crawler_form, crawler_link, crawler_resource,crawler_image, db, crtsh_Result
import json
import logging
from datetime import datetime,UTC, timedelta
from urllib.parse import urljoin, urlparse
import time
from flask import current_app
import hashlib
import os
import random
import stem
from stem import Signal
from stem.control import Controller
import socket
import socks
import subprocess
import sys
import psutil
import winreg
import platform
import urllib3
import certifi
from .image_handler import ImageHandler
from .url_classifier import UrlClassifier

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def logger():
    # 配置日誌
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    # 創建控制台處理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)

    # 創建格式化器
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)

    # 添加處理器到日誌記錄器
    logger.addHandler(console_handler)
    
    return logger

logger = logger()

def is_valid_domain(domain):
    """驗證域名格式"""
    if not domain or len(domain) < 3:  # 域名至少要有3個字符
        return False
    if domain.startswith('.') or domain.endswith('.'):
        return False
    return all(c.isalnum() or c in '-.' for c in domain)

def change_to_list(user_id, target_id):
    """從 crtsh 結果中提取有效的域名列表"""
    try:      
        # 獲取最新的結果
        crtsh_data = crtsh_Result.query.filter_by(
            target_id=target_id
        ).order_by(crtsh_Result.scan_time.desc()).first()
        
        if not crtsh_data:
            logger.error(f"未找到 crtsh 結果: target_id={target_id}")
            return []
        
        if not crtsh_data.domains:
            logger.error(f"crtsh 結果中沒有域名數據: {crtsh_data.id}")
            return []
            
        logger.debug(f"處理 crtsh 結果: ID={crtsh_data.id}, domains={crtsh_data.domains}")
        
        try:
            # JSON 解析
            domains_data = crtsh_data.domains
            if isinstance(domains_data, str):
                try:
                    domains_data = json.loads(domains_data)
                except json.JSONDecodeError as e:
                    logger.error(f"JSON 解析失敗: {str(e)}")
                    domains_list = [d.strip() for d in domains_data.split(',')] if ',' in domains_data else [domains_data.strip()]
            else:
                domains_list = domains_data if isinstance(domains_data, list) else [str(domains_data)]
                
            # 過濾並驗證域名
            valid_domains = []
            for domain in domains_list:
                if not domain:
                    continue
                    
                domain = str(domain).strip().strip('"\'')
                
                if domain and '*' not in domain and is_valid_domain(domain):
                    valid_domains.append(domain)
                    logger.debug(f"添加有效域名: {domain}")
                else:
                    logger.debug(f"跳過無效域名: {domain}")
            
            logger.info(f"找到 {len(valid_domains)} 個有效域名")
            return valid_domains
            
        except Exception as e:
            logger.error(f"處理域名數據時發生錯誤: {str(e)}")
            return []
            
    except Exception as e:
        logger.error(f"查詢數據庫時發生錯誤: {str(e)}")
        return []

def normalize_url(base_url, url):
    """標準化URL"""
    if not url:
        return None
    try:
        if url.startswith('//'):
            url = 'https:' + url
        elif url.startswith('/'):
            url = urljoin(base_url, url)
        elif not url.startswith(('http://', 'https://')):
            url = urljoin(base_url, url)
        return url
    except Exception as e:
        logger.error(f"URL標準化失敗: {str(e)}")
        return None

def find_tor_browser_path():
    """在Windows中查找Tor Browser的安裝路徑"""
    try:
        # 常見的Tor Browser安裝路徑
        common_paths = [
            os.path.join(os.getenv('LOCALAPPDATA'), 'Tor Browser'),
            os.path.join(os.getenv('PROGRAMFILES'), 'Tor Browser'),
            os.path.join(os.getenv('PROGRAMFILES(X86)'), 'Tor Browser'),
            os.path.expanduser('~\\Desktop\\Tor Browser'),
            'C:\\Tor Browser'
        ]
        
        for path in common_paths:
            tor_exe = os.path.join(path, 'Browser\\TorBrowser\\Tor\\tor.exe')
            if os.path.exists(tor_exe):
                return tor_exe
                
        return None
    except Exception as e:
        current_app.logger.error(f"查找Tor Browser路徑時發生錯誤: {str(e)}")
        return None

def is_tor_running():
    """檢查Tor服務是否正在運行"""
    try:
        for proc in psutil.process_iter(['name']):
            if 'tor.exe' in proc.info['name'].lower():
                return True
        return False
    except Exception as e:
        current_app.logger.error(f"檢查Tor服務狀態時發生錯誤: {str(e)}")
        return False

def start_tor_service():
    """啟動Tor服務"""
    if platform.system() != 'Windows':
        current_app.logger.error("此功能僅支持Windows系統")
        return False
        
    if is_tor_running():
        current_app.logger.info("Tor服務已在運行")
        return True
        
    tor_path = find_tor_browser_path()
    if not tor_path:
        current_app.logger.error("未找到Tor Browser，請確保已安裝")
        return False
        
    try:
        # 啟動Tor服務
        subprocess.Popen([tor_path], 
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        creationflags=subprocess.CREATE_NO_WINDOW)
        
        # 等待服務啟動
        max_wait = 30
        while max_wait > 0:
            if is_tor_running():
                current_app.logger.info("Tor服務已成功啟動")
                return True
            time.sleep(1)
            max_wait -= 1
            
        current_app.logger.error("Tor服務啟動超時")
        return False
        
    except Exception as e:
        current_app.logger.error(f"啟動Tor服務時發生錯誤: {str(e)}")
        return False

def ensure_tor_running():
    """確保Tor服務正在運行"""
    try:
        # 檢查Tor是否已在運行
        if is_tor_running():
            current_app.logger.info("Tor服務已在運行")
            return True
            
        # 如果沒有運行，嘗試啟動Tor
        tor_path = find_tor_browser_path()
        if not tor_path:
            current_app.logger.error("未找到Tor Browser，請確保已安裝")
            return False
            
        # 創建Tor配置文件
        tor_config_path = os.path.join(os.path.dirname(tor_path), 'torrc')
        with open(tor_config_path, 'w', encoding='utf-8') as f:
            f.write("""
SocksPort 9050
ControlPort 9051
HashedControlPassword 16:872860B76453A77D60CA2BB8C1A7042072093276A3D701AD684053EC4C
CookieAuthentication 1
            """.strip())
            
        # 啟動Tor服務
        try:
            subprocess.Popen([tor_path, '-f', tor_config_path], 
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            creationflags=subprocess.CREATE_NO_WINDOW)
        except Exception as e:
            current_app.logger.error(f"啟動Tor服務失敗: {str(e)}")
            return False
        
        # 等待服務啟動
        max_wait = 30
        while max_wait > 0:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex(('127.0.0.1', 9050))
                sock.close()
                
                if result == 0:
                    current_app.logger.info("Tor服務已成功啟動")
                    time.sleep(5)  # 給予額外時間完全初始化
                    return True
            except Exception as e:
                current_app.logger.debug(f"等待Tor服務時發生錯誤: {str(e)}")
            finally:
                max_wait -= 1
                time.sleep(1)
                
        current_app.logger.error("Tor服務啟動超時")
        return False
        
    except Exception as e:
        current_app.logger.error(f"啟動Tor服務時發生錯誤: {str(e)}")
        return False

def get_random_user_agent():
    """獲取隨機User-Agent"""
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    ]
    return random.choice(user_agents)

def get_enhanced_headers():
    """獲取增強的請求頭，特別針對 Cloudflare 的檢測"""
    chrome_version = f"{random.randint(115, 120)}.0.{random.randint(1000, 9999)}.{random.randint(100, 999)}"
    
    # 更真實的平台信息
    platforms = {
        'Windows': {
            'os': f"Windows NT {random.choice(['10.0', '11.0'])}",
            'arch': 'Win64; x64',
            'platform': 'Windows'
        }
    }
    
    chosen_platform = random.choice(list(platforms.keys()))
    platform_info = platforms[chosen_platform]
    
    headers = {
        'User-Agent': f'Mozilla/5.0 ({platform_info["os"]}{"; " + platform_info["arch"] if platform_info["arch"] else ""}) '
                     f'AppleWebKit/537.36 (KHTML, like Gecko) '
                     f'Chrome/{chrome_version} Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'en-US,en;q=0.9,zh-TW;q=0.8,zh;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'sec-ch-ua': f'"Not A(Brand";v="99", "Google Chrome";v="{chrome_version.split(".")[0]}", "Chromium";v="{chrome_version.split(".")[0]}"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': f'"{platform_info["platform"]}"',
        'Sec-CH-UA-Full-Version': chrome_version,
        'Sec-CH-UA-Platform-Version': platform_info['os'].split()[-1],
        'Sec-CH-UA-Arch': platform_info['arch'].split(';')[0] if platform_info['arch'] else '',
        'Sec-CH-UA-Bitness': '64',
        'Sec-CH-UA-Model': '',
        'Sec-CH-UA-Full-Version-List': f'"Not A(Brand";v="99.0.0.0", "Google Chrome";v="{chrome_version}", "Chromium";v="{chrome_version}"',
        'Cache-Control': 'max-age=0',
        'DNT': '1',
        'Pragma': 'no-cache',
        'TE': 'trailers'
    }
    
    return headers

def get_session():
    """創建一個乾淨的session"""
    session = requests.Session()
    # 使用certifi提供的證書
    session.verify = certifi.where()
    # 設置基本的請求頭
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br'
    })
    return session

def get_tor_session():
    """創建一個使用Tor代理的session"""
    if not ensure_tor_running():
        raise Exception("無法啟動Tor服務")
    
    session = get_session()
    session.proxies = {
        'http': 'socks5h://127.0.0.1:9050',
        'https': 'socks5h://127.0.0.1:9050'
    }
    # 對於Tor連接，我們需要禁用證書驗證
    session.verify = False
    return session

def renew_tor_ip():
    """更新Tor的IP地址"""
    try:
        # 確保Tor正在運行
        if not ensure_tor_running():
            raise Exception("Tor服務未運行")
            
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                with Controller.from_port(port=9051) as controller:
                    controller.authenticate()
                    controller.signal(Signal.NEWNYM)
                    time.sleep(5)  # 等待新的IP生效
                    
                    # 驗證IP是否確實更改
                    old_ip = get_current_ip(get_tor_session())
                    controller.signal(Signal.NEWNYM)
                    time.sleep(5)
                    new_ip = get_current_ip(get_tor_session())
                    
                    if old_ip != new_ip:
                        current_app.logger.info(f"成功更換Tor IP地址: {new_ip}")
                        return True
                        
                    retry_count += 1
                    time.sleep(5)
            except Exception as e:
                current_app.logger.error(f"嘗試更換IP時發生錯誤: {str(e)}")
                retry_count += 1
                time.sleep(5)
                
        raise Exception("無法成功更換IP地址")
        
    except Exception as e:
        current_app.logger.error(f"更換Tor IP地址失敗: {str(e)}")
        return False

def get_current_ip(session):
    """獲取當前IP地址"""
    try:
        response = session.get('https://api.ipify.org?format=json')
        return response.json()['ip']
    except Exception as e:
        current_app.logger.error(f"獲取當前IP地址失敗: {str(e)}")
        return None

def process_image_url(img_url, base_url):
    """處理圖片URL
    
    Args:
        img_url: 原始圖片URL
        base_url: 基礎URL用於處理相對路徑
        
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
        img_url = urljoin(base_url, img_url)
        
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

def get_image_info(img_url, timeout=3):
    """獲取圖片信息
    
    Args:
        img_url: 圖片URL
        timeout: 請求超時時間（秒）
        
    Returns:
        int: 圖片大小（字節）或 None 如果獲取失敗
    """
    try:
        session = requests.Session()
        img_response = session.head(img_url, verify=False, timeout=timeout)
        img_size = img_response.headers.get('content-length', '0')
        return int(img_size)
    except requests.exceptions.Timeout:
        current_app.logger.warning(f"獲取圖片信息超時: {img_url}")
        return None
    except requests.exceptions.RequestException as e:
        current_app.logger.warning(f"獲取圖片信息失敗: {img_url}, 錯誤: {str(e)}")
        return None

def crawl_website(user_id, target_id):
    """爬取網站內容並保存到數據庫"""
    try:
        domains = change_to_list(user_id, target_id)
        if not domains:
            logger.error("沒有有效的域名可供爬取")
            return False

        success_count = 0
        for domain in domains:
            try:
                if not is_valid_domain(domain):
                    logger.warning(f"跳過無效域名: {domain}")
                    continue
                    
                url = f"https://{domain}"
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                
                logger.info(f"正在爬取: {url}")
                response = requests.get(url, headers=headers, timeout=10, verify=False)
                
                # 創建爬蟲記錄
                crawler_record = crawler(
                    target_id=target_id,
                    error_message=None,
                    created_at=datetime.now(UTC)
                )
                db.session.add(crawler_record)
                db.session.flush()  # 獲取 crawler_id
                
                # 解析HTML內容
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 提取並保存表單信息
                forms = soup.find_all('form')
                for form in forms:
                    inputs = form.find_all(['input', 'textarea', 'select'])
                    input_data = [{'name': input.get('name', ''), 'type': input.get('type', '')} for input in inputs]
                    
                    form_data = crawler_form(
                        crawler_id=crawler_record.id,
                        form_data=json.dumps(input_data),
                        form_type=form.get('method', 'GET')
                    )
                    db.session.add(form_data)
                
                # 提取並保存鏈接信息
                links = soup.find_all('a')
                for link in links:
                    href = normalize_url(url, link.get('href'))
                    if href:
                        link_data = crawler_link(
                            crawler_id=crawler_record.id,
                            link_url=href,
                            link_type='internal' if domain in href else 'external',
                            link_data=json.dumps({
                                'text': link.get_text(strip=True),
                                'title': link.get('title', '')
                            })
                        )
                        db.session.add(link_data)
                
                # 提取並保存資源信息
                resources = soup.find_all(['script', 'link'])
                for resource in resources:
                    resource_url = normalize_url(url, resource.get('src') or resource.get('href'))
                    if resource_url:
                        resource_data = crawler_resource(
                            crawler_id=crawler_record.id,
                            resource_url=resource_url,
                            resource_type=resource.name,
                            resource_data=json.dumps({
                                'alt': resource.get('alt', ''),
                                'rel': resource.get('rel', ''),
                                'type': resource.get('type', '')
                            })
                        )
                        db.session.add(resource_data)
                
                # 處理圖片
                image_handler = ImageHandler(url)
                images = soup.find_all('img')
                for img in images:
                    result = image_handler.process_image(img)
                    if result:
                        new_image = crawler_image(
                            crawler_id=crawler_record.id,
                            image_url=result['url'],
                            image_size=result['size'],
                            image_path=os.path.splitext(result['filename'])[1][1:] or 'unknown',
                            image_content=None  # 暫時不存儲圖片內容
                        )
                        db.session.add(new_image)
                
                # 更新爬蟲完成時間
                crawler_record.completed_at = datetime.now(UTC)
                db.session.commit()
                success_count += 1
                logger.info(f"成功爬取並保存: {url}")
                
            except Exception as e:
                logger.error(f"爬取 {domain} 時發生錯誤: {str(e)}")
                db.session.rollback()
                continue
        
        if success_count > 0:
            logger.info(f"成功爬取 {success_count} 個域名")
            return True
        else:
            logger.error("所有域名爬取失敗")
            return False

    except Exception as e:
        logger.error(f"爬蟲過程中發生錯誤: {str(e)}")
        return False

class Crawler:
    def __init__(self):
        self.session = requests.Session()
        self.logger = logging.getLogger(__name__)
        self.use_proxy = False
        self.max_retries = 10  # 增加最大重試次數
        self.retry_delay = 5   # 增加重試延遲時間
        self.ip_change_interval = 3  # 每3次重試更換一次IP
        
        # 初始化代理設置
        self.proxy_port = 9050
        self.control_port = 9051
        self.proxy_url = f"socks5h://127.0.0.1:{self.proxy_port}"
        
    def request_with_retry(self, url):
        """發送請求並處理重試邏輯
        
        Args:
            url: 目標URL
        """
        retries = 0
        while retries < self.max_retries:
            try:
                # 根據重試次數增加延遲
                if retries > 0:
                    delay = self.retry_delay * (1 + retries * 0.5)  # 漸進式增加延遲
                    self.logger.info(f"等待 {delay} 秒後進行第 {retries + 1} 次重試")
                    time.sleep(delay)
                
                # 每隔指定次數更換IP
                if self.use_proxy and retries > 0 and retries % self.ip_change_interval == 0:
                    self.logger.info("嘗試更換IP地址")
                    if not self.change_ip():
                        self.logger.warning("更換IP失敗，使用當前IP繼續")
                    else:
                        current_ip = self.get_current_ip()
                        self.logger.info(f"成功更換IP: {current_ip}")
                        
                # 發送請求
                response = self.session.get(url, timeout=30)
                
                if response.status_code == 200:
                    return response
                elif response.status_code == 403:
                    self.logger.warning("收到403響應，可能需要更換IP")
                    self.use_proxy = True
                    retries += 1
                    continue
                else:
                    self.logger.warning(f"請求返回狀態碼: {response.status_code}")
                    retries += 1
                    
            except Exception as e:
                self.logger.error(f"請求發生錯誤: {str(e)}")
                retries += 1
                
        raise Exception(f"達到最大重試次數({self.max_retries})，請求失敗")

def get_enhanced_session():
    """創建一個增強的session，特別處理 Cloudflare 的檢測"""
    session = requests.Session()
    
    # 基本瀏覽器特徵
    session.headers.update(get_enhanced_headers())
    
    # 添加常見的 cookie
    current_timestamp = int(time.time())
    past_timestamp = current_timestamp - random.randint(86400, 604800)  # 1-7天前
    
    default_cookies = {
        # Google Analytics cookies
        '_ga': f"GA1.2.{random.randint(1000000000, 9999999999)}.{past_timestamp}",
        '_gid': f"GA1.2.{random.randint(1000000000, 9999999999)}.{current_timestamp}",
        '_gat': '1',
        
        # Cloudflare cookies
        'cf_clearance': hashlib.sha256(str(time.time()).encode()).hexdigest()[:32],
        '__cf_bm': hashlib.sha256(str(time.time()).encode()).hexdigest(),
        '__cf_locale': random.choice(['en-US', 'en-GB', 'de-DE', 'fr-FR', 'ja-JP']),
        'cf_use_ob': '0',
        'cf_ob_info': '',
        
        # 瀏覽器特徵
        'timezone': random.choice(['America/New_York', 'Europe/London', 'Europe/Berlin', 'Asia/Tokyo', 'Australia/Sydney']),
        'screen_resolution': f"{random.choice([1920, 2560, 3440])}x{random.choice([1080, 1440, 2160])}",
        'color_depth': str(random.choice([24, 32])),
        'pixel_ratio': str(random.choice([1, 1.25, 1.5, 2])),
        'browser_language': session.headers['Accept-Language'].split(',')[0],
        'browser_platform': session.headers['sec-ch-ua-platform'].strip('"'),
        'browser_name': 'Chrome',
        'browser_version': session.headers['User-Agent'].split('Chrome/')[1].split(' ')[0],
        
        # 其他常見 cookies
        'OptanonConsent': hashlib.sha256(str(time.time()).encode()).hexdigest(),
        'OptanonAlertBoxClosed': (datetime.now() - timedelta(days=random.randint(1, 30))).strftime('%Y-%m-%d'),
        '_fbp': f"fb.1.{past_timestamp}.{random.randint(1000000000, 9999999999)}",
        '_ttp': hashlib.sha256(str(time.time()).encode()).hexdigest()[:16]
    }
    
    session.cookies.update(default_cookies)
    return session

def simulate_user_behavior(session, base_url, request_kwargs):
    """模擬真實用戶的瀏覽行為"""
    try:
        # 訪問主頁
        current_app.logger.info(f"訪問主頁: {base_url}")
        response = session.get(base_url, **request_kwargs)
        
        # 檢查是否需要處理 Cloudflare 驗證
        if "cf-browser-verification" in response.text.lower():
            current_app.logger.warning("檢測到 Cloudflare 驗證頁面")
            return False
            
        # 解析頁面中的所有鏈接
        soup = BeautifulSoup(response.text, 'html.parser')
        internal_links = []
        
        # 收集內部鏈接
        for link in soup.find_all(['a', 'link']):
            href = link.get('href')
            if href and not href.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
                normalized_url = normalize_url(base_url, href)
                if normalized_url and normalized_url.startswith(base_url):
                    internal_links.append(normalized_url)
        
        if not internal_links:
            current_app.logger.warning("未找到有效的內部鏈接")
            return False
            
        # 隨機訪問2-3個內部頁面
        for _ in range(random.randint(2, 3)):
            if not internal_links:
                break
                
            # 隨機選擇一個鏈接
            target_url = random.choice(internal_links)
            internal_links.remove(target_url)
            
            try:
                # 更新 Referer
                session.headers.update({
                    'Referer': base_url,
                    'Sec-Fetch-Site': 'same-origin',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-User': '?1',
                    'Sec-Fetch-Dest': 'document'
                })
                
                # 訪問內部頁面
                current_app.logger.info(f"訪問內部頁面: {target_url}")
                response = session.get(target_url, **request_kwargs)
                
                # 模擬閱讀時間
                time.sleep(random.uniform(4, 7))
                
                # 模擬滾動行為
                for _ in range(random.randint(2, 4)):
                    session.headers.update({
                        'Sec-Fetch-Mode': 'cors',
                        'Sec-Fetch-Site': 'same-origin',
                        'Sec-Fetch-Dest': 'empty'
                    })
                    time.sleep(random.uniform(1, 3))
                
                # 檢查是否遇到 Cloudflare 驗證
                if "cf-browser-verification" in response.text.lower():
                    current_app.logger.warning("在訪問內部頁面時檢測到 Cloudflare 驗證")
                    return False
                    
            except Exception as e:
                current_app.logger.warning(f"訪問內部頁面時發生錯誤: {str(e)}")
                continue
        
        return True
    except Exception as e:
        current_app.logger.error(f"模擬用戶行為時發生錯誤: {str(e)}")
        return False

def crawler_scan_target(target_url, user_id, target_id):
    try:
        if not target_url.startswith(('http://', 'https://')):
            target_url = f'https://{target_url}'
            
        result = {
            'target_url': target_url,
            'scan_time': time.strftime('%Y-%m-%d %H:%M:%S'),
            'urls': {
                'form_urls': [],
                'image_urls': [],
                'normal_urls': []
            }
        }
        
        current_app.logger.info(f"開始掃描目標: {target_url}")
        
        # 使用增強的 session
        session = get_enhanced_session()
        session.verify = False
        
        # 設置請求頭,不接受 br 壓縮
        parsed_url = urlparse(target_url)
        session.headers.update({
            'Host': parsed_url.netloc,
            'Accept-Encoding': 'gzip, deflate',  # 移除 br
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        
        # 初始化請求參數
        request_kwargs = {
            'verify': False,
            'allow_redirects': True,
            'timeout': 30
        }
        
        # 直接訪問目標URL
        current_app.logger.info(f"訪問目標URL: {target_url}")
        response = session.get(target_url, **request_kwargs)
        response.raise_for_status()
        
        # 打印響應狀態和頭部
        current_app.logger.info(f"響應狀態碼: {response.status_code}")
        current_app.logger.info(f"響應頭部: {dict(response.headers)}")
        
        # 處理響應內容
        try:
            html_content = response.text
            current_app.logger.info(f"成功獲取HTML內容,長度: {len(html_content)}")
            current_app.logger.debug(f"HTML內容預覽: {html_content[:500]}")
            
            # 創建爬蟲記錄
            crawler_record = crawler(
                target_id=target_id,
                error_message=None,
                created_at=datetime.now(UTC)
            )
            db.session.add(crawler_record)
            db.session.flush()  # 獲取 crawler_id
            
            # 使用URL分類器處理HTML內容
            url_classifier = UrlClassifier(target_url)
            url_classifier.process_html(html_content)
            classified_urls = url_classifier.get_classified_urls()
            
            current_app.logger.info(f"分類結果:")
            current_app.logger.info(f"- 表單數量: {len(classified_urls['form_urls'])}")
            current_app.logger.info(f"- 圖片數量: {len(classified_urls['image_urls'])}")
            current_app.logger.info(f"- 鏈接數量: {len(classified_urls['normal_urls'])}")
            
            # 保存表單URL
            for form_data in classified_urls['form_urls']:
                form = crawler_form(
                    crawler_id=crawler_record.id,
                    form_data=json.dumps(form_data['inputs']),
                    form_type=form_data['method']
                )
                db.session.add(form)
                
            # 保存圖片URL
            for img_data in classified_urls['image_urls']:
                img = crawler_image(
                    crawler_id=crawler_record.id,
                    image_url=img_data['url'],
                    image_size=0,  # 暫時設為0
                    image_path=os.path.splitext(urlparse(img_data['url']).path)[1][1:] or 'unknown',
                    image_content=None
                )
                db.session.add(img)
                
            # 保存一般URL
            for url_data in classified_urls['normal_urls']:
                url = crawler_link(
                    crawler_id=crawler_record.id,
                    link_url=url_data['url'],
                    link_type='link' if url_data['type'] == 'link' else 'resource',
                    link_data=json.dumps({
                        'text': url_data['text'],
                        'title': url_data['title']
                    })
                )
                db.session.add(url)
                
            # 更新爬蟲完成時間
            crawler_record.completed_at = datetime.now(UTC)
            
            # 提交所有更改
            db.session.commit()
            
            # 更新結果
            result['urls'] = classified_urls
            
            current_app.logger.info(f"掃描完成: {target_url}")
            return result, True, 200
            
        except Exception as e:
            current_app.logger.error(f"處理響應內容時發生錯誤: {str(e)}")
            raise
            
    except Exception as e:
        error_msg = f"爬蟲掃描過程中發生錯誤: {str(e)}"
        current_app.logger.error(error_msg)
        db.session.rollback()
        return {"error": error_msg}, False, 500
        