import urllib.request
import ssl
import json

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

url = "https://mapcloud.kinmen.gov.tw/arcgiswa/rest/services/Public/URBAN_Pub_Big/MapServer/0/query?where=1%3D1&outFields=uplan,KIND,Building_C,Floor_Area&returnGeometry=false&resultRecordCount=15&f=pjson"
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
    data = json.loads(resp.read().decode('utf-8'))
    print("Sample records from URBAN_Pub_Big:")
    for feat in data.get('features', []):
        print(" ", feat.get('attributes'))
