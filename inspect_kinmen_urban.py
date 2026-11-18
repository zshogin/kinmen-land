import urllib.request
import ssl
import re

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = "https://urban.kinmen.gov.tw/kmgis/publicweb/index.aspx"
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
    html = resp.read().decode('utf-8', errors='ignore')

print("Page length:", len(html))
with open("kinmen_urban_page.html", "w", encoding="utf-8") as f:
    f.write(html)

# Extract scripts, links, services
scripts = re.findall(r'<script[^>]*src=[\'"]([^\'"]+)[\'"]', html, re.I)
print("Scripts loaded:")
for s in scripts[:15]:
    print(" ", s)

# Find arcgis / openlayers / leaflet / map services
services = re.findall(r'(https?://[^\s\'"<>]+(?:arcgis|rest|wms|wmts|service)[^\s\'"<>]*)', html, re.I)
print("External Map Services:")
for s in set(services):
    print(" ", s)
