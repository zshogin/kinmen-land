import urllib.request
import json

base = "http://localhost:8080"

# 1. Health
with urllib.request.urlopen(f"{base}/api/v1/health") as resp:
    print("Health:", resp.read().decode())

# 2. Stats
with urllib.request.urlopen(f"{base}/api/v1/real-estate/stats") as resp:
    data = json.loads(resp.read().decode())
    print("\nStats - Town Rankings:")
    for t in data["town_ranking"]:
        print(f"  {t['town']}: {t['count']}件, 均價 {t['avg_unit_ping']}萬/坪")

# 3. Identify
req_data = json.dumps({"lat": 24.455, "lon": 118.330}).encode('utf-8')
req = urllib.request.Request(f"{base}/api/v1/gis/identify", data=req_data, headers={"Content-Type": "application/json"})
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode())
    print("\nIdentify (24.455, 118.330):")
    sp = data["spatial"]
    print("  Town:", sp["town"])
    print("  Zoning:", sp["zoning"]["name"])
    print("  Coverage Limit:", sp["zoning"]["building_coverage_limit_percent"], "%")
    print("  FAR Limit:", sp["zoning"]["floor_area_ratio_percent"], "%")
    print("  Nearby cases found:", len(data["nearby_transactions"]))

# 4. Capacity Calculation
cap_data = json.dumps({"land_area_ping": 120, "zoning_name": "自然村專用區"}).encode('utf-8')
req_cap = urllib.request.Request(f"{base}/api/v1/gis/calculate-capacity", data=cap_data, headers={"Content-Type": "application/json"})
with urllib.request.urlopen(req_cap) as resp:
    cap = json.loads(resp.read().decode())
    print("\nCapacity (120坪 自然村專用區):")
    print(f"  最大建築基底: {cap['max_building_footprint_ping']}坪 (建蔽率 {cap['coverage_percent']}%)")
    print(f"  最大總樓地板: {cap['max_total_floor_area_ping']}坪 (容積率 {cap['far_percent']}%)")
    print(f"  建議樓層: {cap['suggested_floors']}層")
