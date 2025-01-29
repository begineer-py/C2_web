from pathlib import Path
from datetime import datetime
import subprocess
import sys

AVAILABLE_SOURCES = [
    'anubis', 'baidu', 'bevigil', 'binaryedge', 'bing', 'brave',
    'censys', 'certspotter', 'criminalip', 'crtsh', 'dnsdumpster',
    'duckduckgo', 'fullhunt', 'github-code', 'hackertarget', 'hunter',
    'hunterhow', 'intelx', 'netlas', 'onyphe', 'otx', 'pentesttools',
    'projectdiscovery', 'rapiddns', 'rocketreach', 'securityTrails',
    'sitedossier', 'subdomaincenter', 'subdomainfinderc99', 'threatminer',
    'tomba', 'urlscan', 'virustotal', 'yahoo', 'zoomeye'
]

def validate_sources(source):
    """驗證搜索源是否有效"""
    if source.lower() == 'all':
        return 'all'
        
    sources = [s.strip() for s in source.split(',')]
    invalid_sources = [s for s in sources if s not in AVAILABLE_SOURCES]
    
    if invalid_sources:
        print(f"\n[-] 錯誤: 無效的搜索源: {', '.join(invalid_sources)}")
        print("\n[*] 提示: 使用 -h 查看幫助")
        show_sources()
        sys.exit(1)
    
    return source

def show_sources():
    """顯示所有可用的搜索源"""
    print("\n可用的搜索源:")
    print("-" * 60)
    for i in range(0, len(AVAILABLE_SOURCES), 4):
        row = AVAILABLE_SOURCES[i:i+4]
        print("  ".join(f"{s:<15}" for s in row))
    print("\n使用示例:")
    print("  單個源: -b bing")
    print("  多個源: -b \"bing,yahoo,baidu\"")
    print("  所有源: -b all")
    print("-" * 60)

def run_harvester(domain, limit=100, source='bing', output_dir=None):
    """
    運行 theHarvester
    
    Args:
        domain: 目標域名
        limit: 結果數量限制
        source: 搜索源
        output_dir: 輸出目錄
    """
    # 驗證搜索源
    source = validate_sources(source)
    
    # 獲取當前腳本的目錄
    current_dir = Path(__file__).parent.resolve()
    base_dir = current_dir.parent
    
    # 計算 theHarvester.py 的路徑
    harvester_path = base_dir / 'theHarvester' / 'theHarvester.py'
    
    # 确保 harvester_path 存在
    if not harvester_path.exists():
        print(f"[-] 错误: 未找到 theHarvester.py 脚本: {harvester_path}")
        return
    
    # 如果沒有提供輸出目錄，則創建一個
    if output_dir is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_domain = "".join(c for c in domain if c.isalnum() or c in ('-', '.'))
        output_dir = base_dir / 'reporting' / safe_domain / timestamp
    
    # 確保輸出目錄存在
    harvester_dir = output_dir / 'harvester'
    harvester_dir.mkdir(parents=True, exist_ok=True)
    
    # 構建命令
    cmd = [
        sys.executable,
        str(harvester_path),
        '-d', domain,
        '-l', str(limit),
        '-b', source,
        '-f', str(harvester_dir / 'results')  # 使用完整的絕對路徑
    ]
    
    try:
        print(f"[*] 創建輸出目錄: {harvester_dir}")
        print(f"[*] 運行命令: {' '.join(cmd)}")
        
        # 在 theHarvester 目錄下運行命令
        process = subprocess.run(
            cmd,
            check=True,
            cwd=str(harvester_path.parent)  # 确保这个路径是有效的目录
        )
        
        if process.returncode == 0:
            print(f"\n[+] theHarvester 掃描完成！")
            
            # 檢查生成的文件
            expected_files = [
                harvester_dir / f"results.{ext}"
                for ext in ['xml', 'json', 'txt']
            ]
            
            found_files = False
            for file_path in expected_files:
                if file_path.exists():
                    print(f"    [+] 找到文件: {file_path}")
                    found_files = True
                else:
                    print(f"    [-] 未找到文件: {file_path}")
            
            if not found_files:
                print("\n[!] 警告: 沒有找到任何輸出文件")
                print(f"[*] 檢查目錄: {harvester_dir}")
                if harvester_dir.exists():
                    print("[*] 目錄內容:")
                    for item in harvester_dir.iterdir():
                        print(f"    - {item}")
            
            # 創建摘要文件
            summary_file = harvester_dir / 'summary.txt'
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write(f"掃描目標: {domain}\n")
                f.write(f"掃描時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"使用的搜索源: {source}\n")
                f.write(f"結果限制: {limit}\n")
            print(f"\n[+] 創建摘要文件: {summary_file}")
            
        else:
            print(f"\n[-] 掃描失敗，返回碼: {process.returncode}")
            
    except subprocess.CalledProcessError as e:
        print(f"\n[-] 執行出錯: {e}")
    except Exception as e:
        print(f"\n[-] 發生錯誤: {e}")
        import traceback
        traceback.print_exc() 