import logging
import sys
from flask import with_appcontext
from models import db,ParamSpiderResult,Target
from check_cloudflare import check_cloudflare
from normal_pass import NormalRequest
def setup_logging():
    logger = logging.getLogger(__name__)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    handler.stream.reconfigure(encoding='utf-8')
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger
logger = setup_logging()
class crawler_pass:
    def __init__(self,user_id,target_id,crawler_id):
        self.user_id = user_id
        self.target_id = with_appcontext(lambda: Target.query.filter_by(id=target_id).first().domain)
        self.crawler_id = crawler_id
        self.links = with_appcontext(lambda: ParamSpiderResult.query.filter_by(crawler_id=crawler_id).first().result_text)
    def cloudflare_check(self,url):
        code , message = check_cloudflare(url)#如果使用Cloudflare，則返回True,如果未使用Cloudflare，則返回False
        if code:
            self.cloudflare_pass(self.target_id)
        else:#如果未使用Cloudflare，則使用NormalRequest
            normal_request = NormalRequest()
            for link in self.links:
                normal_request.make_request(link)
    def cloudflare_pass(self,url):#如果使用Cloudflare，則使用此方法
        code , message = check_cloudflare(url)#如果使用Cloudflare，則返回True,如果未使用Cloudflare，則返回False
        if code:
            pass
        else:
            normal_request = NormalRequest()
            for link in self.links:
                normal_request.make_request(link)


