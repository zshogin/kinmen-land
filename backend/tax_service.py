"""
Tax Calculator Service for Kinmen Land Cloud (金門地政雲)
Implements:
1. Land Value Increment Tax (土地增值稅 - 土地稅法第33條、第34條)
   - Regular progressive tax tiers (20%, 30%, 40%) with formula deductions
   - Self-use residential preferential tax rate (自用住宅優惠稅率 10%)
   - Long-term holding tax reductions (長期持有20年/30年/40年分別減徵20%/30%/40%)
2. Buyer Registration & Transaction Expenses (買方稅費與地政規費)
   - Deed Tax (契稅 6% - 契稅條例第2條、第3條)
   - Stamp Duty (公契印花稅 0.1% - 印花稅法第5條)
   - Land Registration Fee (地政買賣登記規費 0.1% + 書狀費每張80元 - 土地法第65條)
   - Professional Land Scrivener Fee (地政士代書簽約與登記代辦費預估)
3. House and Land Transactions Income Tax 2.0 (房地合一稅2.0 說明與試算)
"""

from typing import Dict, Any, Optional
import math

class TaxCalculator:

    @staticmethod
    def calculate_lvit(
        land_area_sqm: float,
        current_announced_val: float,
        prev_announced_val: float,
        cpi_ratio: float = 100.0,
        holding_years: int = 5,
        is_self_use: bool = False,
        land_improvement_cost: float = 0.0
    ) -> Dict[str, Any]:
        """
        Calculate Land Value Increment Tax (土地增值稅)
        """
        land_area_sqm = max(0.1, float(land_area_sqm))
        current_announced_val = max(1.0, float(current_announced_val))
        prev_announced_val = max(1.0, float(prev_announced_val))
        cpi_ratio = max(50.0, float(cpi_ratio))
        holding_years = max(0, int(holding_years))
        land_improvement_cost = max(0.0, float(land_improvement_cost))

        # 1. 申報移轉現值總額
        p_current_total = land_area_sqm * current_announced_val

        # 2. 前次移轉現值 (經消費者物價指數調整)
        cpi_factor = cpi_ratio / 100.0
        p_prev_adjusted_total = land_area_sqm * prev_announced_val * cpi_factor

        # 3. 土地漲價總數額
        increment_total = max(0.0, p_current_total - p_prev_adjusted_total - land_improvement_cost)

        if increment_total <= 0:
            return {
                "p_current_total": round(p_current_total),
                "p_prev_adjusted_total": round(p_prev_adjusted_total),
                "increment_total": 0,
                "increment_ratio": 0.0,
                "tax_tier_desc": "無土地漲價數額 (免課土地增值稅)",
                "tax_rate_pct": 0,
                "basic_tax": 0,
                "holding_reduction": 0,
                "final_tax": 0,
                "is_self_use": is_self_use,
                "holding_years": holding_years
            }

        # 4. 漲價倍數比率
        ratio = increment_total / p_prev_adjusted_total if p_prev_adjusted_total > 0 else 3.0

        if is_self_use:
            # 自用住宅優惠稅率 10%
            tax_rate_pct = 10.0
            tax_tier_desc = "自用住宅優惠稅率 (10%) - 一生一次 / 一生一屋"
            basic_tax = increment_total * 0.10
            holding_reduction = 0.0
            final_tax = basic_tax
        else:
            # 一般用地累進稅率 (土地稅法第33條)
            if ratio <= 1.0:
                # 第一級：漲價總數額在原規定地價或前次移轉現值總額100%以下者
                tax_rate_pct = 20.0
                tax_tier_desc = "第一級 (漲價倍數 ≤ 100%，稅率 20%)"
                basic_tax = increment_total * 0.20
            elif ratio <= 2.0:
                # 第二級：超過100%未達200%者
                tax_rate_pct = 30.0
                deduction = p_prev_adjusted_total * 0.10
                tax_tier_desc = "第二級 (漲價倍數 100%~200%，稅率 30% 減累進差額 10%)"
                basic_tax = max(0.0, (increment_total * 0.30) - deduction)
            else:
                # 第三級：超過200%以上者
                tax_rate_pct = 40.0
                deduction = p_prev_adjusted_total * 0.30
                tax_tier_desc = "第三級 (漲價倍數 > 200%，稅率 40% 減累進差額 30%)"
                basic_tax = max(0.0, (increment_total * 0.40) - deduction)

            # 長期持有減徵 (土地稅法第33條第6項)
            # 就超過最低稅率(20%)部分之稅額，持有20年以上減徵20%、30年以上減徵30%、40年以上減徵40%
            min_rate_tax = increment_total * 0.20
            excess_tax = max(0.0, basic_tax - min_rate_tax)

            discount_pct = 0
            if holding_years >= 40:
                discount_pct = 40
            elif holding_years >= 30:
                discount_pct = 30
            elif holding_years >= 20:
                discount_pct = 20

            holding_reduction = excess_tax * (discount_pct / 100.0)
            final_tax = max(0.0, basic_tax - holding_reduction)

        return {
            "p_current_total": round(p_current_total),
            "p_prev_adjusted_total": round(p_prev_adjusted_total),
            "increment_total": round(increment_total),
            "increment_ratio": round(ratio * 100, 1),
            "tax_tier_desc": tax_tier_desc,
            "tax_rate_pct": tax_rate_pct,
            "basic_tax": round(basic_tax),
            "holding_discount_pct": discount_pct if not is_self_use else 0,
            "holding_reduction": round(holding_reduction),
            "final_tax": round(final_tax),
            "is_self_use": is_self_use,
            "holding_years": holding_years
        }

    @staticmethod
    def calculate_buyer_expenses(
        land_area_sqm: float,
        current_announced_val: float,
        has_building: bool = False,
        building_area_ping: float = 0.0,
        building_eval_val_per_ping: float = 12000.0,
        scrivener_fee: float = 15000.0
    ) -> Dict[str, Any]:
        """
        Calculate Buyer's taxes and fees (買方負擔稅費與規費)
        """
        land_area_sqm = max(0.1, float(land_area_sqm))
        current_announced_val = max(1.0, float(current_announced_val))
        building_area_ping = max(0.0, float(building_area_ping))
        building_eval_val_per_ping = max(1000.0, float(building_eval_val_per_ping))

        # 1. 土地買賣公契現值總額
        land_contract_val = land_area_sqm * current_announced_val

        # 2. 房屋評定現值總額
        house_eval_val = (building_area_ping * building_eval_val_per_ping) if has_building else 0.0

        # 公契總金額
        contract_total = land_contract_val + house_eval_val

        # 3. 契稅 (Deed Tax) - 僅房屋課徵 6%，純土地買賣免課契稅
        deed_tax = round(house_eval_val * 0.06)

        # 4. 印花稅 (Stamp Duty) - 公契移轉現值總額 0.1% (千分之一)
        stamp_duty = round(contract_total * 0.001)

        # 5. 地政買賣登記規費 (Registration Fee) - 公契移轉現值總額 0.1%
        registration_fee = round(contract_total * 0.001)

        # 6. 書狀費 (Certificate Fee) - 每張 80 元
        cert_count = 2 if has_building else 1
        certificate_fee = cert_count * 80

        # 7. 地政士代書費 (Scrivener Fee)
        scrivener_fee = round(scrivener_fee)

        # 買方總支出
        buyer_total = deed_tax + stamp_duty + registration_fee + certificate_fee + scrivener_fee

        return {
            "land_contract_val": round(land_contract_val),
            "house_eval_val": round(house_eval_val),
            "contract_total": round(contract_total),
            "deed_tax": deed_tax,
            "deed_tax_desc": f"房屋契稅 6% (現值 ${round(house_eval_val):,} × 6%)" if has_building else "免契稅 (純土地買賣免課契稅)",
            "stamp_duty": stamp_duty,
            "stamp_duty_desc": f"公契現值 0.1% (千分之一) (${round(contract_total):,} × 0.1%)",
            "registration_fee": registration_fee,
            "registration_fee_desc": f"地政所有權移轉登記費 0.1% (${round(contract_total):,} × 0.1%)",
            "certificate_fee": certificate_fee,
            "certificate_fee_desc": f"土地/建物權狀工本費 (每張 $80 共 {cert_count} 張)",
            "scrivener_fee": scrivener_fee,
            "scrivener_fee_desc": "地政士簽約、買賣過戶與實價登錄代辦費行情預估",
            "buyer_total": round(buyer_total),
            "has_building": has_building,
            "building_area_ping": building_area_ping
        }

    @classmethod
    def calculate_full_transaction(cls, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Aggregate calculation for both buyer and seller.
        """
        land_area_sqm = float(payload.get("land_area_sqm", 330.6))
        current_announced_val = float(payload.get("current_announced_val", 2500.0))
        prev_announced_val = float(payload.get("prev_announced_val", 800.0))
        cpi_ratio = float(payload.get("cpi_ratio", 100.0))
        holding_years = int(payload.get("holding_years", 5))
        is_self_use = bool(payload.get("is_self_use", False))
        land_improvement_cost = float(payload.get("land_improvement_cost", 0.0))
        
        has_building = bool(payload.get("has_building", False))
        building_area_ping = float(payload.get("building_area_ping", 0.0))
        building_eval_val_per_ping = float(payload.get("building_eval_val_per_ping", 12000.0))
        scrivener_fee = float(payload.get("scrivener_fee", 15000.0))

        # 賣方土增稅
        seller_tax = cls.calculate_lvit(
            land_area_sqm=land_area_sqm,
            current_announced_val=current_announced_val,
            prev_announced_val=prev_announced_val,
            cpi_ratio=cpi_ratio,
            holding_years=holding_years,
            is_self_use=is_self_use,
            land_improvement_cost=land_improvement_cost
        )

        # 買方稅規費
        buyer_tax = cls.calculate_buyer_expenses(
            land_area_sqm=land_area_sqm,
            current_announced_val=current_announced_val,
            has_building=has_building,
            building_area_ping=building_area_ping,
            building_eval_val_per_ping=building_eval_val_per_ping,
            scrivener_fee=scrivener_fee
        )

        # 交易總稅費與比例
        total_transaction_tax_cost = seller_tax["final_tax"] + buyer_tax["buyer_total"]
        seller_ratio_pct = round((seller_tax["final_tax"] / total_transaction_tax_cost * 100), 1) if total_transaction_tax_cost > 0 else 50.0
        buyer_ratio_pct = round(100.0 - seller_ratio_pct, 1) if total_transaction_tax_cost > 0 else 50.0

        # 房地合一稅 2.0 稅率說明對照
        house_land_tax_rules = [
            {"period": "持有 2 年以內", "rate_pct": 45, "note": "短期交易抑制高稅率"},
            {"period": "持有超過 2 年，未逾 5 年", "rate_pct": 35, "note": "中短期交易適用"},
            {"period": "持有超過 5 年，未逾 10 年", "rate_pct": 20, "note": "長期一般置產適用"},
            {"period": "持有超過 10 年以上", "rate_pct": 15, "note": "長期持有優惠最低稅率"},
            {"period": "自住住宅優惠 (設籍滿6年且無出租)", "rate_pct": 10, "note": "獲利 400 萬以下免稅，超過部分按 10%"}
        ]

        # 金門在地地政稅務特性提示
        kinmen_tax_notices = [
            "金門縣土地公告現值與台灣本島相較相對平穩，若自戰地政務時期或早期繼承取得，前次移轉現值可能較低，漲價倍數可能跨入第二或第三級距，建議檢視是否符合自用住宅優惠稅率。",
            "農業用地依法作農業使用，於移轉予自然人時，得依土地稅法第39條之2申請不課徵土地增值稅。",
            "公共設施保留地（如都市計畫道路、公園保留地）尚未徵收前之買賣移轉，依法免徵土地增值稅。",
            "若同時移轉建物（如集合住宅、透天），買方須繳納 6% 契稅，若為純農地或建地移轉則免課契稅。"
        ]

        return {
            "parameters": {
                "land_area_sqm": land_area_sqm,
                "land_area_ping": round(land_area_sqm * 0.3025, 2),
                "current_announced_val": current_announced_val,
                "prev_announced_val": prev_announced_val,
                "cpi_ratio": cpi_ratio,
                "holding_years": holding_years,
                "is_self_use": is_self_use,
                "has_building": has_building,
                "building_area_ping": building_area_ping
            },
            "summary": {
                "seller_total_tax": seller_tax["final_tax"],
                "buyer_total_tax": buyer_tax["buyer_total"],
                "combined_total_cost": total_transaction_tax_cost,
                "seller_ratio_pct": seller_ratio_pct,
                "buyer_ratio_pct": buyer_ratio_pct
            },
            "seller": seller_tax,
            "buyer": buyer_tax,
            "house_land_tax_rules": house_land_tax_rules,
            "kinmen_tax_notices": kinmen_tax_notices
        }

tax_calculator = TaxCalculator()
