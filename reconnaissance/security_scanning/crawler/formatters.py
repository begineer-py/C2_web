def format_curl_result(url, response, ssl_info=None, cookies=None, security_issues=None):
    """格式化curl扫描结果"""
    result = []
    
    # 基本信息
    result.append("=" * 50)
    result.append("基本信息")
    result.append("=" * 50)
    result.append(f"目標網址: {url}")
    result.append(f"HTTP 狀態碼: {response.status_code}")
    result.append(f"響應時間: {response.elapsed.total_seconds():.2f} 秒")
    result.append(f"響應大小: {len(response.content)} 字節")
    
    # 网页标题
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')
        title = soup.title.string if soup.title else "無標題"
        result.append(f"網頁標題: {title}")
    except:
        result.append("網頁標題: 無法解析")
    
    # 服务器信息
    result.append("\n" + "=" * 50)
    result.append("服務器信息")
    result.append("=" * 50)
    server = response.headers.get('Server', '未知')
    result.append(f"服務器: {server}")
    result.append(f"服務器時間: {response.headers.get('Date', '未知')}")
    result.append(f"內容類型: {response.headers.get('Content-Type', '未知')}")
    result.append(f"字符編碼: {response.encoding}")
    
    # 响应头信息
    result.append("\n" + "=" * 50)
    result.append("響應頭信息")
    result.append("=" * 50)
    for header, value in response.headers.items():
        if header.lower() not in ['set-cookie']:  # 排除cookie信息，单独显示
            result.append(f"  {header}: {value}")
    
    # SSL/TLS证书信息
    if ssl_info:
        result.append("\n" + "=" * 50)
        result.append("SSL/TLS 證書信息")
        result.append("=" * 50)
        result.append(f"  版本: {ssl_info.get('version', '未知')}")
        result.append(f"  頒發者: {format_dict(ssl_info.get('issuer', {}))}")
        result.append(f"  主題: {format_dict(ssl_info.get('subject', {}))}")
        result.append(f"  有效期開始: {ssl_info.get('notBefore', '未知')}")
        result.append(f"  有效期結束: {ssl_info.get('notAfter', '未知')}")
        result.append(f"  簽名算法: {ssl_info.get('signatureAlgorithm', '未知')}")
    
    # Cookie信息
    if cookies:
        result.append("\n" + "=" * 50)
        result.append("Cookie 信息")
        result.append("=" * 50)
        for cookie in cookies:
            result.append(f"  Cookie: {cookie.name}")
            result.append(f"    值: {cookie.value}")
            result.append(f"    域: {cookie.domain}")
            result.append(f"    路徑: {cookie.path}")
            result.append(f"    過期時間: {cookie.expires}")
            result.append(f"    HttpOnly: {cookie.has_nonstandard_attr('HttpOnly')}")
            result.append(f"    Secure: {cookie.secure}")
            result.append("")
    
    # 安全问题
    if security_issues:
        result.extend(format_security_issues(security_issues))
    
    return "\n".join(result)

def format_security_issues(security_issues):
    """格式化安全问题"""
    if not security_issues:
        return [
            "\n" + "=" * 50,
            "安全配置檢查",
            "=" * 50,
            "未發現明顯的安全問題"
        ]
    
    result = [
        "\n" + "=" * 50,
        "安全配置檢查",
        "=" * 50,
        "發現以下潛在問題:"
    ]
    
    for issue in security_issues:
        result.append(f"⚠️ {issue}")
    
    return result

def format_dict(d):
    """格式化字典输出"""
    if not d:
        return "未知"
    return ", ".join(f"{k}={v}" for k, v in d.items()) 