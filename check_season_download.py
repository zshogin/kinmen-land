import urllib.request
import ssl
import zipfile
import io

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

for s in ['115S3', '115S2', '115S1', '114S4']:
    url = f"https://plvr.land.moi.gov.tw/DownloadHistory?type=season&fileName={s}"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
            data = resp.read()
            print(f"Season {s}: HTTP {resp.status}, size {len(data)} bytes")
            if len(data) > 1000:
                try:
                    with zipfile.ZipFile(io.BytesIO(data)) as zf:
                        w_files = [n for n in zf.namelist() if 'w_lvr' in n.lower()]
                        print(f"  Kinmen files in {s}: {w_files}")
                        if 'w_lvr_land_a.csv' in zf.namelist():
                            lines = zf.read('w_lvr_land_a.csv').decode('utf-8-sig', errors='replace').splitlines()
                            print(f"  w_lvr_land_a.csv rows: {len(lines)}")
                except Exception as ze:
                    print(f"  Not a valid zip or error: {ze}")
    except Exception as e:
        print(f"Error for {s}: {e}")
