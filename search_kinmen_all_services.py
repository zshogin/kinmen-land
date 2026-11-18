import urllib.request
import ssl
import json

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

root_url = "https://mapcloud.kinmen.gov.tw/arcgiswa/rest/services?f=pjson"
req = urllib.request.Request(root_url, headers=headers)
with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
    root = json.loads(resp.read().decode('utf-8'))

all_services = [s['name'] for s in root.get('services', [])]
for folder in root.get('folders', []):
    f_url = f"https://mapcloud.kinmen.gov.tw/arcgiswa/rest/services/{folder}?f=pjson"
    req_f = urllib.request.Request(f_url, headers=headers)
    try:
        with urllib.request.urlopen(req_f, context=ctx, timeout=10) as resp_f:
            f_data = json.loads(resp_f.read().decode('utf-8'))
            for s in f_data.get('services', []):
                all_services.append(s['name'])
    except Exception as e:
        print(f"Error fetching folder {folder}: {e}")

print(f"Total services on mapcloud.kinmen.gov.tw: {len(all_services)}")
for s in sorted(all_services):
    print(" ", s)
