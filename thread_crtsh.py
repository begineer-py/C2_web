import threading
from queue import Queue, Empty
from reconnaissance.security_scanning.crtsh import crtsh_scan_target
from models import db, crtsh_Result
from datetime import datetime

class crtsh_ScanThread(threading.Thread):
    def __init__(self, target_ip, user_id, target_id, app):
        threading.Thread.__init__(self)
        self.target_ip = target_ip
        self.user_id = user_id
        self.target_id = target_id
        self.app = app
        self.result = Queue()
        self.daemon = True

    def run(self):
        with self.app.app_context():
            try:
                # 执行扫描
                domains, success, message = crtsh_scan_target(self.target_ip, self.user_id, self.target_id)
                
                if success:
                    # 检查是否已存在扫描结果
                    existing_result = crtsh_Result.query.filter_by(
                        target_id=self.target_id,
                        user_id=self.user_id
                    ).first()
                    
                    # 如果存在就更新，不存在就创建新记录
                    try:
                        if existing_result:
                            existing_result.domains = domains
                            existing_result.total_domains = len(domains)
                            existing_result.scan_time = datetime.now()
                            existing_result.status = 'success'
                            existing_result.error_message = None
                        else:
                            new_result = crtsh_Result(
                                user_id=self.user_id,
                                target_id=self.target_id,
                                domains=domains,
                                total_domains=len(domains),
                                scan_time=datetime.now(),
                                status='success'
                            )
                            db.session.add(new_result)
                        
                        # 使用重试机制保存到数据库
                        max_retries = 3
                        retry_delay = 1  # 秒
                        
                        for attempt in range(max_retries):
                            try:
                                db.session.commit()
                                break
                            except Exception as e:
                                if attempt < max_retries - 1:
                                    db.session.rollback()
                                    self.app.logger.warning(f"保存扫描结果时发生错误，尝试重试 {attempt + 1}/{max_retries}")
                                    threading.Event().wait(retry_delay)
                                else:
                                    raise e
                        
                        # 构建返回结果
                        result = {
                            'domains': domains,
                            'total': len(domains),
                            'scan_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'status': 'success'
                        }
                        self.result.put((result, True, 200))
                        
                    except Exception as e:
                        db.session.rollback()
                        error_msg = f"保存扫描结果时发生错误: {str(e)}"
                        self.app.logger.error(error_msg)
                        self.result.put(({'error': error_msg}, False, 500))
                else:
                    self.result.put(({'error': message}, False, 400))
                    
            except Exception as e:
                error_msg = f"扫描过程中发生错误: {str(e)}"
                self.app.logger.error(error_msg)
                self.result.put(({'error': error_msg}, False, 500))

    def get_result(self, timeout=300):  # 默认超时时间设为5分钟
        try:
            return self.result.get(timeout=timeout)
        except Empty:
            return {'error': '扫描超时'}, False, 408  # 408 是超时状态码