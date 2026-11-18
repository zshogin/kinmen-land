import zipfile
import csv
import io
import os

# Let's extract Kinmen files from the downloaded current zip and inspect
with zipfile.ZipFile("lvr_landcsv_current.zip", "r") as zf:
    zf.extract("w_lvr_land_a.csv", path="kinmen_data")
    if "w_lvr_land_b.csv" in zf.namelist():
        zf.extract("w_lvr_land_b.csv", path="kinmen_data")

# Read w_lvr_land_a.csv
with open("kinmen_data/w_lvr_land_a.csv", mode="r", encoding="utf-8-sig") as f:
    reader = csv.reader(f)
    header = next(reader)
    header_en = next(reader)
    rows = list(reader)

print(f"Total current transactions in Kinmen (買賣): {len(rows)}")
print("Columns:")
for idx, col in enumerate(header):
    print(f"  {idx}: {col}")

print("\nSample records:")
for r in rows[:10]:
    # town, target, address, date, building type, total price, unit price
    town = r[0]
    target = r[1]
    addr = r[2]
    date = r[7]
    b_type = r[11]
    total_p = r[21]
    unit_p = r[22]
    print(f"[{town}] {date} | {target} | {addr} | 總價: {int(total_p):,}元 | 單價: {unit_p}元/m² | {b_type}")
