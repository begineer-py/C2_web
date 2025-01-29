import argparse
import asyncio
import aiohttp
import time
from typing import List, Dict
import logging
import platform
import sys
import random
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if platform.system() == 'Windows':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

class EnhancedLoadTester:
    def __init__(self, target_url: str, num_requests: int, concurrent_users: int):
        self.target_url = target_url
        self.num_requests = num_requests
        self.concurrent_users = concurrent_users
        self.results: List[Dict] = []
        
        # 模擬不同的用戶代理
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'
        ]
        
    async def make_request(self, session: aiohttp.ClientSession) -> Dict:
        headers = {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/json',
            'Accept-Language': 'zh-TW,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive'
        }
        
        start_time = time.time()
        try:
            async with session.get(
                self.target_url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30),
                allow_redirects=True
            ) as response:
                await response.text()
                return {
                    'time': time.time() - start_time,
                    'status': response.status,
                    'size': len(await response.text())
                }
        except Exception as e:
            logger.error(f"請求失敗: {str(e)}")
            return {'time': -1, 'status': 0, 'size': 0, 'error': str(e)}

    async def run_test(self):
        conn = aiohttp.TCPConnector(limit=self.concurrent_users)
        async with aiohttp.ClientSession(connector=conn) as session:
            tasks = []
            for _ in range(self.num_requests):
                tasks.append(self.make_request(session))
                if len(tasks) >= self.concurrent_users:
                    completed = await asyncio.gather(*tasks)
                    self.results.extend(completed)
                    tasks = []
                    await asyncio.sleep(0.1)  # 避免請求過於密集
            
            if tasks:
                completed = await asyncio.gather(*tasks)
                self.results.extend(completed)

    def print_results(self):
        successful_requests = [r for r in self.results if r['time'] != -1]
        if not successful_requests:
            logger.error("所有請求都失敗了")
            return

        total_bytes = sum(r['size'] for r in successful_requests)
        avg_time = sum(r['time'] for r in successful_requests) / len(successful_requests)
        
        logger.info(f"\n===== 測試結果 =====")
        logger.info(f"總請求數: {len(self.results)}")
        logger.info(f"成功請求數: {len(successful_requests)}")
        logger.info(f"平均響應時間: {avg_time:.2f} 秒")
        logger.info(f"總傳輸數據: {total_bytes/1024:.2f} KB")
        logger.info(f"請求成功率: {(len(successful_requests)/len(self.results))*100:.1f}%")
        
        # 統計HTTP狀態碼
        status_counts = {}
        for r in self.results:
            status = r.get('status', 0)
            status_counts[status] = status_counts.get(status, 0) + 1
        
        logger.info("\nHTTP狀態碼統計:")
        for status, count in status_counts.items():
            logger.info(f"狀態碼 {status}: {count} 次")

def main():
    parser = argparse.ArgumentParser(description='增強型網站負載測試工具')
    parser.add_argument('url', help='目標URL')
    parser.add_argument('-n', '--num-requests', type=int, default=100, help='總請求數')
    parser.add_argument('-c', '--concurrent-users', type=int, default=10, help='並發用戶數')
    
    args = parser.parse_args()
    
    tester = EnhancedLoadTester(args.url, args.num_requests, args.concurrent_users)
    asyncio.run(tester.run_test())
    tester.print_results()

if __name__ == "__main__":
    main() 