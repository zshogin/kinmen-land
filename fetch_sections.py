import urllib.request
import ssl
import xml.etree.ElementTree as ET
import json

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

towns = [
    ("W01", "金湖鎮"),
    ("W02", "金沙鎮"),
    ("W03", "金城鎮"),
    ("W04", "金寧鄉"),
    ("W05", "烈嶼鄉")
]

sections_data = {}

for code, name in towns:
    url = f"https://api.nlsc.gov.tw/other/ListLandSection/W/{code}"
    print(f"Fetching sections for {name} ({code})...")
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
            root = ET.fromstring(resp.read().decode('utf-8'))
            sect_list = []
            for item in root.findall('sectItem'):
                sc = item.find('sectcode')
                sn = item.find('sectstr')
                if sc is not None and sn is not None and sc.text and sn.text:
                    sect_list.append({"code": sc.text, "name": sn.text})
            sections_data[name] = sect_list
            print(f"  Got {len(sect_list)} sections for {name}")
    except Exception as e:
        print(f"  Error {name}: {e}")

with open("kinmen_sections.json", "w", encoding="utf-8") as f:
    json.dump(sections_data, f, ensure_ascii=False, indent=2)

print("Saved kinmen_sections.json")
