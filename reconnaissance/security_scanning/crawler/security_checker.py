from bs4 import BeautifulSoup

def check_security_headers(headers, response_text=None):
    """检查安全响应头配置"""
    security_issues = []
    headers_lower = {k.lower(): v for k, v in headers.items()}
    
    # HSTS检查
    if 'strict-transport-security' not in headers_lower:
        security_issues.append("未配置 HSTS (HTTP Strict Transport Security)")
    
    # X-Frame-Options检查
    if 'x-frame-options' not in headers_lower:
        security_issues.append("未配置 X-Frame-Options，可能存在點擊劫持風險")
    
    # X-Content-Type-Options检查
    if 'x-content-type-options' not in headers_lower:
        security_issues.append("未配置 X-Content-Type-Options，可能存在 MIME 類型混淆攻擊風險")
    
    # X-XSS-Protection检查
    if 'x-xss-protection' not in headers_lower:
        security_issues.append("未配置 X-XSS-Protection，可能存在 XSS 攻擊風險")
    
    # CSP检查
    if 'content-security-policy' not in headers_lower:
        security_issues.append("未配置 Content Security Policy，可能存在各類注入攻擊風險")
    elif headers_lower['content-security-policy']:
        csp = headers_lower['content-security-policy']
        if "'unsafe-inline'" in csp or "'unsafe-eval'" in csp:
            security_issues.append("CSP 配置包含不安全的指令 (unsafe-inline 或 unsafe-eval)")
    
    # CSRF Token检查
    csrf_issues = check_csrf_protection(headers, response_text)
    if csrf_issues:
        security_issues.extend(csrf_issues)
    
    # 同源策略检查
    sop_issues = check_same_origin_policy(headers)
    if sop_issues:
        security_issues.extend(sop_issues)
    
    return security_issues

def check_csrf_protection(headers, response_text):
    """检查CSRF保护措施"""
    security_issues = []
    
    # 首先检查是否有表单
    if not response_text or '<form' not in response_text.lower():
        return []
        
    try:
        soup = BeautifulSoup(response_text, 'html.parser')
        forms = soup.find_all('form')#找到所有表單
        
        if not forms:
            return []#如果沒有表單，返回空列表
            
        # 检查CSRF相关响应头
        headers_lower = {k.lower(): v for k, v in headers.items()}
        csrf_headers = [
            'x-csrf-token',
            'x-xsrf-token',
            'csrf-token',
            'anti-csrf-token',
            '_csrf'
        ]
        
        # 檢查是否存在任何 CSRF 相關的響應頭
        has_csrf_header = any(header in headers_lower for header in csrf_headers)
        
        # 初始化一個列表來存儲缺少 CSRF 保護的表單編號
        forms_without_csrf = []
        
        # 遍歷所有表單，從 1 開始編號
        for i, form in enumerate(forms, 1):
            # 獲取表單的 method 屬性，如果沒有則返回空字符串，並轉換為小寫
            method = form.get('method', '').lower()
            # 如果是 GET 方法的表單，跳過檢查
            if method == 'get':
                continue
                
            # 检查CSRF相关隐藏字段
            csrf_inputs = form.find_all('input', attrs={
                'type': 'hidden',
                'name': lambda x: x and any(token in x.lower() for token in [
                    'csrf', 'xsrf', '_token', 'authenticity_token'
                ])
            })
            
            # 检查meta标签中的CSRF token
            csrf_meta = soup.find('meta', attrs={
                'name': lambda x: x and any(token in str(x).lower() for token in [
                    'csrf-token', 'xsrf-token'
                ])
            })
            
            if not csrf_inputs and not csrf_meta and not has_csrf_header:
                forms_without_csrf.append(i)
        
        # 报告结果
        if forms_without_csrf:
            if len(forms_without_csrf) == len(forms):
                security_issues.append("所有表單都缺少 CSRF 保護")
            else:
                form_numbers = ', '.join(map(str, forms_without_csrf))
                security_issues.append(f"第 {form_numbers} 個表單缺少 CSRF 保護")
                
    except Exception as e:
        security_issues.append(f"檢查表單 CSRF 保護時發生錯誤: {str(e)}")
    
    return security_issues

def check_same_origin_policy(headers):
    """检查同源策略相关的安全配置"""
    security_issues = []
    headers_lower = {k.lower(): v for k, v in headers.items()}
    
    # CORS配置检查
    if 'access-control-allow-origin' in headers_lower:
        origin = headers_lower['access-control-allow-origin']
        if origin == '*':
            security_issues.append("CORS 配置過於寬鬆，允許所有來源訪問 (Access-Control-Allow-Origin: *)")
        elif origin.startswith('http://'):
            security_issues.append("CORS 允許非安全的 HTTP 來源訪問")
    
    # CORS凭证配置检查
    if ('access-control-allow-credentials' in headers_lower and 
        headers_lower['access-control-allow-credentials'].lower() == 'true'):
        if 'access-control-allow-origin' in headers_lower:
            origin = headers_lower['access-control-allow-origin']
            if origin == '*':
                security_issues.append("危險的CORS配置：同時允許所有來源和憑證訪問")
    
    # CORS方法配置检查
    if 'access-control-allow-methods' in headers_lower:
        methods = headers_lower['access-control-allow-methods'].upper()
        dangerous_methods = ['DELETE', 'PUT', 'TRACE', 'CONNECT']
        allowed_dangerous = [m for m in dangerous_methods if m in methods]
        if allowed_dangerous:
            security_issues.append(f"CORS 允許潛在危險的 HTTP 方法: {', '.join(allowed_dangerous)}")
    
    # CORS头部配置检查
    if 'access-control-allow-headers' in headers_lower:
        headers_allowed = headers_lower['access-control-allow-headers'].lower()
        if '*' in headers_allowed:
            security_issues.append("CORS 允許所有請求頭，可能導致安全風險")
    
    # CORS预检过期时间检查
    if 'access-control-max-age' in headers_lower:
        max_age = headers_lower['access-control-max-age']
        try:
            if int(max_age) > 86400:  # 24小时
                security_issues.append(f"CORS 預檢響應緩存時間過長 ({max_age} 秒)")
        except ValueError:
            pass
    
    # 跨域策略检查
    if 'x-permitted-cross-domain-policies' not in headers_lower:
        security_issues.append("未設置 X-Permitted-Cross-Domain-Policies 響應頭")
    elif headers_lower['x-permitted-cross-domain-policies'] == 'all':
        security_issues.append("允許所有跨域策略文件 (X-Permitted-Cross-Domain-Policies: all)")
    
    # 其他跨域安全头检查
    if 'cross-origin-embedder-policy' not in headers_lower:
        security_issues.append("未設置 Cross-Origin-Embedder-Policy 響應頭")
    
    if 'cross-origin-opener-policy' not in headers_lower:
        security_issues.append("未設置 Cross-Origin-Opener-Policy 響應頭")
    
    if 'cross-origin-resource-policy' not in headers_lower:
        security_issues.append("未設置 Cross-Origin-Resource-Policy 響應頭")
    
    return security_issues 