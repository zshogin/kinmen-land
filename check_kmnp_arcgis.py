import urllib.request
import ssl
import json

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

test_urls = [
    "https://gismap.kmnp.gov.tw/arcgis/rest/services?f=pjson",
    "https://gismap.kmnp.gov.tw/arcgiswa/rest/services?f=pjson",
    "https://npmap.nps.gov.tw/arcgis/rest/services?f=pjson",
    "https://npmap.nps.gov.tw/arcgiswa/rest/services?f=pjson",
    "https://gis.kmnp.gov.tw/arcgis/rest/services?f=pjson"
]

for u in test_urls:
    print(f"Checking {u}...")
    req = urllib.request.Request(u, headers=headers)
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=6) as resp:
            print(f"  [FOUND] HTTP {resp.status}")
    except Exception as e:
        print(f"  [ERROR] {e}")
