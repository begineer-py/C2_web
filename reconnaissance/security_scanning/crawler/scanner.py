import requests
import ssl
import socket
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from flask import current_app
from .security_checker import check_security_headers
from .formatters import format_curl_result
from .crawler import crawl_website, change_to_list
import re
from models import db,crawler
import json
import logging

# 配置 logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# 如果沒有處理器，添加一個
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

def is_valid_url(url):
    """验证URL是否为有效的域名或IP地址"""
    try:
        # 使用更簡單的方式驗證 URL
        parsed = urlparse(url)
        
        # 檢查協議
        if parsed.scheme not in ('http', 'https'):
            return False
            
        # 檢查主機名
        if not parsed.netloc:
            return False
            
        # 如果是 IP 地址，進行更嚴格的驗證
        if all(c.isdigit() or c == '.' for c in parsed.netloc):
            parts = parsed.netloc.split('.')
            if len(parts) != 4:
                return False
            try:
                return all(0 <= int(part) <= 255 for part in parts)
            except ValueError:
                return False
            
        # 如果是域名
        if parsed.netloc == 'localhost':
            return True
            
        # 檢查一般域名格式
        parts = parsed.netloc.split('.')
        if len(parts) >= 2:
            # 確保每個部分至少包含一個字符，且只包含合法字符
            return all(part and all(c.isalnum() or c in '-' for c in part) for part in parts)
            
        return False
        
    except Exception as e:
        current_app.logger.error(f"URL 驗證失敗: {str(e)}")
        return False

def curl_scan_target(user_id, target_id):
    """執行 curl 掃描並返回結果"""
    try:
        # 獲取域名列表
        domains = change_to_list(user_id, target_id)
        if not domains:
            return {
                'status': 'error',
                'message': '未找到有效域名'
            }

        # 執行爬蟲
        crawl_result = crawl_website(user_id, target_id)
        if not crawl_result:
            return {
                'status': 'error',
                'message': '爬蟲失敗'
            }

        # 構建返回結果
        result = {
            'status': 'success',
            'message': '掃描完成',
            'result': crawl_result
        }
        
        # 添加日誌輸出
        logger.debug(f"返回的掃描結果: {json.dumps(result, indent=2)}")
        
        return result

    except Exception as e:
        logger.error(f"掃描過程中發生錯誤: {str(e)}")
        return {
            'status': 'error',
            'message': f'掃描過程中發生錯誤: {str(e)}'
        }

def get_ssl_info(url):
    """获取SSL/TLS证书信息"""
    try:
        hostname = urlparse(url).netloc
        context = ssl.create_default_context()
        
        with socket.create_connection((hostname, 443)) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()
                
                return {
                    'version': ssock.version(),
                    'issuer': dict(x[0] for x in cert['issuer']),
                    'subject': dict(x[0] for x in cert['subject']),
                    'notBefore': cert['notBefore'],
                    'notAfter': cert['notAfter'],
                    'signatureAlgorithm': cert.get('signatureAlgorithm', 'unknown')
                }
    except Exception as e:
        current_app.logger.error(f"獲取 SSL/TLS 證書信息失敗: {str(e)}")
        return None

def save_scan_result(user_id, target_id, scan_results):
    """保存扫描结果到数据库"""
    try:
        from models import db, curl_Result
        
        # 将扫描结果转换为字符串
        result_str = f"""
基本掃描結果:
{scan_results.get('basic_scan', '未執行基本掃描')}

爬蟲掃描結果:
發現的表單數量: {len(scan_results.get('crawl_results', {}).get('forms', []))}
發現的鏈接數量: {len(scan_results.get('crawl_results', {}).get('links', []))}
發現的資源數量: {len(scan_results.get('crawl_results', {}).get('resources', []))}

安全問題:
{chr(10).join(scan_results.get('security_issues', ['未發現安全問題']))}

錯誤信息:
{scan_results.get('error', '掃描完成，未發生錯誤')}
"""
        
        scan_result = curl_Result(
            user_id=user_id,
            target_id=target_id,
            result=result_str
        )
        
        db.session.add(scan_result)
        db.session.commit()
        
    except Exception as e:
        current_app.logger.error(f"保存掃描結果時發生錯誤: {str(e)}")
        # 这里不抛出异常，因为保存失败不应影响扫描结果的返回 