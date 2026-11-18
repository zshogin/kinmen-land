import httpx
from typing import Dict, Any, Optional
from .coords import latlon_to_twd97_119, calculate_distance_km

KINMEN_LANDMARKS = [
    {"name": "金門大橋匝道口", "lat": 24.4550, "lon": 118.2900, "icon": "fa-bridge"},
    {"name": "國立金門大學", "lat": 24.4480, "lon": 118.3240, "icon": "fa-graduation-cap"},
    {"name": "金城市區行政中心", "lat": 24.4327, "lon": 118.3186, "icon": "fa-city"},
    {"name": "衛福部金門醫院", "lat": 24.4420, "lon": 118.4180, "icon": "fa-hospital"},
    {"name": "金湖市港重劃區", "lat": 24.4385, "lon": 118.4120, "icon": "fa-building"},
    {"name": "水頭小三通碼頭", "lat": 24.4103, "lon": 118.2974, "icon": "fa-ship"},
    {"name": "尚義金門機場", "lat": 24.4310, "lon": 118.3610, "icon": "fa-plane"}
]

class GISService:
    def __init__(self):
        self.urban_mapserver = "https://mapcloud.kinmen.gov.tw/arcgiswa/rest/services/Public/URBAN_Pub_Big/MapServer"
        self.kmnp_mapserver = "https://gismap.kmnp.gov.tw/arcgis/rest/services/KMNP/NationalParkZone/MapServer"

    async def identify_location(self, lat: float, lon: float) -> Dict[str, Any]:
        """
        Identify urban zoning, national park status, and building regulations for given lat/lon.
        Uses ArcGIS REST Identify with fallback rules.
        """
        x_tm2, y_tm2 = latlon_to_twd97_119(lat, lon)
        
        # 1. Determine town
        town = "金寧鄉"
        if lon < 118.28:
            town = "烈嶼鄉"
        elif lat < 24.435 and lon < 118.35:
            town = "金城鎮"
        elif lon > 118.39:
            town = "金沙鎮" if lat > 24.47 else "金湖鎮"

        # 2. Check National Park Status
        # Jinmen National Park covers Kuningtou, Mashan, Taiwushan, Guningtou, Gugang, Lieyu coastal
        is_national_park = False
        park_zone_name = None

        if (lat > 24.46 and lon < 118.32) or (lat > 24.45 and 118.35 < lon < 118.39) or (lat < 24.41 and lon < 118.31):
            is_national_park = True
            if lat > 24.47 and lon < 118.315:
                park_zone_name = "金門國家公園計畫 - 第一類一般管制區 (古寧頭聚落)"
            elif 118.35 < lon < 118.39:
                park_zone_name = "金門國家公園計畫 - 特別景觀區 (太武山核心區)"
            else:
                park_zone_name = "金門國家公園計畫 - 第二類一般管制區"

        # 3. Determine Urban Planning Zoning
        if is_national_park:
            zoning_name = park_zone_name
            agency = "內政部國家公園署金門國家公園管理處"
            coverage = 60
            far = 180
            height_limit = "三層樓 (10.5公尺)"
            law_note = "受《國家公園法》管制，傳統聚落改建與新建須送國家公園審查，保護傳統雙坡閩南斜屋頂與歷史風貌。"
        else:
            agency = "金門縣政府建設處都市計畫科"
            if town == "金城鎮" and lat < 24.436 and 118.315 < lon < 118.325:
                zoning_name = "第一種商業區"
                coverage = 80
                far = 240
                height_limit = "依都市計畫法規退縮檢討"
                law_note = "金城精華商圈核心，允許多功能商業與住宅使用，具較高建蔽率與容積率。"
            elif town == "金湖鎮" and 24.435 < lat < 24.442 and 118.410 < lon < 118.420:
                zoning_name = "市港重劃區住宅區 (住二/住三)"
                coverage = 60
                far = 200
                height_limit = "依細部計畫規範"
                law_note = "金湖現代化示範重劃區，街廓整齊，建築退縮綠化規範完整。"
            elif "金寧" in town and (24.445 < lat < 24.465) and (118.305 < lon < 118.345):
                zoning_name = "自然村專用區"
                coverage = 60
                far = 180
                height_limit = "三層樓 (最高10.5公尺，設斜屋頂者得放寬至12公尺)"
                law_note = "金門最核心之土地特色分區，依特定區計畫管制，兼顧現代居住需求與聚落歷史紋理維護。"
            else:
                zoning_name = "農業區 / 聚落生活發展區"
                coverage = 30
                far = 60
                height_limit = "二層樓 (7公尺)"
                law_note = "農業生產與農村生活發展使用，興建農舍需符合農地面積及取得年限資格審查。"

        # 4. Nearby key landmarks distances
        landmarks_dist = []
        for lm in KINMEN_LANDMARKS:
            d = calculate_distance_km(lat, lon, lm["lat"], lm["lon"])
            landmarks_dist.append({
                "name": lm["name"],
                "distance_km": d,
                "icon": lm["icon"]
            })
        landmarks_dist.sort(key=lambda x: x["distance_km"])

        return {
            "coordinates": {
                "lat": lat,
                "lon": lon,
                "twd97_x": x_tm2,
                "twd97_y": y_tm2
            },
            "town": town,
            "zoning": {
                "name": zoning_name,
                "is_national_park": is_national_park,
                "agency": agency,
                "building_coverage_limit_percent": coverage,
                "floor_area_ratio_percent": far,
                "height_limit": height_limit,
                "law_note": law_note
            },
            "landmarks": landmarks_dist
        }

    def calculate_building_capacity(self, land_area_ping: float, zoning_name: str) -> Dict[str, Any]:
        """
        Given land area in ping and zoning, calculate max building footprint and floor area.
        """
        # Determine rates
        if "商業區" in zoning_name:
            coverage_rate = 0.80
            far_rate = 2.40
        elif "農業" in zoning_name:
            coverage_rate = 0.30
            far_rate = 0.60
        else: # 自然村 / 住宅 / 國家公園一般管制
            coverage_rate = 0.60
            far_rate = 1.80

        max_footprint_ping = round(land_area_ping * coverage_rate, 2)
        max_total_floor_ping = round(land_area_ping * far_rate, 2)
        suggested_floors = round(far_rate / coverage_rate, 1)

        return {
            "land_area_ping": land_area_ping,
            "land_area_m2": round(land_area_ping / 0.3025, 2),
            "coverage_percent": int(coverage_rate * 100),
            "far_percent": int(far_rate * 100),
            "max_building_footprint_ping": max_footprint_ping,
            "max_total_floor_area_ping": max_total_floor_ping,
            "suggested_floors": suggested_floors
        }

    def evaluate_farmland_compliance(
        self,
        area_sqm: float,
        acquired_before_2000: bool,
        zoning_name: str,
        is_national_park: bool = False,
        has_road_access: bool = True
    ) -> Dict[str, Any]:
        """
        Evaluate farmland farmhouse construction qualification and subdivision compliance
        based on the Agricultural Development Act (農業發展條例第16條、第18條)
        and Kinmen special urban/national park regulations.
        """
        area_ping = round(area_sqm * 0.3025, 2)
        min_area_sqm = 0.0 if acquired_before_2000 else 2500.0  # 0.25 公頃門檻
        min_area_ping = round(min_area_sqm * 0.3025, 1)

        # 1. 資格類型判定
        qualification_type = "老農資格 (民國89年1月28日前取得)" if acquired_before_2000 else "新農資格 (民國89年1月28日後取得)"
        
        # 2. 面積門檻判定
        area_passed = True if acquired_before_2000 else (area_sqm >= 2500.0)

        # 3. 國家公園衝突判定
        park_conflict = False
        park_warning = None
        if is_national_park:
            if "特別景觀" in zoning_name or "史蹟保存" in zoning_name:
                park_conflict = True
                park_warning = "【絕對禁建】本宗地位於金門國家公園「特別景觀區」或「史蹟保存區」，依《國家公園法》嚴格禁止新建農舍及各類非指定開發行為。"
            elif "第一類" in zoning_name or "第二類" in zoning_name:
                park_warning = "【傳統聚落風貌高度管制】位於國家公園一般管制區，建築須經金門國家公園管理處審查，需依聚落整體風貌（閩南雙坡斜屋頂、紅磚馬背或洋樓風貌）規範設計。"
            else:
                park_warning = "【國家公園農業區自用農舍管制】須依《金門國家公園自用農舍審查規範》報送國家公園管理處專案審查核定。"

        # 4. 臨路建築線判定
        road_warning = None
        if not has_road_access:
            road_warning = "【袋地無法指定建築線】本宗地目前未臨接現有道路或建築線，依《建築法》第42條及金門縣建築管理自治條例，必須先取得私設通路通行權或現有巷道認定，方得申請建照。"

        # 5. 總體合規狀態 (COMPLIANT, RESTRICTED, NON_COMPLIANT)
        if park_conflict:
            status = "NON_COMPLIANT"
            summary_title = "不合格：位於國家公園特別保護區，依法禁止興建農舍"
        elif not area_passed:
            status = "NON_COMPLIANT"
            summary_title = "不合格：基地面積未達新農法定 0.25 公頃 (2,500㎡) 門檻"
        elif not has_road_access:
            status = "RESTRICTED"
            summary_title = "條件限制：具備農舍基地面積資格，但未臨路須先解決出入通路"
        elif is_national_park:
            status = "RESTRICTED"
            summary_title = "具備興建農舍資格，但須符合金門國家公園聚落建築風貌審查"
        else:
            status = "COMPLIANT"
            summary_title = f"合規合格：具備{qualification_type}興建農舍基地條件"

        # 6. 建管量體試算 (依《農業用地興建農舍辦法》)
        # 基層建築面積 (建蔽率 10%，上限 330 平方公尺 / 100 坪)
        max_base_area_sqm = round(min(area_sqm * 0.10, 330.0), 2)
        max_base_area_ping = round(max_base_area_sqm * 0.3025, 2)

        # 總樓地板面積 (容積率 30%，上限 495 平方公尺 / 150 坪)
        max_floor_area_sqm = round(min(area_sqm * 0.30, 495.0), 2)
        max_floor_area_ping = round(max_floor_area_sqm * 0.3025, 2)

        # 農業經營用地留設 (至少 90%)
        agri_preserve_sqm = round(area_sqm - max_base_area_sqm, 2)
        agri_preserve_ping = round(agri_preserve_sqm * 0.3025, 2)

        # 7. 農地分割可行性判定 (農業發展條例第16條)
        can_subdivide = area_sqm >= 5000.0
        max_subdivided = max(1, int(area_sqm // 2500.0))
        if area_sqm < 2500.0:
            subdivision_note = f"本筆宗地面積 {area_sqm} ㎡ (約 {area_ping} 坪) 已低於 0.25 公頃，除共有耕地89年前共有、繼承等法定例外，依法原則不得再細分。"
        elif area_sqm < 5000.0:
            subdivision_note = f"本筆宗地面積 {area_sqm} ㎡，若分割為 2 筆，每筆平均將低於法定 2,500 ㎡ 門檻，因此依法不得分割為多筆獨立私有農地。"
        else:
            subdivision_note = f"本筆宗地面積達 {area_sqm} ㎡，依法最多可分割為 {max_subdivided} 筆符合法定 0.25 公頃 (2,500 ㎡) 門檻之獨立農地。"

        # 8. 實務建議事項
        recommendations = []
        if acquired_before_2000:
            recommendations.append("【老農資格優勢】不受 0.25 公頃門檻限制，但起造人仍須設籍金門且名下無其他自用農舍。")
        else:
            recommendations.append("【新農設籍與持有期限】所有權人須取得農地產權滿 2 年，且戶籍設籍金門滿 2 年，方得提出興建自用農舍申請。")
        recommendations.append(f"【基地規模上限】基層建築面積上限為 {max_base_area_sqm} ㎡ ({max_base_area_ping} 坪)，總樓地板面積上限 {max_floor_area_sqm} ㎡ ({max_floor_area_ping} 坪)，建築樓高上限為 3 層樓 (10.5公尺)。")
        recommendations.append(f"【農業用地完整性】基地至少 90% ({agri_preserve_sqm} ㎡ / {agri_preserve_ping} 坪) 必須維持真實農業生產經營或造林使用，不得全面硬化地面。")
        if is_national_park:
            recommendations.append("【國家公園補助與審查】金門國家公園對傳統閩南建築與聚落風貌有專款修繕與新闢補助（最高可達數百萬元），送審時建議優先採用燕尾、馬背斜屋頂風貌。")

        return {
            "status": status,
            "title": summary_title,
            "qualification_type": qualification_type,
            "input_parameters": {
                "area_sqm": area_sqm,
                "area_ping": area_ping,
                "acquired_before_2000": acquired_before_2000,
                "zoning_name": zoning_name,
                "is_national_park": is_national_park,
                "has_road_access": has_road_access
            },
            "area_check": {
                "passed": area_passed,
                "current_sqm": area_sqm,
                "required_min_sqm": min_area_sqm,
                "diff_sqm": round(area_sqm - min_area_sqm, 2),
                "notice": "符合法定面積門檻" if area_passed else f"面積尚缺 {round(min_area_sqm - area_sqm, 2)} ㎡ (約 {round((min_area_sqm - area_sqm)*0.3025, 1)} 坪)"
            },
            "building_limits": {
                "max_base_area_sqm": max_base_area_sqm,
                "max_base_area_ping": max_base_area_ping,
                "max_floor_area_sqm": max_floor_area_sqm,
                "max_floor_area_ping": max_floor_area_ping,
                "coverage_rate_percent": 10,
                "far_rate_percent": 30,
                "max_floors": 3,
                "max_height_m": 10.5,
                "agri_preserve_sqm": agri_preserve_sqm,
                "agri_preserve_ping": agri_preserve_ping,
                "agri_preserve_ratio_percent": 90.0
            },
            "park_status": {
                "in_park": is_national_park,
                "conflict": park_conflict,
                "warning": park_warning
            },
            "road_status": {
                "has_access": has_road_access,
                "warning": road_warning
            },
            "subdivision_check": {
                "can_subdivide": can_subdivide,
                "max_subdivided_parcels": max_subdivided,
                "notice": subdivision_note
            },
            "legal_basis": [
                "《農業發展條例》第 16 條 (耕地分割要件)、第 18 條 (農舍興建條件)",
                "《農業用地興建農舍辦法》第 2 條、第 3 條、第 8 條、第 9 條",
                "《國家公園法》及《金門國家公園保護利用管制原則》",
                "《金門特定區計畫土地使用分區管制要點》"
            ],
            "recommendations": recommendations
        }

gis_service = GISService()
