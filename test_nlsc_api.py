import urllib.request
import ssl
import xml.etree.ElementTree as ET

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# Test NLSC Towns for Kinmen (W)
url = "https://api.nlsc.gov.tw/other/ListTown/W"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req, context=ctx, timeout=8) as resp:
        xml_data = resp.read().decode('utf-8')
        root = ET.fromstring(xml_data)
        towns = []
        for t in root.findall('townItem'):
            town_code = t.find('towncode').text
            town_name = t.find('townname').text
            towns.append((town_code, town_name))
            print(f"Town: {town_code} {town_name}")

        # Test sections for first town
        if towns:
            s_url = f"https://api.nlsc.gov.tw/other/ListLandSection/W/{towns[0][0]}"
            with urllib.request.urlopen(urllib.request.Request(s_url, headers={'User-Agent': 'Mozilla/5.0'}), context=ctx, timeout=8) as s_resp:
                s_xml = s_resp.read().decode('utf-8')
                s_root = ET.fromstring(s_xml)
                for s in s_root.findall('sectItem')[:10]:
                    print("  Section:", s.find('sectcode').text, s.find('sectname').text)
except Exception as e:
    print("Error:", e)
