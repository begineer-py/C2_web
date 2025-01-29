import nmap

def scan_target(target, ports="80,443"):
    """
    使用Nmap掃描目標主機的端口和服務。
    
    :param target: 掃描的目標地址（域名或IP）
    :param ports: 掃描的端口範圍，默認為1-65535
    """
    scanner = nmap.PortScanner()
    
    print(f"開始掃描目標: {target}, 端口範圍: {ports}")
    
    try:
        # 使用 Nmap 掃描
        scanner.scan(target, ports, arguments='-sV')
        
        # 輸出掃描結果
        for host in scanner.all_hosts():
            print(f"\n目標: {host}")
            print(f"狀態: {scanner[host].state()}")
            
            for protocol in scanner[host].all_protocols():
                print(f"\n協議: {protocol}")
                ports = scanner[host][protocol].keys()
                for port in sorted(ports):
                    port_info = scanner[host][protocol][port]
                    print(f"端口: {port} | 狀態: {port_info['state']} | 服務: {port_info.get('name', '未知')} | 版本: {port_info.get('version', '未知')}")
    
    except Exception as e:
        print(f"掃描失敗: {e}")

if __name__ == "__main__":
    # 替換為需要掃描的域名或IP
    target = "example.com"
    scan_target(target)
