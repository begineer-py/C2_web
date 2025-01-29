import requests
import re
from models import db, webtech_Result
from flask import current_app
import json
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from datetime import datetime

def webtech_scan_target(domain, user_id, target_id):
    """
    分析网站使用的技术
    :param domain: 目标域名
    :param user_id: 用户ID
    :param target_id: 目标ID
    :return: 扫描结果
    """
    try:
        current_app.logger.debug(f"开始网站技术扫描: {domain}")
        
        # 确保域名包含协议
        if not domain.startswith(('http://', 'https://')):
            domain = f'https://{domain}'
        
        # 发送请求
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(domain, headers=headers, timeout=10, verify=False)
        
        # 获取技术信息
        tech_info = analyze_technologies(response)
        
        # 格式化结果
        formatted_result = format_webtech_result(tech_info, domain)
        
        try:
            # 将字典转换为JSON字符串
            result_json = json.dumps(formatted_result)
            
            # 将结果保存到数据库
            db.session.add(webtech_Result(
                user_id=user_id,
                target_id=target_id,
                webtech_result=result_json
            ))
            db.session.commit()
            current_app.logger.debug("扫描结果已保存到数据库")
            
            return formatted_result, True, 200
            
        except Exception as db_error:
            db.session.rollback()
            current_app.logger.error(f"保存到数据库时发生错误: {db_error}")
            return "数据库错误", False, 500
        
    except Exception as e:
        current_app.logger.error(f"扫描过程中发生错误: {e}")
        return f"扫描错误: {str(e)}", False, 500

