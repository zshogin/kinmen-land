import urllib.request
import ssl
import json

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

for folder in ['KIM_GIS', 'Public', 'SystemOnline']:
    url = f"https://mapcloud.kinmen.gov.tw/arcgiswa/rest/services/{folder}?f=pjson"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            print(f"=== Folder: {folder} ===")
            for s in data.get("services", []):
                print(f"  - {s.get('name')} ({s.get('type')})")
    except Exception as e:
        print(f"Error {folder}: {e}")
