import csv
import json
import glob
import math
import re
import os

M2_TO_PING = 0.3025

# Coordinate dictionary for Kinmen landmarks, villages, sections, and roads
# Generated from door_Pub and official points
KNOWN_LOCATIONS = {
    # Townships
    "金城鎮": (24.4327, 118.3186),
    "金寧鄉": (24.4550, 118.3300),
    "金湖鎮": (24.4420, 118.4180),
    "金沙鎮": (24.4900, 118.4100),
    "烈嶼鄉": (24.4300, 118.2450),
    
    # Major Roads / Areas
    "民生路": (24.4355, 118.3190),
    "民族路": (24.4310, 118.3175),
    "民權路": (24.4340, 118.3160),
    "伯玉路一段": (24.4361, 118.3274),
    "伯玉路二段": (24.4420, 118.3500),
    "伯玉路三段": (24.4450, 118.3750),
    "環島北路一段": (24.4400, 118.3250),
    "環島北路二段": (24.4545, 118.3652),
    "環島西路二段": (24.4630, 118.3165),
    "西海路一段": (24.4100, 118.2865),
    "西海路三段": (24.4250, 118.3050),
    "慈湖路一段": (24.4450, 118.3120),
    "慈湖路二段": (24.4560, 118.3050),
    "市港路": (24.4385, 118.4120),
    "黃海路": (24.4445, 118.4158),
    "太湖路一段": (24.4360, 118.4050),
    "太湖路二段": (24.4385, 118.4193),
    "中正路": (24.4320, 118.3180),
    "復興路": (24.4430, 118.4170),
    "光華路": (24.4380, 118.4350),

    # Villages & Sections
    "塔后": (24.4370, 118.4080),
    "中堡": (24.4588, 118.3384),
    "東堡": (24.4560, 118.3403),
    "頂堡": (24.4473, 118.3409),
    "下堡": (24.4450, 118.3380),
    "湖下": (24.4511, 118.3125),
    "頂埔下": (24.4460, 118.3150),
    "埔邊": (24.4407, 118.3172),
    "榜林": (24.4345, 118.3311),
    "后盤山": (24.4534, 118.3524),
    "后沙": (24.4568, 118.3614),
    "東洲": (24.4303, 118.3303),
    "湖南": (24.4520, 118.3275),
    "安岐": (24.4680, 118.3210),
    "北山": (24.4796, 118.3120),
    "南山": (24.4750, 118.3130),
    "古寧頭": (24.4770, 118.3125),
    "盤山": (24.4500, 118.3410),
    "長寮": (24.4530, 118.3350),
    "大橋湖峰": (24.4550, 118.3080),
    "赤岑": (24.4620, 118.3290),
    "西堡": (24.4610, 118.3380),
    "水頭": (24.4103, 118.2974),
    "小西門": (24.4120, 118.3288),
    "庵前": (24.4188, 118.3188),
    "燕南山": (24.4180, 118.3100),
    "山外": (24.4447, 118.4142),
    "成功": (24.4376, 118.3893),
    "夏興": (24.4400, 118.3940),
    "料羅": (24.4225, 118.4316),
    "新塘": (24.4214, 118.4416),
    "溪邊": (24.4430, 118.4599),
    "安民": (24.4443, 118.4320),
    "瓊林": (24.4540, 118.3730),
    "沙美": (24.4910, 118.4130),
    "陽翟": (24.4820, 118.4200),
    "西園": (24.5050, 118.4050),
    "官澳": (24.5200, 118.3980),
    "后浦頭": (24.4890, 118.4120),
    "忠孝新村": (24.4920, 118.4180),
    "雙口": (24.4401, 118.2299),
    "東林": (24.4236, 118.2483),
    "青岐": (24.4154, 118.2260),
    "西方": (24.4362, 118.2388),
    "西宅": (24.4303, 118.2468),
    "烈濱": (24.4350, 118.2300),
    "上林": (24.4279, 118.2302),
    "后頭": (24.4404, 118.2597)
}

def get_lat_lon(addr, town):
    # Search for matching keywords in KNOWN_LOCATIONS
    for loc, coords in KNOWN_LOCATIONS.items():
        if loc in addr:
            # Add small random jitter (approx 20-50m) so multiple markers on the same street don't stack directly
            import hashlib
            h = int(hashlib.md5(addr.encode('utf-8')).hexdigest()[:6], 16)
            jitter_lat = ((h % 100) - 50) * 0.00004
            jitter_lon = (((h // 100) % 100) - 50) * 0.00004
            return coords[0] + jitter_lat, coords[1] + jitter_lon
    
    # Fallback to town
    if town in KNOWN_LOCATIONS:
        coords = KNOWN_LOCATIONS[town]
        import hashlib
        h = int(hashlib.md5(addr.encode('utf-8')).hexdigest()[:6], 16)
        jitter_lat = ((h % 200) - 100) * 0.0001
        jitter_lon = (((h // 200) % 200) - 100) * 0.0001
        return coords[0] + jitter_lat, coords[1] + jitter_lon
        
    return 24.4400, 118.3300

# Collect all transactions
csv_files = glob.glob("kinmen_data/**/w_lvr_land_a*.csv", recursive=True) + glob.glob("kinmen_data/**/w_lvr_land_b*.csv", recursive=True)
all_items = []
seen_ids = set()

for fpath in csv_files:
    is_presale = "w_lvr_land_b" in fpath
    with open(fpath, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        try:
            next(reader)
            next(reader)
        except:
            continue
        for r in reader:
            if not r or len(r) < 23:
                continue
            item_id = r[27] if len(r) > 27 and r[27] else f"{r[0]}_{r[2]}_{r[7]}_{r[21]}"
            if item_id in seen_ids:
                continue
            seen_ids.add(item_id)
            
            town = r[0]
            target = r[1]
            addr = r[2]
            try:
                total_p = int(float(r[21]))
            except:
                continue
            try:
                unit_m2 = float(r[22])
                unit_ping = round(unit_m2 / M2_TO_PING / 10000, 1) if unit_m2 > 0 else 0
            except:
                unit_ping = 0

            b_type = "預售屋" if is_presale else r[11]
            if not b_type or b_type == "其他":
                b_type = "土地" if "土地" in target else ("透天厝" if "透天" in addr else "其他標的")

            area_ping = round(float(r[15]) * M2_TO_PING, 1) if r[15] and float(r[15]) > 0 else (round(float(r[3]) * M2_TO_PING, 1) if r[3] else 0)
            
            lat, lon = get_lat_lon(addr, town)

            date_str = r[7] # e.g. 1151003 -> 115/10/03
            if len(date_str) == 7:
                fmt_date = f"{date_str[:3]}/{date_str[3:5]}/{date_str[5:]}"
            else:
                fmt_date = date_str

            all_items.append({
                "id": item_id,
                "town": town,
                "target": target,
                "addr": addr,
                "date": fmt_date,
                "b_type": b_type,
                "floor": r[9],
                "total_floors": r[10],
                "rooms": r[16],
                "total_price_wan": round(total_p / 10000, 1),
                "unit_ping_wan": unit_ping,
                "area_ping": area_ping,
                "zoning": r[4] or r[5] or "一般",
                "lat": round(lat, 6),
                "lon": round(lon, 6),
                "note": r[26] if len(r) > 26 else ""
            })

print(f"Total processed real estate items: {len(all_items)}")

with open("kinmen_real_estate.json", "w", encoding="utf-8") as f:
    json.dump(all_items, f, ensure_ascii=False, indent=2)

print("Saved to kinmen_real_estate.json")
