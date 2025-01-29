import requests
import socket
import ssl
from urllib.parse import urlparse
import logging
import sys
def setup_logging():
    logger = logging.getLogger(__name__)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    handler.stream.reconfigure(encoding='utf-8')
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

def extract_domain(url):
    """從 URL 中提取域名"""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc
        if not domain:
            domain = parsed.path.split('/')[0]
        return domain.split(':')[0]  # 移除端口號
    except Exception as e:
        print(f"提取域名時出錯: {str(e)}")
        return None

def get_ssl_cert(domain):
    """獲取域名的 SSL 證書信息"""
    try:
        context = ssl.create_default_context()
        with socket.create_connection((domain, 443)) as sock:
            with context.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()
                return cert
    except Exception as e:
        print(f"獲取 SSL 證書時出錯: {str(e)}")
        return None

def check_cloudflare(url):
    """檢查網站是否使用 Cloudflare"""
    try:
        domain = extract_domain(url)
        if not domain:
            return False, "無法解析域名"

        # 檢查 HTTP 響應頭
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            
            # 檢查常見的 Cloudflare 特徵
            cf_headers = [
                'cf-ray',
                'cf-cache-status',
                'cf-request-id',
                'cf-worker',
                'server'
            ]
            
            for header in cf_headers:
                if header in response.headers:
                    if header == 'server' and 'cloudflare' in response.headers[header].lower():
                        return True, "從 Server 響應頭檢測到 Cloudflare"
                    elif header != 'server':
                        return True, f"從 {header} 響應頭檢測到 Cloudflare"

            # 檢查 SSL 證書
            cert = get_ssl_cert(domain)
            if cert:
                for org in cert.get('subject', ()):
                    if 'cloudflare' in org[0][1].lower():
                        return True, "從 SSL 證書檢測到 Cloudflare"
                for org in cert.get('issuer', ()):
                    if 'cloudflare' in org[0][1].lower():
                        return True, "從 SSL 證書頒發者檢測到 Cloudflare"

            return False, "未檢測到 Cloudflare"
        except Exception as e:
            return False, f"檢查過程出錯: {str(e)}"
    except requests.exceptions.RequestException as e:
        return None, f"請求錯誤: {str(e)}"
    except Exception as e:
        return None, f"檢查過程出錯: {str(e)}"

def main(url):
    """主函數"""
    print(f"正在檢查 {url} 是否使用 Cloudflare...")
    is_cloudflare, message = check_cloudflare(url)
    
    if is_cloudflare is None:
        print(f"檢查失敗: {message}")
        return None
    elif is_cloudflare:
        print(f"檢測到 Cloudflare: {message}")
        return True
    else:
        print(f"未使用 Cloudflare: {message}")
        return False

if __name__ == "__main__":
    # 測試用例
    test_url = "https://example.com"
    main(test_url)
