#!/usr/bin/env python3
import argparse
from pathlib import Path
from datetime import datetime
from harvester import run_harvester, show_sources
from nikto import run_nikto

def main():
    parser = argparse.ArgumentParser(
        description='安全掃描工具',
        epilog='整合了 theHarvester 和 Nikto 的掃描工具'
    )
    parser.add_argument('-d', '--domain', required=True, help='目標域名')
    parser.add_argument('-l', '--limit', type=int, default=100, help='theHarvester 結果數量限制 (默認: 100)')
    parser.add_argument('-b', '--source', default='bing', help='theHarvester 搜索源 (默認: bing)')
    parser.add_argument('--list-sources', action='store_true', help='顯示所有可用的搜索源')
    parser.add_argument('--skip-nikto', action='store_true', help='跳過 Nikto 掃描')
    
    args = parser.parse_args()
    
    if args.list_sources:
        show_sources()
        return
    
    print("""
    ╔══════════════════════════════════════╗
    ║           安全掃描工具               ║
    ╚══════════════════════════════════════╝
    """)
    
    # 生成輸出目錄
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    safe_domain = "".join(c for c in args.domain if c.isalnum() or c in ('-', '.'))
    base_dir = Path(__file__).parent.parent / 'reporting'
    domain_dir = base_dir / safe_domain
    output_dir = domain_dir / timestamp
    
    # 確保目錄存在
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 運行 theHarvester
    run_harvester(args.domain, args.limit, args.source, output_dir)
    
    # 如果沒有跳過 Nikto 掃描，則運行 Nikto
    if not args.skip_nikto:
        run_nikto(args.domain, output_dir)

if __name__ == '__main__':
    main()