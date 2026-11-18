import urllib.request
import ssl
import json

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# Let's check section names from Kinmen LAND_PUB_NEW
url = "https://mapcloud.kinmen.gov.tw/arcgiswa/rest/services/Public/LAND_PUB_NEW/MapServer?f=pjson"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req, context=ctx) as resp:
    data = json.loads(resp.read().decode('utf-8'))
    layers = data.get('layers', [])
    print(f"LAND_PUB_NEW has {len(layers)} section layers. Sample:")
    for l in layers[:15]:
        print(f"  ID {l['id']}: {l['name']}")
