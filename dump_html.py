import urllib.request
import ssl
import re

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

req = urllib.request.Request('https://plvr.land.moi.gov.tw/DownloadOpenData', headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
    html = resp.read().decode('utf-8', errors='ignore')

with open('download_page.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("Saved HTML, length:", len(html))

# Let's search for script tags or ajax calls
for line in html.splitlines():
    if any(k in line for k in ['Download', 'ajax', 'season', 'lvr_land']):
        print(line[:120].strip())
