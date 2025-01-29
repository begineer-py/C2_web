import os
import sys
import json
import logging
import subprocess
from datetime import datetime
from flask import current_app
from urllib.parse import urlparse

# 添加 ParamSpider 到 Python 路徑
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(base_dir)

from tools.ParamSpider.paramspider.main import fetch_and_clean_urls, setup_logging

class ParamSpiderScanner:
    def __init__(self, target_id, user_id, crawler_id, exclude='', threads=50):
        self.target_id = target_id
        self.user_id = user_id
        self.crawler_id = crawler_id
        self.exclude = exclude
        self.threads = threads
        self.batch_size = 1000  # 每批处理的 URL 数量
        
        # 設置日誌編碼為 UTF-8
        self.logger = logging.getLogger(__name__)
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        handler.stream.reconfigure(encoding='utf-8')
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def _create_result_record(self):
        """創建掃描結果記錄"""
        from models import ParamSpiderResult, db
        
        result = ParamSpiderResult(
            target_id=self.target_id,
            user_id=self.user_id,
            crawler_id=self.crawler_id,
            exclude=self.exclude,
            threads=self.threads,
            status='running'
        )
        db.session.add(result)
        db.session.commit()
        return result.id

    def _sanitize_text(self, text):
        """清理并确保文本是 UTF-8 编码的字符串"""
        try:
            # 如果是二进制，尝试解码
            if isinstance(text, bytes):
                return text.decode('utf-8', errors='ignore')
            # 确保是字符串
            text = str(text)
            # 移除不可打印字符
            return ''.join(char for char in text if char.isprintable() or char in '\n\r\t')
        except Exception as e:
            self.logger.error(f"Error sanitizing text: {str(e)}")
            return ''

    def _process_urls_batch(self, urls):
        """处理一批 URL，提取参数并返回结果文本"""
        unique_params = set()
        processed_urls = []
        
        for url in urls:
            try:
                # 清理 URL 文本
                url = self._sanitize_text(url)
                if not url:
                    continue
                    
                if "?" in url:
                    params = url.split('?')[1].split('&')
                    for param in params:
                        param_name = self._sanitize_text(param.split('=')[0])
                        if param_name:  # 只添加非空参数
                            unique_params.add(param_name)
                    processed_urls.append(url)
            except Exception as e:
                self.logger.error(f"Error processing URL: {str(e)}")
                continue
                
        return processed_urls, unique_params

    def _generate_result_text(self, target_id, user_id, crawler_id, domain, total_urls, unique_params, processed_urls):
        """生成结果文本，确保所有内容都是纯文本"""
        try:
            # 清理所有文本内容
            domain = self._sanitize_text(domain)
            params_list = [self._sanitize_text(p) for p in unique_params if p]
            urls_list = [self._sanitize_text(u) for u in processed_urls if u]
            
            # 生成参数和 URL 列表文本
            params_text = ', '.join(sorted(params_list))
            urls_text = '\n'.join(urls_list)
            
            result_text = f"""掃描目標 ID: {target_id}
用戶 ID: {user_id}
爬蟲 ID: {crawler_id}
掃描域名: {domain}

當前處理 URL 數: {total_urls}
當前唯一參數數: {len(params_list)}

參數列表:
{params_text}

URL 列表:
{urls_text}"""
            
            # 最后一次清理整个文本
            return self._sanitize_text(result_text)
            
        except Exception as e:
            self.logger.error(f"Error generating result text: {str(e)}")
            return "Error generating result text"

    def scan(self, target_url):
        """執行 ParamSpider 掃描"""
        result_id = self._create_result_record()
        
        try:
            # 從 URL 中提取域名
            parsed_url = urlparse(str(target_url))
            domain = parsed_url.netloc or parsed_url.path
            
            # 設置 ParamSpider 日誌
            setup_logging(stream_handler=False)
            
            # 執行掃描
            urls = fetch_and_clean_urls(
                domain=domain,
                stream_output=False,
                proxy=None
            )
            
            if urls:
                all_unique_params = set()
                all_processed_urls = []
                total_urls = 0
                
                # 分批处理 URL
                for i in range(0, len(urls), self.batch_size):
                    batch_urls = urls[i:i + self.batch_size]
                    processed_urls, batch_params = self._process_urls_batch(batch_urls)
                    
                    all_unique_params.update(batch_params)
                    all_processed_urls.extend(processed_urls)
                    total_urls += len(processed_urls)
                    
                    # 生成当前批次的结果文本并更新数据库
                    current_result_text = self._generate_result_text(
                        self.target_id,
                        self.user_id,
                        self.crawler_id,
                        domain,
                        total_urls,
                        all_unique_params,
                        all_processed_urls
                    )

                    self._update_result_status(
                        result_id,
                        'processing',
                        result_text=current_result_text,
                        total_urls=total_urls,
                        unique_parameters=len(all_unique_params)
                    )
                
                # 更新最终状态
                final_result_text = self._generate_result_text(
                    self.target_id,
                    self.user_id,
                    self.crawler_id,
                    domain,
                    total_urls,
                    all_unique_params,
                    all_processed_urls
                )
                
                self._update_result_status(
                    result_id,
                    'completed',
                    result_text=final_result_text,
                    total_urls=total_urls,
                    unique_parameters=len(all_unique_params)
                )
                
                return {
                    'status': 'success',
                    'result_text': f'扫描完成，共发现 {total_urls} 个 URL，{len(all_unique_params)} 个唯一参数',
                    'total_urls': total_urls,
                    'unique_parameters': len(all_unique_params)
                }
            else:
                result_text = '未找到包含參數的 URL'
                self._update_result_status(
                    result_id, 
                    'completed', 
                    result_text=result_text,
                    total_urls=0,
                    unique_parameters=0
                )
                return {
                    'status': 'success', 
                    'result_text': result_text,
                    'total_urls': 0,
                    'unique_parameters': 0
                }

        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"Scan error: {error_msg}")
            self._update_result_status(result_id, 'error', error_message=error_msg)
            return {
                'status': 'error',
                'message': '掃描失敗',
                'error_detail': str(e)
            } 

    def _update_result_status(self, result_id, status, error_message=None, result_text=None, total_urls=0, unique_parameters=0):
        """更新掃描結果狀態"""
        from models import ParamSpiderResult, db
        
        result = ParamSpiderResult.query.get(result_id)
        if result:
            result.status = self._sanitize_text(status)
            if error_message:
                result.error_message = self._sanitize_text(error_message)
            if result_text is not None:
                result.result_text = self._sanitize_text(result_text)
            result.total_urls = total_urls
            result.unique_parameters = unique_parameters
            try:
                db.session.commit()
            except Exception as e:
                self.logger.error(f"Error updating result status: {str(e)}")
                db.session.rollback()
                raise 