import urllib.request
import ssl
import json

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

url = "https://gismap.kmnp.gov.tw/arcgis/rest/services/KMNP/NationalParkZone/MapServer?f=pjson"
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
    data = json.loads(resp.read().decode('utf-8'))
    print("NationalParkZone service info:")
    print("  Spatial Ref:", data.get('spatialReference'))
    print("  Layers:")
    for l in data.get('layers', []):
        print(f"    - Layer ID {l['id']}: {l['name']}")
