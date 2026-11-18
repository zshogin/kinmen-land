import urllib.request
import ssl
import json

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

services_to_check = [
    'Public/LAND_PUB_NEW',
    'Public/URBAN_Pub_Big',
    'Public/URBAN_Pub_Small',
    'Public/door_Pub',
    'Public/Land_pri_PUB'
]

for s in services_to_check:
    url = f"https://mapcloud.kinmen.gov.tw/arcgiswa/rest/services/{s}/MapServer?f=pjson"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            print(f"================== {s} ==================")
            print("Description:", data.get("serviceDescription", "")[:100])
            print("Spatial Reference:", data.get("spatialReference"))
            layers = data.get("layers", [])
            print(f"Layers count: {len(layers)}")
            for l in layers:
                print(f"  Layer ID {l.get('id')}: {l.get('name')} (parent: {l.get('parentLayerId')})")
    except Exception as e:
        print(f"Error {s}: {e}")
