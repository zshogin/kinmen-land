import urllib.request
import ssl
import zipfile
import io

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = "https://plvr.land.moi.gov.tw/Download?type=zip&fileName=lvr_landcsv.zip"
print(f"Fetching {url}...")
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
        data = resp.read()
        print(f"Downloaded {len(data)} bytes. HTTP status: {resp.status}")
        with open("lvr_landcsv_current.zip", "wb") as f:
            f.write(data)
        
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            namelist = zf.namelist()
            print(f"Total files in zip: {len(namelist)}")
            w_files = [n for n in namelist if 'w_lvr' in n.lower()]
            print("Kinmen files (W):", w_files)
except Exception as e:
    print("Error:", e)
