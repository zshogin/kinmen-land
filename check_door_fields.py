import urllib.request
import ssl
import json

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

url = "https://mapcloud.kinmen.gov.tw/arcgiswa/rest/services/Public/door_Pub/MapServer/0?f=pjson"
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
    data = json.loads(resp.read().decode('utf-8'))
    print("door_Pub fields:")
    for f in data.get('fields', []):
        print(f"  {f['name']} ({f['type']}) : {f.get('alias')}")
