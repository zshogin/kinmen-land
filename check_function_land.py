import urllib.request
import ssl
import json

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

for s in ['KIM_GIS/Kim_FunctionLand', 'Public/URBAN_Pub_Big', 'Public/URBAN_Pub_Small']:
    url = f"https://mapcloud.kinmen.gov.tw/arcgiswa/rest/services/{s}/MapServer?f=pjson"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        print(f"=== {s} ===")
        for l in data.get('layers', []):
            print(f"  Layer {l['id']}: {l['name']}")
