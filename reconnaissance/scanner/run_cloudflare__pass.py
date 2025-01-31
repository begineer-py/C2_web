import logging
import sys
from models import db, ParamSpiderResult, Target, crawler
from .check_cloudflare import check_cloudflare
from .normal_pass import scan_normal_website
from .cloudflare_bypass import bypass_cloudflare
import json

def setup_logging():
    logger = logging.getLogger(__name__)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    handler.stream.reconfigure(encoding='utf-8')
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger

logger = setup_logging()

class CrawlerPass:
    def __init__(self, user_id, target_id,limit):
        self.user_id = user_id
        self.target_id = target_id
        # 創建爬蟲記錄
        self.crawler_record = crawler(target_id=target_id)
        self.limit = limit
        db.session.add(self.crawler_record)
        db.session.commit()
        
    def process_url(self, url):
        """處理單個 URL"""
        try:
            logger.info("=" * 50)
            logger.info(f"開始處理 URL: {url}")
            
            # 檢查是否使用 Cloudflare
            is_cloudflare, message = check_cloudflare(url)
            
            if is_cloudflare:
                logger.info(f"[+] 檢測到 Cloudflare 保護：{url}")
                logger.info("[*] 嘗試繞過 Cloudflare...")
                success, message = bypass_cloudflare(url, self.crawler_record.id)
                if success:
                    logger.info(f"[√] 成功繞過 Cloudflare 並抓取內容")
                else:
                    logger.error(f"[×] Cloudflare 繞過失敗：{message}")
            else:
                logger.info(f"[+] 未檢測到 Cloudflare 保護，使用普通掃描")
                success, message = scan_normal_website(url, self.crawler_record.id)
                if success:
                    logger.info(f"[√] 成功掃描並抓取內容")
                else:
                    logger.error(f"[×] 普通掃描失敗：{message}")
            
            if not success:
                logger.error(f"[×] URL 處理失敗：{message}")
                self.crawler_record.error_message = message
            
            logger.info("-" * 50)
            return success, message
            
        except Exception as e:
            error_msg = f"處理 URL 時出錯：{str(e)}"
            logger.error(f"[×] {error_msg}")
            self.crawler_record.error_message = error_msg
            return False, error_msg
        finally:
            # 更新爬蟲記錄
            self.crawler_record.completed_at = db.func.current_timestamp()
            db.session.commit()
    
    def process_paramspider_urls(self, result_text,limit):
        """處理 ParamSpider 結果中的前十個 URL"""
        try:
            logger.info("\n" + "=" * 70)
            logger.info("開始處理 ParamSpider 結果")
            logger.info("=" * 70)
            
            # 解析結果文本
            lines = result_text.split('\n')
            urls = []
            
            # 調試輸出
            logger.info(f"[*] 原始結果行數: {len(lines)}")
            
            # 查找 URL 列表部分
            url_section_start = False
            for i, line in enumerate(lines):
                # 調試輸出
                if i < 5:  # 只顯示前5行用於調試
                    logger.debug(f"Line {i}: {line}")
                
                if "URL 列表:" in line or "URL List:" in line:
                    url_section_start = True
                    logger.info("[+] 找到 URL 列表標記")
                    continue
                    
                if url_section_start and line.strip():
                    # 提取 URL（去除 FUZZ 參數）
                    url = line.strip().replace("?FUZZ", "").replace("=FUZZ", "")
                    if url.startswith(("http://", "https://")):
                        urls.append(url)
                        logger.debug(f"[+] 找到有效 URL: {url}")
                        # 只收集前十個 URL
                        if len(urls) >= limit:
                            logger.info(f"[*] 已收集到{limit}個 URL，停止收集")
                            break
            
            if not urls:
                logger.warning("[!] 未找到有效的 URL")
                logger.info("結果文本預覽:")
                logger.info("-" * 40)
                logger.info(result_text[:200] + "...")  # 顯示前200個字符
                logger.info("-" * 40)
                return True, "未找到需要處理的 URL"
            
            # 處理前100個 URL
            processed_count = 0
            successful_count = 0
            failed_urls = []
            
            logger.info(f"\n[+] 找到 {len(urls)} 個 URL，開始處理前 {min(100, len(urls))} 個")
            logger.info("-" * 70)
            
            for url in urls:
                processed_count += 1
                logger.info(f"\n[{processed_count}/100] 處理 URL: {url}")
                success, message = self.process_url(url)
                if success:
                    successful_count += 1
                    logger.info(f"[√] URL {url} 處理成功")
                else:
                    failed_urls.append((url, message))
                    logger.error(f"[×] URL {url} 處理失敗: {message}")
            
            # 輸出總結
            logger.info("\n" + "=" * 70)
            logger.info("掃描結果總結:")
            logger.info(f"總處理 URL 數: {processed_count}")
            logger.info(f"成功處理數: {successful_count}")
            logger.info(f"失敗處理數: {len(failed_urls)}")
            
            if failed_urls:
                logger.info("\n失敗的 URL 列表:")
                for failed_url, error_msg in failed_urls:
                    logger.info(f"- {failed_url}: {error_msg}")
            
            logger.info("=" * 70)
            
            result_message = f"已處理 {processed_count} 個 URL，成功 {successful_count} 個"
            return True, result_message
            
        except Exception as e:
            error_msg = f"處理 ParamSpider 結果時出錯：{str(e)}"
            logger.error(f"[×] {error_msg}")
            return False, error_msg
    
    def process_target(self,limit=100):
        """處理目標的所有 URL"""
        try:
            logger.info("\n" + "#" * 70)
            logger.info("開始目標掃描流程")
            logger.info("#" * 70 + "\n")
            
            # 獲取目標信息
            target = Target.query.get(self.target_id)
            if not target:
                logger.error("[×] 目標不存在")
                return False, "目標不存在"
            
            logger.info("[*] 處理主要目標 URL")
            # 首先處理主 URL
            success, message = self.process_url(target.target_ip)
            if not success:
                logger.error(f"[×] 主要目標處理失敗：{message}")
                return False, message
            
            # 獲取 ParamSpider 結果
            param_result = ParamSpiderResult.query.filter_by(target_id=self.target_id).first()
            if param_result and param_result.result_text:
                logger.info("\n[*] 開始處理 ParamSpider 發現的 URL")
                success, message = self.process_paramspider_urls(param_result.result_text,limit)
                if not success:
                    logger.error(f"[×] ParamSpider URL 處理失敗：{message}")
                    return False, message
            else:
                logger.info("\n[!] 未找到 ParamSpider 結果或結果為空")
            
            logger.info("\n" + "#" * 70)
            logger.info("目標掃描流程完成")
            logger.info("#" * 70)
            
            return True, "所有 URL 處理完成"
            
        except Exception as e:
            error_msg = f"處理目標時出錯：{str(e)}"
            logger.error(f"[×] {error_msg}")
            return False, error_msg

def main(user_id, target_id):
    """主函數"""
    try:
        crawler = CrawlerPass(user_id, target_id)
        return crawler.process_target()
    except Exception as e:
        error_msg = f"執行過程出錯：{str(e)}"
        logger.error(error_msg)
        return False, error_msg


