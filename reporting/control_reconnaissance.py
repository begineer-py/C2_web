from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os
import logging
from flask_migrate import Migrate

# 設定日誌
logging.basicConfig(filename="control_reconnaissance_site.log", level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 獲取當前文件的路徑
file_path = os.path.dirname(os.path.abspath(__file__))
save_path = os.path.join(file_path, "database", "site.db")

# 創建 Flask 應用
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{save_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 初始化 SQLAlchemy
db = SQLAlchemy(app)
migrate = Migrate(app, db)
class LinksCom(db.Model):
    """包含 '.com' 的鏈接模型"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=True)

    def __repr__(self):
        return f"<LinksCom '{self.name}'>"


class LinksNotCom(db.Model):
    """不包含 '.com' 的鏈接模型"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=True)

    def __repr__(self):
        return f"<LinksNotCom '{self.name}'>"


class Links_desigm_Com(db.Model):
    """包含 '.com' 的鏈接模型，包含技術棧"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=True)
    technology_stack = db.Column(db.String(80), nullable=False)

    def __repr__(self):
        return f"<Links_desigm_Com name='{self.name}', technology_stack='{self.technology_stack}'>"


class Links_desigm_not_Com(db.Model):
    """不包含 '.com' 的鏈接模型，包含技術棧"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=True)
    technology_stack = db.Column(db.String(80), nullable=False)

    def __repr__(self):
        return f"<Links_desigm_not_Com name='{self.name}', technology_stack='{self.technology_stack}'>"

def create_database():
    """創建數據庫和表"""
    with app.app_context():
        db.create_all()
        logger.info("數據庫和表已創建！")

def handle_db_exception(e, action):
    logger.error(f"{action} 時出錯: {e}")
    db.session.rollback()

def add_link(name, is_com=True):
    """向對應的鏈接表中添加一個鏈接"""
    with app.app_context():
        try:
            if is_com:
                existing_link = LinksCom.query.filter_by(name=name).first()
                if existing_link is None:
                    new_link = LinksCom(name=name)
                    db.session.add(new_link)
                    logger.info(f"已添加 '.com' 鏈接: {name}")
                else:
                    logger.warning(f"鏈接已存在: {name}")
            else:
                existing_link = LinksNotCom.query.filter_by(name=name).first()
                if existing_link is None:
                    new_link = LinksNotCom(name=name)
                    db.session.add(new_link)
                    logger.info(f"已添加 非 '.com' 鏈接: {name}")
                else:
                    logger.warning(f"鏈接已存在: {name}")

            db.session.commit()

        except Exception as e:
            handle_db_exception(e, f"添加 {'的 .com' if is_com else '非 .com'} 鏈接")

def query_links(domain_type):
    """查詢所有鏈接，根據 domain_type 決定 '.com' 或非 '.com'"""
    with app.app_context():
        if domain_type and issubclass(domain_type, db.Model):
            try:
                links = domain_type.query.all()
                logger.info(f"查詢所有{domain_type.__name__} 鏈接完成")
                logger.info(links)
                return links
            except Exception as e:
                logger.error(f"查詢鏈接時發生錯誤: {str(e)}")
                return None
        else:
            logger.error("無效的 domain_type 參數")
            return None

        
        
def print_links(links):
    """打印鏈接列表"""
    for link in links:
        print(f"ID: {link.id}, Name: {link.name}")

def remove_duplicates(table_info):
    """通用函數，用於刪除表中的重複鏈接"""
    with app.app_context():
        try:
            model = globals().get(table_info)
            duplicates = db.session.query(model.name, db.func.count(model.id))\
                .group_by(model.name)\
                .having(db.func.count(model.id) > 1).all()

            to_delete = []
            for name, count in duplicates:
                duplicate_links = model.query.filter_by(name=name).all()
                to_delete.extend(duplicate_links[1:])

                logger.info(f"鏈接: {name} 出現了 {count} 次，將刪除 {count - 1} 個重複項")
            for delite in to_delete:
                db.session.delete(delite)
                db.session.commit()

            logger.info(f"{model.__name__} 中所有重複鏈接已刪除！")
            print(f"{model.__name__} 中所有重複鏈接已刪除！")

        except Exception as e:
            handle_db_exception(e, f"刪除 {model.__name__} 表中的重複鏈接")

# 使用範例
if __name__ == '__main__':
    create_database()
    add_link("example.com", is_com=True)   # 添加 '.com' 鏈接
    add_link("example.org", is_com=False)   # 添加非 '.com' 鏈接
    remove_duplicates("LinksCom")
    remove_duplicates("LinksNotCom")
    print("search in links_com")
    query_links(LinksCom)      # 查詢所有 '.com' 鏈接
    print("search in links_not_com")
    query_links(LinksNotCom)  # 查詢所有非 '.com' 鏈接
