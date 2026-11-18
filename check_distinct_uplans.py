import urllib.request
import ssl
import json

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

# Search distinct values of uplan in URBAN_Pub_Big
url = "https://mapcloud.kinmen.gov.tw/arcgiswa/rest/services/Public/URBAN_Pub_Big/MapServer/0/query?where=1%3D1&outFields=uplan&returnDistinctValues=true&returnGeometry=false&f=pjson"
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
    data = json.loads(resp.read().decode('utf-8'))
    uplans = [f['attributes']['uplan'] for f in data.get('features', []) if f.get('attributes') and f['attributes'].get('uplan')]
    print("Distinct uplans in URBAN_Pub_Big (total %d):" % len(uplans))
    for u in sorted(uplans):
        print("  -", u)
