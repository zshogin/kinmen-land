import urllib.request
import ssl
import json

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

url = "https://gismap.kmnp.gov.tw/arcgis/rest/services?f=pjson"
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
    data = json.loads(resp.read().decode('utf-8'))
    print("KMNP ArcGIS Folders:", data.get("folders"))
    print("KMNP Root Services:")
    for s in data.get("services", []):
        print(f"  - {s.get('name')} ({s.get('type')})")

for folder in data.get("folders", []):
    f_url = f"https://gismap.kmnp.gov.tw/arcgis/rest/services/{folder}?f=pjson"
    req_f = urllib.request.Request(f_url, headers=headers)
    try:
        with urllib.request.urlopen(req_f, context=ctx, timeout=10) as resp_f:
            f_data = json.loads(resp_f.read().decode('utf-8'))
            print(f"\nFolder: {folder}")
            for s in f_data.get("services", []):
                print(f"  - {s.get('name')} ({s.get('type')})")
    except Exception as e:
        print(f"Error {folder}: {e}")
