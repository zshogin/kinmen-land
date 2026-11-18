import csv
import glob

M2_TO_PING = 0.3025

# Find highest house unit price, highest house total price, and top areas
houses = []
for p in glob.glob("kinmen_data/**/w_lvr_land_a*.csv", recursive=True):
    with open(p, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        next(reader)
        next(reader)
        for r in reader:
            if not r or len(r) < 23:
                continue
            target = r[1]
            if "房地" in target or "建物" in target:
                try:
                    price = int(float(r[21]))
                    unit_m2 = float(r[22])
                    if unit_m2 > 0 and price > 0:
                        unit_ping = unit_m2 / M2_TO_PING
                        houses.append({
                            "town": r[0],
                            "date": r[7],
                            "addr": r[2],
                            "price": price,
                            "unit_ping": unit_ping,
                            "b_type": r[11],
                            "area_ping": float(r[15]) * M2_TO_PING if r[15] else 0,
                            "note": r[26] if len(r) > 26 else ""
                        })
                except:
                    pass

houses_by_unit = sorted(houses, key=lambda x: x["unit_ping"], reverse=True)
houses_by_price = sorted(houses, key=lambda x: x["price"], reverse=True)

print("Top 5 最高單價房屋交易:")
for h in houses_by_unit[:5]:
    print(f"[{h['town']}] {h['date']} | {h['addr']} | 單價: {h['unit_ping']/10000:.1f}萬/坪 | 總價: {h['price']/10000:.0f}萬 | {h['b_type']} | 面積: {h['area_ping']:.1f}坪 | 備註: {h['note']}")

print("\nTop 5 最高總價房屋交易:")
for h in houses_by_price[:5]:
    print(f"[{h['town']}] {h['date']} | {h['addr']} | 總價: {h['price']/10000:.0f}萬 | 單價: {h['unit_ping']/10000:.1f}萬/坪 | {h['b_type']} | 面積: {h['area_ping']:.1f}坪")
