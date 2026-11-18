import urllib.request
import ssl
import json

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

urls = {
    "NLSC_WMTS_Capabilities": "https://wmts.nlsc.gov.tw/wmts?SERVICE=WMTS&REQUEST=GetCapabilities",
    "NLSC_WMS_Capabilities": "https://wms.nlsc.gov.tw/wms?SERVICE=WMS&REQUEST=GetCapabilities",
    "Kinmen_Urban_GIS": "https://urban.kinmen.gov.tw/kmgis/publicweb/index.aspx",
    "Kinmen_NP_GIS": "https://gismap.kmnp.gov.tw/kmNpuse/Login.aspx",
    "TGOS_LUZ_WMS": "https://luz.tgos.tw/luz_wms/service.svc/get?SERVICE=WMS&REQUEST=GetCapabilities"
}

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

for name, url in urls.items():
    print(f"Testing {name}...")
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=8) as resp:
            content_sample = resp.read(1024).decode('utf-8', errors='ignore')
            print(f"  [SUCCESS] HTTP {resp.status}, preview: {content_sample[:120].strip()}")
    except Exception as e:
        print(f"  [FAILED] {e}")