def analyze_technologies(response):
    """
    分析网站使用的技术
    """
    technologies = []
    
    # 获取响应头和内容
    headers = response.headers
    content = response.text
    soup = BeautifulSoup(content, 'html.parser')
    
    # 检查服务器和 CDN
    if 'CF-RAY' in headers or 'cloudflare' in str(headers).lower():
        technologies.append({
            'name': 'Cloudflare',
            'categories': ['CDN'],
            'confidence': 100
        })
    elif 'Server' in headers and 'cloudflare' not in headers['Server'].lower():
        # 只在不是 Cloudflare 时添加服务器信息
        server = headers['Server']
        technologies.append({
            'name': server,
            'categories': ['Web Server'],
            'confidence': 100
        })
    
    # 检查其他 CDN
    if 'X-Cache' in headers and 'fastly' in headers['X-Cache'].lower():
        technologies.append({
            'name': 'Fastly',
            'categories': ['CDN'],
            'confidence': 100
        })
    elif 'X-Akamai-Transformed' in headers:
        technologies.append({
            'name': 'Akamai',
            'categories': ['CDN'],
            'confidence': 100
        })
    
    # 检查编程语言和框架
    if 'X-Powered-By' in headers:
        tech_name = headers['X-Powered-By']
        # 过滤掉一些常见的误报
        if not any(x in tech_name.lower() for x in ['plesk', 'cpanel', 'webserver']):
            technologies.append({
                'name': tech_name,
                'categories': ['Programming Language'],
                'confidence': 90
            })
    
    # 检查前端框架和库
    js_frameworks = {
        'react': {
            'name': 'React',
            'indicators': [
                'react.development.js',
                'react.production.min.js',
                '_reactRootContainer',
                'data-reactroot',
                '__REACT_DEVTOOLS_GLOBAL_HOOK__'
            ]
        },
        'vue': {
            'name': 'Vue.js',
            'indicators': [
                'vue.js',
                'vue.min.js',
                '__vue__',
                'data-v-',
                'Vue.config'
            ]
        },
        'angular': {
            'name': 'Angular',
            'indicators': [
                'angular.js',
                'ng-app',
                'ng-controller',
                'ng-model',
                'angular.min.js'
            ]
        },
        'jquery': {
            'name': 'jQuery',
            'indicators': [
                'jquery.js',
                'jquery.min.js',
                'jQuery.fn',
                'jquery-'
            ]
        }
    }
    
    # 检查 HTML 内容中的框架特征
    for framework, info in js_frameworks.items():
        confidence = 0
        for indicator in info['indicators']:
            if indicator in content:
                confidence += 20  # 每个特征增加 20% 的置信度
        if confidence > 0:
            technologies.append({
                'name': info['name'],
                'categories': ['Frontend Framework'],
                'confidence': min(confidence, 100)  # 最高 100%
            })
    
    # 检查常见的 CMS 特征
    cms_patterns = {
        'WordPress': {
            'patterns': ['/wp-content/', '/wp-includes/', 'wp-json', 'wp-admin'],
            'meta': ['generator', 'WordPress']
        },
        'Drupal': {
            'patterns': [
                '/sites/default/',
                'Drupal.settings',
                'drupal.js',
                '/core/misc/drupal'
            ],
            'meta': ['generator', 'Drupal']
        },
        'Ruby on Rails': {
            'patterns': [
                'rails-ujs',
                'data-remote="true"',
                'csrf-token',
                '/assets/application-'
            ]
        }
    }
    
    for cms, info in cms_patterns.items():
        confidence = 0
        # 检查模式
        patterns = info.get('patterns', [])
        for pattern in patterns:
            if pattern in content:
                confidence += 30
        
        # 检查元标签
        if 'meta' in info:
            meta_tags = soup.find_all('meta', {'name': info['meta'][0]})
            for meta in meta_tags:
                if info['meta'][1].lower() in meta.get('content', '').lower():
                    confidence += 40
        
        if confidence > 0:
            technologies.append({
                'name': cms,
                'categories': ['CMS/Framework'],
                'confidence': min(confidence, 100)
            })
    
    # 检查安全头部
    security_headers = {
        'X-Frame-Options': {'name': 'Frame Protection', 'category': 'Security'},
        'X-XSS-Protection': {'name': 'XSS Protection', 'category': 'Security'},
        'Content-Security-Policy': {'name': 'CSP', 'category': 'Security'},
        'Strict-Transport-Security': {'name': 'HSTS', 'category': 'Security'},
        'X-Content-Type-Options': {'name': 'Content Type Options', 'category': 'Security'},
        'Referrer-Policy': {'name': 'Referrer Policy', 'category': 'Security'}
    }
    
    for header, info in security_headers.items():
        if header in headers:
            value = headers[header]
            # 简化一些过长的值
            if len(value) > 100:
                value = value[:100] + '...'
            technologies.append({
                'name': info['name'],
                'version': value,
                'categories': [info['category']],
                'confidence': 100
            })
    
    # 检查 Cookie 安全性
    if 'Set-Cookie' in headers:
        cookies = headers.get_all('Set-Cookie') if hasattr(headers, 'get_all') else [headers['Set-Cookie']]
        secure_flags = set()  # 使用集合避免重复
        
        for cookie in cookies:
            if 'Secure' in cookie:
                secure_flags.add('Secure')
            if 'HttpOnly' in cookie:
                secure_flags.add('HttpOnly')
            if 'SameSite' in cookie:
                secure_flags.add('SameSite')
        
        if secure_flags:
            technologies.append({
                'name': 'Cookie Security',
                'version': ', '.join(secure_flags),
                'categories': ['Security'],
                'confidence': 100
            })
    
    return technologies

def format_webtech_result(tech_info, domain):
    """
    格式化扫描结果为结构化数据
    """
    # 初始化结果字典
    result = {
        'technologies': [],
        'target_url': domain,
        'scan_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    if not tech_info:
        return result
    
    # 将技术信息转换为结构化数据
    for tech in tech_info:
        tech_data = {
            'name': tech.get('name', '未知'),
            'version': tech.get('version', ''),
            'categories': tech.get('categories', ['其他']),
            'confidence': tech.get('confidence', 0)
        }
        result['technologies'].append(tech_data)
    
    return result


