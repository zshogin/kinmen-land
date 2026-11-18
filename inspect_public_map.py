import urllib.request
import ssl
import re

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = "https://urban.kinmen.gov.tw/kmgis/map/publicMap.aspx"
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
    html = resp.read().decode('utf-8', errors='ignore')

print("publicMap.aspx length:", len(html))
with open("publicMap.html", "w", encoding="utf-8") as f:
    f.write(html)

# Extract scripts and config
scripts = re.findall(r'<script[^>]*src=[\'"]([^\'"]+)[\'"]', html, re.I)
print("Scripts loaded:")
for s in scripts:
    print(" ", s)

# Search for arcgis / ol / map layers / service URLs
matches = re.findall(r'(https?://[^\s\'"<>\)]+)', html, re.I)
print("\nURLs found:")
for m in set(matches):
    if any(k in m.lower() for k in ['arcgis', 'kmgis', 'nlsc', 'tgos', 'map', 'rest', 'wmts', 'wms']):
        print(" ", m)
