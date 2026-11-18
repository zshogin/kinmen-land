import urllib.request
import ssl
import zipfile
import io
import os
import csv

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

os.makedirs("kinmen_data/seasons", exist_ok=True)

seasons = ['115S2', '115S1', '114S4']

for s in seasons:
    out_file = f"kinmen_data/seasons/w_lvr_land_a_{s}.csv"
    if os.path.exists(out_file):
        continue
    url = f"https://plvr.land.moi.gov.tw/DownloadHistory?type=season&fileName={s}"
    print(f"Downloading {s}...")
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, context=ctx, timeout=60) as resp:
            data = resp.read()
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                if 'w_lvr_land_a.csv' in zf.namelist():
                    with open(out_file, "wb") as f_out:
                        f_out.write(zf.read('w_lvr_land_a.csv'))
                    print(f"Extracted {s} w_lvr_land_a.csv ({os.path.getsize(out_file)} bytes)")
                if 'w_lvr_land_b.csv' in zf.namelist():
                    with open(f"kinmen_data/seasons/w_lvr_land_b_{s}.csv", "wb") as f_out:
                        f_out.write(zf.read('w_lvr_land_b.csv'))
    except Exception as e:
        print(f"Failed {s}: {e}")
