import zipfile
import csv
import io

with zipfile.ZipFile("lvr_landcsv_current.zip", "r") as zf:
    for filename in ['w_lvr_land_a.csv', 'w_lvr_land_b.csv', 'w_lvr_land_c.csv']:
        if filename in zf.namelist():
            raw = zf.read(filename).decode('utf-8-sig', errors='replace')
            lines = raw.strip().splitlines()
            print(f"=== {filename} (Total lines: {len(lines)}) ===")
            reader = csv.reader(lines)
            for i, row in enumerate(reader):
                if i < 5:
                    print(f"Row {i}:", row[:10])
                else:
                    break
