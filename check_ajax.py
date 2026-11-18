import urllib.request
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
    'X-Requested-With': 'XMLHttpRequest'
}

for endpoint in ['Download_ajax_active', 'DownloadHistory_ajax_list']:
    url = f'https://plvr.land.moi.gov.tw/{endpoint}'
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
            content = resp.read().decode('utf-8', errors='ignore')
            print(f"=== {endpoint} (len: {len(content)}) ===")
            print(content[:500])
            with open(f"{endpoint}.html", "w", encoding="utf-8") as f:
                f.write(content)
    except Exception as e:
        print(f"Error for {endpoint}: {e}")
