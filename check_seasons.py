import urllib.request
import ssl
import re

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = "https://plvr.land.moi.gov.tw/DownloadSeason_ajax_list"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'X-Requested-With': 'XMLHttpRequest'})
try:
    with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
        content = resp.read().decode('utf-8', errors='ignore')
        opts = re.findall(r'<option[^>]*value=[\'"]?([^\'">\s]+)[\'"]?[^>]*>(.*?)</option>', content)
        print("Available seasons count:", len(opts))
        for val, label in opts[:20]:
            print(f"Season: val={val}, label={label.strip()}")
except Exception as e:
    print("Error:", e)
