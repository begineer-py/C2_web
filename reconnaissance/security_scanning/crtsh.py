import requests
import json
from flask import current_app
import time
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

def crtsh_scan_target(domain, user_id, target_id):
    """
    使用 crt.sh 進行子域名掃描
    :param domain: 目標域名
    :param user_id: 用戶ID
    :param target_id: 目標ID
    :return: (domains, success, message)
    """
    try:
        current_app.logger.debug(f"開始 crtsh 掃描: {domain}")
        
        # 移除協議前綴和路徑
        domain = domain.replace('https://', '').replace('http://', '').split('/')[0]
        
        # 配置重試策略
        retry_strategy = Retry(
            total=5,  # 增加到5次重試
            backoff_factor=2,  # 增加退避因子
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],  # 只允許GET請求重試
            respect_retry_after_header=True  # 尊重服務器的Retry-After頭
        )
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_maxsize=10)
        
        # 創建會話並設置重試策略
        session = requests.Session()
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        
        # 準備多個備用 URL
        urls = [
            f"https://crt.sh/?q=%.{domain}&output=json",
            f"https://crt.sh/?q=%.{domain}",  # 嘗試不使用 JSON 輸出
            f"https://crt.sh/?q={domain}&output=json",  # 不使用通配符
        ]
        
        response = None
        last_error = None
        
        # 嘗試每個 URL
        for url in urls:
            current_app.logger.debug(f"嘗試請求 URL: {url}")
            max_attempts = 3
            
            for attempt in range(max_attempts):
                try:
                    # 增加初始等待時間
                    if attempt > 0:
                        wait_time = (2 ** attempt) * 5  # 5, 10, 20 秒
                        current_app.logger.warning(f"等待 {wait_time} 秒後重試...")
                        time.sleep(wait_time)
                    
                    response = session.get(
                        url,
                        timeout=60,  # 增加超時時間
                        headers={
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                        }
                    )
                    
                    if response.status_code == 200:
                        current_app.logger.info(f"成功獲取響應，URL: {url}")
                        break
                    elif response.status_code == 503:
                        current_app.logger.warning(f"服務暫時不可用 (503)，URL: {url}")
                        continue
                    else:
                        current_app.logger.error(f"請求失敗，狀態碼: {response.status_code}，URL: {url}")
                        continue
                        
                except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                    last_error = str(e)
                    current_app.logger.warning(f"請求異常: {str(e)}，正在重試...")
                    continue
                    
            if response and response.status_code == 200:
                break
        
        if not response or response.status_code != 200:
            error_msg = last_error or f"所有 URL 請求都失敗"
            current_app.logger.error(error_msg)
            return [], False, error_msg
            
        try:
            data = response.json()
        except json.JSONDecodeError as e:
            # 如果不是 JSON 格式，嘗試解析 HTML 響應
            if "name_value" in response.text:
                current_app.logger.warning("JSON 解析失敗，嘗試解析 HTML 響應")
                # 這裡可以添加 HTML 解析邏輯
                return [], False, "暫不支持 HTML 響應解析"
            else:
                current_app.logger.error(f"JSON 解析錯誤: {str(e)}")
                return [], False, f"JSON 解析錯誤: {str(e)}"
            
        if not data:
            current_app.logger.warning("API 返回空數據")
            return [], False, "未找到任何域名"
            
        # 使用集合來去重
        domains = set()
        
        # 處理每個證書記錄
        for cert in data:
            # 從 name_value 中提取域名（可能包含多個）
            if 'name_value' in cert:
                names = cert['name_value'].split('\n')
                for name in names:
                    name = name.strip().lower()
                    if name and name.endswith(domain):
                        domains.add(name)
                        
            # 從 common_name 中提取域名
            if 'common_name' in cert and cert['common_name']:
                common_name = cert['common_name'].strip().lower()
                if common_name and common_name.endswith(domain):
                    domains.add(common_name)
        
        # 將集合轉換為列表並排序
        domain_list = sorted(list(domains))
        
        # 記錄找到的域名數量
        current_app.logger.info(f"找到 {len(domain_list)} 個域名")
        current_app.logger.debug(f"域名列表: {domain_list}")
        
        if not domain_list:
            current_app.logger.warning("未找到任何域名")
            return [domain], False, "未找到任何子域名，僅返回主域名"
            
        return domain_list, True, "成功獲取域名列表"
        
    except Exception as e:
        current_app.logger.error(f"未預期的錯誤: {str(e)}")
        return [], False, f"發生錯誤: {str(e)}" 