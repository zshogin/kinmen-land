"""
Cadastral Subdivision & Merger Simulation Engine for Kinmen Land Cloud (金門地政雲 - 宗地分割與合併模擬器)
Supports:
1. Equal split (等分分割: 2, 3, 4 筆), Ratio split (比例分割), Specified Area split (指定面積分割)
2. Regulatory compliance checks:
   - 農業發展條例第16條 (耕地0.25公頃/756.25坪分割限制與法定例外)
   - 金門縣畸零地使用自治條例 (基地最小面寬3.5m與深度12m檢核)
3. Cadastral Merger simulation (相鄰宗地合併聯集、面寬擴充、容積樓地板規模效益評估)
4. Multi-system coordinate output: TWD97 Zone 119 metric coordinates and WGS84 GeoJSON
5. AutoCAD DXF export for subdivided boundaries and cut lines
"""

import math
from typing import Dict, Any, List, Tuple, Optional
from .coords import latlon_to_twd97_119, twd97_119_to_latlon

class CadastralSubdivisionEngine:

    @classmethod
    def get_base_dimensions(cls, area_sqm: float, aspect_ratio: float = 1.45) -> Tuple[float, float]:
        """Width and depth from area and aspect ratio"""
        width = math.sqrt(area_sqm / aspect_ratio)
        depth = width * aspect_ratio
        return round(width, 3), round(depth, 3)

    @classmethod
    def simulate_subdivision(
        cls,
        target_info: Dict[str, Any],
        split_mode: str = "equal",
        count: int = 2,
        ratios: Optional[List[float]] = None,
        target_sqm: Optional[float] = None,
        cut_axis: str = "width" # "width" divides road frontage, "depth" cuts front/back
    ) -> Dict[str, Any]:
        """
        Simulate cadastral subdivision for a parcel into 2 or more sub-parcels.
        """
        lat = float(target_info.get("lat", 24.4550))
        lon = float(target_info.get("lon", 118.3300))
        area_sqm = float(target_info.get("area_sqm", 330.6))
        town = target_info.get("town", "金寧鄉")
        section = target_info.get("section", "赤岑段")
        number = str(target_info.get("number", "165"))
        zoning = target_info.get("zoning", "自然村專用區")
        coverage = float(target_info.get("building_coverage", 60))
        far = float(target_info.get("floor_area_ratio", 180))
        rotation_deg = float(target_info.get("rotation_deg", 15.0))
        unit_price = float(target_info.get("unit_price_sqm", 35000.0)) # NTD per sqm

        # Aspect ratio and base size
        aspect_ratio = 1.45
        total_w, total_d = cls.get_base_dimensions(area_sqm, aspect_ratio)
        x_c, y_c = latlon_to_twd97_119(lat, lon)

        rad = math.radians(rotation_deg)
        cos_r = math.cos(rad)
        sin_r = math.sin(rad)

        def to_global_twd97(lx: float, ly: float) -> Tuple[float, float]:
            rx = lx * cos_r - ly * sin_r
            ry = lx * sin_r + ly * cos_r
            return round(x_c + rx, 3), round(y_c + ry, 3)

        # Base parcel corners (centered at 0, 0)
        half_w = total_w / 2.0
        half_d = total_d / 2.0
        base_corners_local = [
            (-half_w, -half_d),
            (half_w, -half_d),
            (half_w, half_d),
            (-half_w, half_d),
            (-half_w, -half_d)
        ]
        base_polygon_twd97 = [to_global_twd97(px, py) for px, py in base_corners_local]
        base_polygon_wgs84 = [list(twd97_119_to_latlon(gx, gy)) for gx, gy in base_polygon_twd97]

        # Determine sub-parcel slice boundaries
        slices: List[Dict[str, Any]] = []

        if split_mode == "equal":
            count = max(2, min(count, 4))
            slice_fractions = [1.0 / count] * count
        elif split_mode == "ratio":
            if not ratios or len(ratios) < 2:
                ratios = [1.0, 1.0]
            sum_r = sum(ratios)
            slice_fractions = [r / sum_r for r in ratios]
            count = len(slice_fractions)
        elif split_mode == "custom_area":
            if not target_sqm or target_sqm <= 0 or target_sqm >= area_sqm:
                target_sqm = round(area_sqm * 0.4, 1)
            frac_1 = target_sqm / area_sqm
            frac_2 = 1.0 - frac_1
            slice_fractions = [frac_1, frac_2]
            count = 2
        else:
            slice_fractions = [0.5, 0.5]
            count = 2

        sub_parcels: List[Dict[str, Any]] = []
        cut_lines_twd97: List[List[Tuple[float, float]]] = []
        cut_lines_wgs84: List[List[List[float]]] = []

        if cut_axis == "width":
            # Splitting along the width (dividing road frontage)
            cur_x = -half_w
            for i, frac in enumerate(slice_fractions):
                sub_w = total_w * frac
                next_x = cur_x + sub_w
                sub_area = area_sqm * frac
                
                # 4 corners local
                p_c1 = (cur_x, -half_d)
                p_c2 = (next_x, -half_d)
                p_c3 = (next_x, half_d)
                p_c4 = (cur_x, half_d)
                p_c5 = p_c1

                # Sub-polygon global
                sub_poly_twd97 = [to_global_twd97(px, py) for px, py in [p_c1, p_c2, p_c3, p_c4, p_c5]]
                sub_poly_wgs84 = [list(twd97_119_to_latlon(gx, gy)) for gx, gy in sub_poly_twd97]

                # Center of sub-parcel
                center_lx = (cur_x + next_x) / 2.0
                center_ly = 0.0
                c_gx, c_gy = to_global_twd97(center_lx, center_ly)
                c_lat, c_lon = twd97_119_to_latlon(c_gx, c_gy)

                # Number designation
                sub_no = f"{number}" if i == 0 else f"{number}-{i}"
                sub_label = f"A地 ({sub_no}地號)" if i == 0 else f"B地 ({sub_no}地號)" if i == 1 else f"{chr(65+i)}地 ({sub_no}地號)"

                sub_parcels.append({
                    "index": i + 1,
                    "label": sub_label,
                    "sub_number": sub_no,
                    "town": town,
                    "section": section,
                    "full_title": f"{town}{section} {sub_no}地號",
                    "area_sqm": round(sub_area, 2),
                    "area_ping": round(sub_area * 0.3025, 2),
                    "frontage_m": round(sub_w, 2),
                    "depth_m": round(total_d, 2),
                    "coverage_rate": coverage,
                    "far_rate": far,
                    "max_building_area_sqm": round(sub_area * (coverage / 100.0), 2),
                    "max_floor_area_sqm": round(sub_area * (far / 100.0), 2),
                    "est_present_value_twd": int(sub_area * unit_price),
                    "center_lat": round(c_lat, 6),
                    "center_lon": round(c_lon, 6),
                    "polygon_twd97": sub_poly_twd97,
                    "polygon_wgs84": sub_poly_wgs84,
                    "color_hex": "#2563eb" if i == 0 else "#059669" if i == 1 else "#d97706" if i == 2 else "#7c3aed"
                })

                if i < count - 1:
                    # Cut line
                    cut_pt1_twd97 = to_global_twd97(next_x, -half_d)
                    cut_pt2_twd97 = to_global_twd97(next_x, half_d)
                    cut_lines_twd97.append([cut_pt1_twd97, cut_pt2_twd97])
                    cut_lines_wgs84.append([
                        list(twd97_119_to_latlon(cut_pt1_twd97[0], cut_pt1_twd97[1])),
                        list(twd97_119_to_latlon(cut_pt2_twd97[0], cut_pt2_twd97[1]))
                    ])

                cur_x = next_x

        else:
            # Splitting along the depth (front lot and rear lot)
            cur_y = -half_d
            for i, frac in enumerate(slice_fractions):
                sub_d = total_d * frac
                next_y = cur_y + sub_d
                sub_area = area_sqm * frac

                p_c1 = (-half_w, cur_y)
                p_c2 = (half_w, cur_y)
                p_c3 = (half_w, next_y)
                p_c4 = (-half_w, next_y)
                p_c5 = p_c1

                sub_poly_twd97 = [to_global_twd97(px, py) for px, py in [p_c1, p_c2, p_c3, p_c4, p_c5]]
                sub_poly_wgs84 = [list(twd97_119_to_latlon(gx, gy)) for gx, gy in sub_poly_twd97]

                center_lx = 0.0
                center_ly = (cur_y + next_y) / 2.0
                c_gx, c_gy = to_global_twd97(center_lx, center_ly)
                c_lat, c_lon = twd97_119_to_latlon(c_gx, c_gy)

                sub_no = f"{number}" if i == 0 else f"{number}-{i}"
                sub_label = f"前院地 ({sub_no}地號)" if i == 0 else f"後進地 ({sub_no}地號)" if i == 1 else f"{chr(65+i)}地 ({sub_no}地號)"

                sub_parcels.append({
                    "index": i + 1,
                    "label": sub_label,
                    "sub_number": sub_no,
                    "town": town,
                    "section": section,
                    "full_title": f"{town}{section} {sub_no}地號",
                    "area_sqm": round(sub_area, 2),
                    "area_ping": round(sub_area * 0.3025, 2),
                    "frontage_m": round(total_w, 2),
                    "depth_m": round(sub_d, 2),
                    "coverage_rate": coverage,
                    "far_rate": far,
                    "max_building_area_sqm": round(sub_area * (coverage / 100.0), 2),
                    "max_floor_area_sqm": round(sub_area * (far / 100.0), 2),
                    "est_present_value_twd": int(sub_area * unit_price),
                    "center_lat": round(c_lat, 6),
                    "center_lon": round(c_lon, 6),
                    "polygon_twd97": sub_poly_twd97,
                    "polygon_wgs84": sub_poly_wgs84,
                    "color_hex": "#2563eb" if i == 0 else "#059669" if i == 1 else "#d97706" if i == 2 else "#7c3aed"
                })

                if i < count - 1:
                    cut_pt1_twd97 = to_global_twd97(-half_w, next_y)
                    cut_pt2_twd97 = to_global_twd97(half_w, next_y)
                    cut_lines_twd97.append([cut_pt1_twd97, cut_pt2_twd97])
                    cut_lines_wgs84.append([
                        list(twd97_119_to_latlon(cut_pt1_twd97[0], cut_pt1_twd97[1])),
                        list(twd97_119_to_latlon(cut_pt2_twd97[0], cut_pt2_twd97[1]))
                    ])

                cur_y = next_y

        # Regulatory Diagnostics
        is_farmland = ("農" in zoning or "耕" in zoning)
        min_farmland_sqm = 2500.0 # 0.25 公頃 (756.25 坪)
        has_sub_under_min_farmland = any(p["area_sqm"] < min_farmland_sqm for p in sub_parcels)

        farmland_check = {
            "is_farmland": is_farmland,
            "min_required_sqm": min_farmland_sqm,
            "min_required_ping": 756.25,
            "status": "WARNING" if (is_farmland and has_sub_under_min_farmland) else "PASS",
            "law_title": "農業發展條例第 16 條 (耕地分割限制)",
            "message": (
                "⚠️ 警示：本宗地屬於農業用地，且分割後子筆面積小於 0.25 公頃 (2,500 ㎡ / 756.25 坪)。依法原則不得分割；但符合「繼承分割」、「因買賣與毗鄰耕地合併」等 8 款法定例外情形者，可依法檢附證明辦理。"
                if (is_farmland and has_sub_under_min_farmland)
                else "✅ 合規：符合農業發展條例規定（或非屬受限耕地）。"
            ),
            "exceptions": [
                "1. 因買賣、贈與或交換，與毗鄰耕地合併者。",
                "2. 依土地法或土地徵收條例徵收土地者。",
                "3. 因繼承而為分割者（每人分割後得未滿0.25公頃）。",
                "4. 耕地分割後提供公用設施使用者。",
                "5. 農業發展條例修正前（民國89年1月28日前）已共有之耕地分割。"
            ]
        }

        # Building site min dimensions check (金門縣畸零地使用自治條例)
        min_frontage_req = 3.5
        min_depth_req = 12.0
        frontage_warning = any(p["frontage_m"] < min_frontage_req for p in sub_parcels)
        depth_warning = any(p["depth_m"] < min_depth_req for p in sub_parcels)

        dimensions_check = {
            "min_frontage_m": min_frontage_req,
            "min_depth_m": min_depth_req,
            "status": "WARNING" if (frontage_warning or depth_warning) else "PASS",
            "law_title": "金門縣畸零地使用自治條例規範",
            "message": (
                "⚠️ 注意：部分分割後子地號臨路面寬小於 3.5m 或深度小於 12m，恐構成畸零地，未來單獨申請建照恐受限，建議調整分割線或預留鄰地通行持分地。"
                if (frontage_warning or depth_warning)
                else "✅ 合規：各子地號面寬與深度均達法定建築基地標準，可單獨請領建照獨立開發。"
            )
        }

        return {
            "success": True,
            "split_mode": split_mode,
            "cut_axis": cut_axis,
            "parent_parcel": {
                "title": f"{town}{section} {number}地號",
                "town": town,
                "section": section,
                "number": number,
                "area_sqm": area_sqm,
                "area_ping": round(area_sqm * 0.3025, 2),
                "zoning": zoning,
                "total_frontage_m": round(total_w, 2),
                "total_depth_m": round(total_d, 2),
                "polygon_twd97": base_polygon_twd97,
                "polygon_wgs84": base_polygon_wgs84
            },
            "sub_parcels": sub_parcels,
            "cut_lines_twd97": cut_lines_twd97,
            "cut_lines_wgs84": cut_lines_wgs84,
            "regulatory_checks": {
                "farmland": farmland_check,
                "dimensions": dimensions_check
            }
        }

    @classmethod
    def simulate_merger(
        cls,
        primary_info: Dict[str, Any],
        neighbors: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Simulate cadastral merger for primary parcel and 1 or more neighboring parcels.
        """
        lat = float(primary_info.get("lat", 24.4550))
        lon = float(primary_info.get("lon", 118.3300))
        p_area = float(primary_info.get("area_sqm", 330.6))
        town = primary_info.get("town", "金寧鄉")
        section = primary_info.get("section", "赤岑段")
        number = str(primary_info.get("number", "165"))
        zoning = primary_info.get("zoning", "自然村專用區")
        coverage = float(primary_info.get("building_coverage", 60))
        far = float(primary_info.get("floor_area_ratio", 180))
        unit_price = float(primary_info.get("unit_price_sqm", 35000.0))

        if not neighbors:
            # Generate authentic adjacent mock neighbors for demo
            neighbors = [
                {
                    "number": f"{number}-1",
                    "title": f"{town}{section} {number}-1地號",
                    "area_sqm": round(p_area * 0.65, 1),
                    "zoning": zoning,
                    "rel_pos": "東側毗鄰"
                },
                {
                    "number": str(int(number) + 1) if number.isdigit() else "166",
                    "title": f"{town}{section} {int(number)+1 if number.isdigit() else '166'}地號",
                    "area_sqm": round(p_area * 0.8, 1),
                    "zoning": zoning,
                    "rel_pos": "南側毗鄰"
                }
            ]

        # Calculate merged totals
        total_merged_sqm = p_area + sum(float(n.get("area_sqm", 100.0)) for n in neighbors)
        merged_ping = round(total_merged_sqm * 0.3025, 2)

        # Base vs Merged Dimensions
        orig_w, orig_d = cls.get_base_dimensions(p_area, 1.45)
        merged_w, merged_d = cls.get_base_dimensions(total_merged_sqm, 1.35)

        # Polygon generation for merged parcel
        x_c, y_c = latlon_to_twd97_119(lat, lon)
        rad = math.radians(15.0)
        cos_r = math.cos(rad)
        sin_r = math.sin(rad)

        def to_global_twd97(lx: float, ly: float) -> Tuple[float, float]:
            rx = lx * cos_r - ly * sin_r
            ry = lx * sin_r + ly * cos_r
            return round(x_c + rx, 3), round(y_c + ry, 3)

        half_w = merged_w / 2.0
        half_d = merged_d / 2.0
        merged_corners_local = [
            (-half_w, -half_d),
            (half_w, -half_d),
            (half_w, half_d),
            (-half_w, half_d),
            (-half_w, -half_d)
        ]
        merged_polygon_twd97 = [to_global_twd97(px, py) for px, py in merged_corners_local]
        merged_polygon_wgs84 = [list(twd97_119_to_latlon(gx, gy)) for gx, gy in merged_polygon_twd97]

        # Capacity expansion metrics
        orig_coverage_sqm = round(p_area * (coverage / 100.0), 2)
        orig_far_sqm = round(p_area * (far / 100.0), 2)
        merged_coverage_sqm = round(total_merged_sqm * (coverage / 100.0), 2)
        merged_far_sqm = round(total_merged_sqm * (far / 100.0), 2)

        # Scale bonus estimation (規模經濟效益)
        frontage_growth = round((merged_w - orig_w) / orig_w * 100.0, 1)
        far_growth = round((merged_far_sqm - orig_far_sqm) / orig_far_sqm * 100.0, 1)

        # Regulatory law check for merger (土地登記規則第88條)
        zoning_consistent = all(n.get("zoning", zoning) == zoning for n in neighbors)
        merger_law_check = {
            "status": "PASS" if zoning_consistent else "WARNING",
            "law_title": "土地登記規則第 88 條 (宗地合併規定)",
            "message": (
                "✅ 合規：各筆土地之使用分區完全相同，符合地籍測量實施規則及土地登記規則合併要件。"
                if zoning_consistent else
                "⚠️ 警示：部分毗鄰土地使用分區不一致，依土地登記規則規定，使用分區不同之土地非經變更登記不得逕行合併。"
            ),
            "requirements": [
                "1. 土地所有權人須相同，或經全體共有人協議同意辦理合併。",
                "2. 土地必須相互毗鄰連接，無公共設施或未登錄道路阻隔。",
                "3. 使用分區及使用地類別須相同（都市計畫內土地或非都市土地分區相同）。",
                "4. 抵押權或限制登記之負擔需先清理或協議轉載。"
            ]
        }

        # Merged number assignment: Primary number retained
        merged_title = f"{town}{section} {number}地號 (合併後)"

        return {
            "success": True,
            "primary_parcel": {
                "title": f"{town}{section} {number}地號",
                "area_sqm": p_area,
                "area_ping": round(p_area * 0.3025, 2),
                "frontage_m": orig_w,
                "depth_m": orig_d,
                "coverage_sqm": orig_coverage_sqm,
                "far_sqm": orig_far_sqm,
                "est_present_value_twd": int(p_area * unit_price)
            },
            "merged_parcel": {
                "title": merged_title,
                "retained_number": number,
                "town": town,
                "section": section,
                "total_area_sqm": round(total_merged_sqm, 2),
                "total_area_ping": merged_ping,
                "frontage_m": merged_w,
                "depth_m": merged_d,
                "coverage_rate": coverage,
                "far_rate": far,
                "merged_coverage_sqm": merged_coverage_sqm,
                "merged_far_sqm": merged_far_sqm,
                "est_present_value_twd": int(total_merged_sqm * unit_price),
                "polygon_twd97": merged_polygon_twd97,
                "polygon_wgs84": merged_polygon_wgs84,
                "center_lat": round(lat, 6),
                "center_lon": round(lon, 6)
            },
            "neighbors_included": neighbors,
            "growth_benefits": {
                "frontage_increase_percent": frontage_growth,
                "far_increase_sqm": round(merged_far_sqm - orig_far_sqm, 2),
                "far_growth_percent": far_growth,
                "est_units": math.floor(merged_far_sqm / 100.0) # approx 30-ping apartments
            },
            "regulatory_check": merger_law_check
        }

    @classmethod
    def generate_subdivision_dxf(cls, sim_result: Dict[str, Any]) -> str:
        """
        Generate standard AutoCAD DXF for the subdivided cadastral boundaries & cut lines.
        """
        parent = sim_result["parent_parcel"]
        sub_parcels = sim_result["sub_parcels"]
        cut_lines = sim_result.get("cut_lines_twd97", [])

        # Extents
        all_xs: List[float] = []
        all_ys: List[float] = []
        for sp in sub_parcels:
            for pt in sp["polygon_twd97"]:
                all_xs.append(pt[0])
                all_ys.append(pt[1])

        min_x = min(all_xs) - 20.0
        min_y = min(all_ys) - 20.0
        max_x = max(all_xs) + 20.0
        max_y = max(all_ys) + 20.0

        dxf = []
        # Header
        dxf.extend([
            "0", "SECTION",
            "2", "HEADER",
            "9", "$ACADVER", "1", "AC1009",
            "9", "$INSUNITS", "70", "6", # Meters
            "9", "$MEASUREMENT", "70", "1",
            "9", "$EXTMIN", "10", str(min_x), "20", str(min_y), "30", "0.0",
            "9", "$EXTMAX", "10", str(max_x), "20", str(max_y), "30", "0.0",
            "0", "ENDSEC"
        ])

        # Tables / Layers
        dxf.extend([
            "0", "SECTION",
            "2", "TABLES",
            "0", "TABLE",
            "2", "LAYER",
            "70", "4",
            # Layer 1: PARENT_BOUNDARY (Yellow)
            "0", "LAYER", "2", "PARENT_BOUNDARY", "70", "0", "62", "2", "6", "DASHED",
            # Layer 2: SUBDIVIDED_LOTS (Green)
            "0", "LAYER", "2", "SUBDIVIDED_LOTS", "70", "0", "62", "3", "6", "CONTINUOUS",
            # Layer 3: CUT_LINES (Cyan)
            "0", "LAYER", "2", "CUT_LINES", "70", "0", "62", "4", "6", "CONTINUOUS",
            # Layer 4: LOT_ANNOTATION (White)
            "0", "LAYER", "2", "LOT_ANNOTATION", "70", "0", "62", "7", "6", "CONTINUOUS",
            "0", "ENDTAB",
            "0", "ENDSEC"
        ])

        # Entities
        dxf.extend([
            "0", "SECTION",
            "2", "ENTITIES"
        ])

        # Write each sub-parcel as lightweight polyline
        for sp in sub_parcels:
            pts = sp["polygon_twd97"]
            dxf.extend([
                "0", "POLYLINE",
                "8", "SUBDIVIDED_LOTS",
                "66", "1",
                "70", "1" # Closed
            ])
            for pt in pts[:-1]:
                dxf.extend([
                    "0", "VERTEX",
                    "8", "SUBDIVIDED_LOTS",
                    "10", str(pt[0]),
                    "20", str(pt[1]),
                    "30", "0.0"
                ])
            dxf.extend(["0", "SEQEND"])

            # Center text annotation
            cx, cy = latlon_to_twd97_119(sp["center_lat"], sp["center_lon"])
            text_str = f"{sp['sub_number']} ({sp['area_sqm']}m2 / {sp['area_ping']}坪)"
            dxf.extend([
                "0", "TEXT",
                "8", "LOT_ANNOTATION",
                "10", str(cx),
                "20", str(cy),
                "30", "0.0",
                "40", "1.8", # Text height in meters
                "1", text_str,
                "50", "15.0" # Rotation
            ])

        # Write cut lines
        for cl in cut_lines:
            dxf.extend([
                "0", "LINE",
                "8", "CUT_LINES",
                "10", str(cl[0][0]),
                "20", str(cl[0][1]),
                "30", "0.0",
                "11", str(cl[1][0]),
                "21", str(cl[1][1]),
                "31", "0.0"
            ])

        dxf.extend([
            "0", "ENDSEC",
            "0", "EOF"
        ])

        return "\n".join(dxf)
