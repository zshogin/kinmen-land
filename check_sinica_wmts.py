import urllib.request
import ssl
import xml.etree.ElementTree as ET

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = "https://gis.sinica.edu.tw/kinmen/wmts?SERVICE=WMTS&REQUEST=GetCapabilities"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req, context=ctx, timeout=8) as resp:
        xml_data = resp.read().decode('utf-8')
        print(f"WMTS Capabilities fetched, length: {len(xml_data)}")
        root = ET.fromstring(xml_data)
        # Find Layers
        # Extract Layer identifiers and titles
        for elem in root.iter():
            if elem.tag.endswith('Layer'):
                ident = elem.find('{http://www.opengis.net/ows/1.1}Identifier')
                title = elem.find('{http://www.opengis.net/ows/1.1}Title')
                if ident is not None:
                    print(f"Layer: ID={ident.text}, Title={title.text if title is not None else ''}")
except Exception as e:
    print("Error:", e)
