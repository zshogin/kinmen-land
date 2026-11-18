import csv
import glob
import os
from collections import defaultdict

M2_TO_PING = 0.3025

def safe_float(val):
    try:
        return float(val)
    except:
        return None

def safe_int(val):
    try:
        return int(float(val))
    except:
        return None

files = [
    ("最新期別(115年10月)", "kinmen_data/w_lvr_land_a.csv"),
    ("115年第2季", "kinmen_data/seasons/w_lvr_land_a_115S2.csv"),
    ("115年第1季", "kinmen_data/seasons/w_lvr_land_a_115S1.csv"),
    ("114年第4季", "kinmen_data/seasons/w_lvr_land_a_114S4.csv")
]

all_records = []

for period_label, fpath in files:
    if not os.path.exists(fpath):
        continue
    with open(fpath, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        header = next(reader)
        next(reader) # skip en header
        for r in reader:
            if not r or len(r) < 23:
                continue
            all_records.append({
                "period": period_label,
                "town": r[0],
                "target": r[1],
                "addr": r[2],
                "land_area_m2": safe_float(r[3]),
                "zoning": r[4] or r[5],
                "date": r[7],
                "floor": r[9],
                "total_floors": r[10],
                "b_type": r[11],
                "usage": r[12],
                "build_area_m2": safe_float(r[15]),
                "rooms": r[16],
                "living": r[17],
                "bath": r[18],
                "total_price": safe_int(r[21]),
                "unit_price_m2": safe_float(r[22]),
                "note": r[26] if len(r) > 26 else ""
            })

print(f"Total collected transaction records: {len(all_records)}")

# 1. Summary by period & target
period_target_cnt = defaultdict(lambda: defaultdict(int))
for r in all_records:
    target_group = "房地(含建物)" if "房地" in r["target"] or "建物" in r["target"] else ("土地" if r["target"] == "土地" else "車位/其他")
    period_target_cnt[r["period"]][target_group] += 1

print("\n--- 依季度與標的分佈 ---")
for p, targets in period_target_cnt.items():
    print(f"{p}: {dict(targets)}")

# 2. Summary by Township
town_stats = defaultdict(lambda: {"cnt": 0, "house_cnt": 0, "land_cnt": 0, "total_vol": 0, "house_unit_prices": [], "land_unit_prices": []})
for r in all_records:
    t = r["town"]
    town_stats[t]["cnt"] += 1
    if r["total_price"]:
        town_stats[t]["total_vol"] += r["total_price"]
    
    unit_m2 = r["unit_price_m2"]
    if unit_m2 and unit_m2 > 0:
        unit_ping = unit_m2 / M2_TO_PING
        if "房地" in r["target"] or "建物" in r["target"]:
            town_stats[t]["house_cnt"] += 1
            town_stats[t]["house_unit_prices"].append(unit_ping)
        elif r["target"] == "土地":
            town_stats[t]["land_cnt"] += 1
            town_stats[t]["land_unit_prices"].append(unit_ping)

print("\n--- 各鄉鎮統計 ---")
for t, st in sorted(town_stats.items(), key=lambda x: x[1]["cnt"], reverse=True):
    avg_h = sum(st["house_unit_prices"])/len(st["house_unit_prices"]) if st["house_unit_prices"] else 0
    avg_l = sum(st["land_unit_prices"])/len(st["land_unit_prices"]) if st["land_unit_prices"] else 0
    print(f"[{t}] 總件數: {st['cnt']} (房地: {st['house_cnt']}, 土地: {st['land_cnt']}), 成交總額: {st['total_vol']/100000000:.2f}億元, 住宅均價: {avg_h/10000:.1f}萬/坪, 土地均價: {avg_l/10000:.1f}萬/坪")

# 3. Building type breakdown
btype_stats = defaultdict(list)
for r in all_records:
    if ("房地" in r["target"] or "建物" in r["target"]) and r["unit_price_m2"] and r["unit_price_m2"] > 0:
        btype = r["b_type"]
        unit_ping = r["unit_price_m2"] / M2_TO_PING
        btype_stats[btype].append((r["total_price"], unit_ping))

print("\n--- 建物型態行情統計 ---")
for bt, vals in sorted(btype_stats.items(), key=lambda x: len(x[1]), reverse=True):
    avg_ping = sum(v[1] for v in vals)/len(vals)
    avg_total = sum(v[0] for v in vals)/len(vals)
    print(f"{bt}: {len(vals)}件, 平均總價: {avg_total/10000:.0f}萬元, 平均單價: {avg_ping/10000:.1f}萬元/坪")

# 4. Check presale data if any
presale_files = glob.glob("kinmen_data/**/w_lvr_land_b*.csv", recursive=True)
print(f"\n--- 預售屋檔案 ({len(presale_files)}) ---")
presale_records = []
for pf in presale_files:
    with open(pf, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        next(reader) # header
        next(reader) # en
        for r in reader:
            if r and len(r) > 22:
                presale_records.append(r)
print(f"預售屋總件數: {len(presale_records)}")
for r in presale_records[:5]:
    print(f"預售: [{r[0]}] {r[7]} | {r[2]} | 總價: {int(float(r[21])):,}元 | 單價: {float(r[22])/M2_TO_PING/10000:.1f}萬/坪")
