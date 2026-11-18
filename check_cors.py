import urllib.request
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

urls = [
    "https://mapcloud.kinmen.gov.tw/arcgiswa/rest/services/Public/URBAN_Pub_Big/MapServer?f=pjson",
    "https://gismap.kmnp.gov.tw/arcgis/rest/services/KMNP/NationalParkZone/MapServer?f=pjson",
    "https://wmts.nlsc.gov.tw/wmts"
]

for u in urls:
    req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0', 'Origin': 'http://localhost:8000'})
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=8) as resp:
            headers = dict(resp.headers)
            cors = headers.get('access-control-allow-origin', 'NONE')
            print(f"{u[:50]}... CORS: {cors}")
    except Exception as e:
        print(f"Error {u}: {e}")
