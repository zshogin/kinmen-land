import urllib.request
import ssl
import xml.etree.ElementTree as ET

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = "https://gis.sinica.edu.tw/kinmen/wmts?SERVICE=WMTS&REQUEST=GetCapabilities"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req, context=ctx, timeout=8) as resp:
    xml_data = resp.read().decode('utf-8')
    root = ET.fromstring(xml_data)

for layer in root.iter('{http://www.opengis.net/wmts/1.0}Layer'):
    ident = layer.find('{http://www.opengis.net/ows/1.1}Identifier').text
    if '1958' in ident or '1966' in ident:
        print(f"\n--- Layer: {ident} ---")
        for fmt in layer.findall('{http://www.opengis.net/wmts/1.0}Format'):
            print("  Format:", fmt.text)
        for tms in layer.findall('{http://www.opengis.net/wmts/1.0}TileMatrixSetLink'):
            print("  TileMatrixSet:", tms.find('{http://www.opengis.net/wmts/1.0}TileMatrixSet').text)
        for res in layer.findall('{http://www.opengis.net/wmts/1.0}ResourceURL'):
            print("  ResourceURL:", res.attrib)
