import requests

def crtsh_scan_target(target_id):
    url = f"https://crt.sh/?q={target_id}&output=json"
    response = requests.get(url)
    return response.json()