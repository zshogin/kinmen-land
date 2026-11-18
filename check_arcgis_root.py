import urllib.request
import ssl
import json

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = "https://mapcloud.kinmen.gov.tw/arcgiswa/rest/services?f=pjson"
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

req = urllib.request.Request(url, headers=headers)
try:
    with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        print("ArcGIS Services Root:")
        print("  Folders:", data.get("folders"))
        print("  Services:")
        for s in data.get("services", []):
            print(f"    - {s.get('name')} ({s.get('type')})")
except Exception as e:
    print("Error:", e)
