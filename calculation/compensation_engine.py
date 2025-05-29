#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
弁護士基準損害賠償計算エンジン
正確な計算ロジックと法的基準に基づいた計算処理
"""

from decimal import Decimal, ROUND_HALF_UP
from datetime import date, datetime
from typing import Dict, Any, Optional, Tuple, List
import logging
from dataclasses import dataclass

from models import CaseData, PersonInfo, AccidentInfo, MedicalInfo, IncomeInfo
from utils.error_handler import get_error_handler, CalculationError, ErrorSeverity # 追加

@dataclass
class CalculationResult:
    """計算結果データクラス"""
    item_name: str
    amount: Decimal
    calculation_details: str
    legal_basis: str = ""
    notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'item_name': self.item_name,
            'amount': str(self.amount),
            'calculation_details': self.calculation_details,
            'legal_basis': self.legal_basis,
            'notes': self.notes
        }

class CompensationEngine:
    """弁護士基準損害賠償計算エンジン"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._error_handler = get_error_handler() # 追加
        self.init_standards()
    
    def init_standards(self):
        """法的基準データの初期化"""
        
        # 入通院慰謝料表（赤い本別表I） 単位：万円
        # より詳細で正確なデータに拡張
        self.hospitalization_table_1 = {
            0: {0:0, 1:28, 2:52, 3:73, 4:90, 5:105, 6:116, 7:124, 8:132, 9:139, 10:145, 11:150, 12:154, 13:158, 14:162, 15:166, 16:169, 17:172, 18:175, 19:178, 20:180},
            1: {0:53, 1:77, 2:98, 3:115, 4:130, 5:141, 6:150, 7:158, 8:164, 9:169, 10:174, 11:177, 12:181, 13:185, 14:189, 15:193, 16:196, 17:199, 18:201, 19:204, 20:206},
            2: {0:101, 1:122, 2:140, 3:154, 4:167, 5:176, 6:183, 7:188, 8:193, 9:196, 10:199, 11:201, 12:204, 13:207, 14:210, 15:213, 16:215, 17:218, 18:220, 19:222, 20:224},
            3: {0:145, 1:162, 2:177, 3:188, 4:197, 5:204, 6:209, 7:213, 8:216, 9:218, 10:221, 11:223, 12:225, 13:228, 14:231, 15:233, 16:235, 17:237, 18:239, 19:241, 20:243},
            4: {0:165, 1:184, 2:198, 3:208, 4:216, 5:223, 6:228, 7:232, 8:235, 9:237, 10:239, 11:241, 12:243, 13:245, 14:247, 15:249, 16:251, 17:252, 18:254, 19:256, 20:257},
            5: {0:183, 1:202, 2:215, 3:225, 4:233, 5:239, 6:244, 7:248, 8:250, 9:252, 10:254, 11:256, 12:258, 13:260, 14:262, 15:264, 16:265, 17:267, 18:268, 19:270, 20:271},
            6: {0:199, 1:218, 2:230, 3:239, 4:246, 5:252, 6:257, 7:260, 8:262, 9:264, 10:266, 11:268, 12:270, 13:272, 14:274, 15:276, 16:277, 17:279, 18:280, 19:282, 20:283},
            7: {0:212, 1:231, 2:242, 3:250, 4:256, 5:261, 6:266, 7:269, 8:271, 9:273, 10:275, 11:277, 12:279, 13:281, 14:282, 15:284, 16:285, 17:287, 18:288, 19:290, 20:291},
            8: {0:224, 1:242, 2:252, 3:259, 4:265, 5:270, 6:274, 7:277, 8:279, 9:281, 10:283, 11:285, 12:286, 13:288, 14:290, 15:291, 16:293, 17:294, 18:295, 19:297, 20:298},
            9: {0:234, 1:251, 2:261, 3:267, 4:272, 5:277, 6:281, 7:284, 8:286, 9:288, 10:290, 11:292, 12:293, 13:295, 14:296, 15:298, 16:299, 17:301, 18:302, 19:303, 20:305},
            10: {0:242, 1:259, 2:268, 3:274, 4:279, 5:284, 6:287, 7:290, 8:292, 9:294, 10:296, 11:298, 12:299, 13:301, 14:302, 15:304, 16:305, 17:306, 18:308, 19:309, 20:310}
        }
        
        # むちうち症等（他覚症状なし）の場合 - 別表II
        self.hospitalization_table_2 = {
            k: {vk: round(vv * 0.67) for vk, vv in v.items()}
            for k, v in self.hospitalization_table_1.items()
        }
        
        # 後遺障害慰謝料（弁護士基準）
        self.disability_compensation = {
            1: 2800, 2: 2370, 3: 1990, 4: 1670, 5: 1400, 6: 1180, 7: 1000,
            8: 830, 9: 690, 10: 550, 11: 420, 12: 290, 13: 180, 14: 110
        }
        
        # 労働能力喪失率
        self.disability_loss_rate = {
            1: 100, 2: 100, 3: 100, 4: 92, 5: 79, 6: 67, 7: 56,
            8: 45, 9: 35, 10: 27, 11: 20, 12: 14, 13: 9, 14: 5
        }
        
        # ライプニッツ係数（法定利率3%）- より正確な表
        self.leibniz_coefficients = {
            1: 0.971, 2: 1.913, 3: 2.829, 4: 3.717, 5: 4.580,
            6: 5.417, 7: 6.230, 8: 7.020, 9: 7.786, 10: 8.530,
            11: 9.253, 12: 9.954, 13: 10.635, 14: 11.296, 15: 11.938,
            16: 12.561, 17: 13.166, 18: 13.754, 19: 14.324, 20: 14.877,
            21: 15.415, 22: 15.937, 23: 16.444, 24: 16.936, 25: 17.413,
            26: 17.877, 27: 18.327, 28: 18.764, 29: 19.188, 30: 19.600,
            31: 20.000, 32: 20.389, 33: 20.766, 34: 21.132, 35: 21.487,
            36: 21.832, 37: 22.167, 38: 22.492, 39: 22.808, 40: 23.115,
            41: 23.412, 42: 23.701, 43: 23.982, 44: 24.254, 45: 24.519,
            46: 24.775, 47: 25.025, 48: 25.267, 49: 25.502, 50: 25.730,
            51: 25.951, 52: 26.166, 53: 26.374, 54: 26.578, 55: 26.774,
            56: 26.965, 57: 27.151, 58: 27.331, 59: 27.506, 60: 27.676,
            61: 27.840, 62: 28.000, 63: 28.155, 64: 28.306, 65: 28.453,
            66: 28.595, 67: 28.733
        }
        
        # 年齢別平均余命（簡易版）
        self.life_expectancy = {
            0: 81.41, 1: 80.43, 5: 76.48, 10: 71.52, 15: 66.56, 
            20: 61.63, 25: 56.72, 30: 51.84, 35: 47.00, 40: 42.21,
            45: 37.48, 50: 32.84, 55: 28.31, 60: 23.91, 65: 19.70,
            70: 15.71, 75: 12.05, 80: 8.78, 85: 6.04, 90: 3.95
        }
        
        # 家事従事者の年収基準
        self.housework_annual_income = {
            "全年齢平均": 3936000,  # 2023年基準
            "30代": 4200000,
            "40代": 4500000,
            "50代": 4300000,
            "60代": 3800000
        }

    def get_leibniz_coefficient(self, period: int) -> Optional[Decimal]:
        """指定された期間のライプニッツ係数を取得します。"""
        if period <= 0:
            return Decimal('0')
        if period in self.leibniz_coefficients:
            return Decimal(str(self.leibniz_coefficients[period]))
        else:
            # 辞書にない場合は近似計算 (3%の利率を想定)
            # (1 - (1 + 利率)^(-期間)) / 利率
            try:
                rate = Decimal('0.03')
                leibniz = (Decimal('1') - (Decimal('1') + rate) ** -period) / rate
                # 小数点以下3桁で四捨五入（一般的なライプニッツ係数の表示に合わせる）
                return leibniz.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
            except Exception as e:
                calc_err = CalculationError(
                    message=f"ライプニッツ係数の近似計算エラー (期間: {period}): {e}",
                    user_message="ライプニッツ係数の計算中にエラーが発生しました。入力期間を確認してください。",
                    severity=ErrorSeverity.MEDIUM,
                    context={"period": period, "original_error": str(e)}
                )
                self._error_handler.handle_exception(e, context=calc_err.context)
                # Noneを返すか、エラーを再送するかは設計次第。ここではNoneを返す。
                return None

    def calculate_hospitalization_compensation(self, medical_info: MedicalInfo) -> CalculationResult:
        """入通院慰謝料の計算"""
        try:
            hospital_months = min(medical_info.hospital_months, 10)  # 表の上限
            outpatient_months = min(medical_info.outpatient_months, 20)  # 表の上限
            
            # 使用する表を決定
            table = self.hospitalization_table_2 if medical_info.is_whiplash else self.hospitalization_table_1
            
            # 基本慰謝料の取得
            if hospital_months in table and outpatient_months in table[hospital_months]:
                base_amount = table[hospital_months][outpatient_months]
            else:
                # 表の範囲外の場合は最大値を使用
                max_hospital = max(table.keys())
                max_outpatient = max(table[max_hospital].keys())
                base_amount = table[max_hospital][max_outpatient]
            
            # 実通院日数による調整
            actual_days = medical_info.actual_outpatient_days
            if outpatient_months > 0 and actual_days > 0:
                expected_days = outpatient_months * 15  # 月15日通院が標準
                if actual_days < expected_days * 0.6:  # 実通院日数が少ない場合
                    adjustment_ratio = min(1.0, actual_days / (expected_days * 0.6))
                    base_amount = int(base_amount * adjustment_ratio)
            
            amount = Decimal(str(base_amount * 10000))  # 万円を円に変換
            
            table_type = "別表II（むちうち症等）" if medical_info.is_whiplash else "別表I"
            details = f"""
入院期間: {medical_info.hospital_months}ヶ月
通院期間: {medical_info.outpatient_months}ヶ月
実通院日数: {medical_info.actual_outpatient_days}日
適用表: 赤い本{table_type}
基準額: {base_amount}万円
"""
            
            return CalculationResult(
                item_name="入通院慰謝料",
                amount=amount,
                calculation_details=details.strip(),
                legal_basis="民法第709条、赤い本2023年版",
                notes="実通院日数が少ない場合は減額調整を行っています"
            )
            
        except KeyError as e: # テーブル参照エラー
            calc_err = CalculationError(
                message=f"入通院慰謝料表の参照エラー: {e}",
                user_message="入通院慰謝料の計算に必要なデータが見つかりませんでした。期間の入力が正しいか確認してください。",
                severity=ErrorSeverity.HIGH,
                context={"medical_info": medical_info.to_dict() if hasattr(medical_info, 'to_dict') else str(medical_info), "original_error": str(e)}
            )
            self._error_handler.handle_exception(e, context=calc_err.context)
            return CalculationResult(
                item_name="入通院慰謝料",
                amount=Decimal('0'),
                calculation_details=f"計算エラー: {calc_err.user_message}",
                legal_basis="",
                notes="計算できませんでした"
            )
        except Exception as e:
            calc_err = CalculationError(
                message=f"入通院慰謝料計算エラー: {e}",
                user_message="入通院慰謝料の計算中に予期せぬエラーが発生しました。",
                severity=ErrorSeverity.HIGH,
                context={"medical_info": medical_info.to_dict() if hasattr(medical_info, 'to_dict') else str(medical_info), "original_error": str(e)}
            )
            self._error_handler.handle_exception(e, context=calc_err.context)
            return CalculationResult(
                item_name="入通院慰謝料",
                amount=Decimal('0'),
                calculation_details=f"計算エラー: {str(e)}",
                legal_basis="",
                notes="計算できませんでした"
            )
    
    def calculate_disability_compensation(self, medical_info: MedicalInfo) -> CalculationResult:
        """後遺障害慰謝料の計算"""
        try:
            if medical_info.disability_grade == 0:
                return CalculationResult(
                    item_name="後遺障害慰謝料",
                    amount=Decimal('0'),
                    calculation_details="後遺障害等級の認定なし",
                    legal_basis="",
                    notes=""
                )
            
            grade = medical_info.disability_grade
            if grade in self.disability_compensation:
                base_amount = self.disability_compensation[grade]
                amount = Decimal(str(base_amount * 10000))  # 万円を円に変換
                
                details = f"""
後遺障害等級: 第{grade}級
弁護士基準慰謝料: {base_amount}万円
"""
                
                return CalculationResult(
                    item_name="後遺障害慰謝料",
                    amount=amount,
                    calculation_details=details.strip(),
                    legal_basis="民法第709条、赤い本2023年版",
                    notes=medical_info.disability_details
                )
            else:
                return CalculationResult(
                    item_name="後遺障害慰謝料",
                    amount=Decimal('0'),
                    calculation_details=f"第{grade}級は対応範囲外です",
                    legal_basis="",
                    notes="等級を確認してください"
                )
                
        except KeyError as e: # 等級テーブル参照エラー
            calc_err = CalculationError(
                message=f"後遺障害慰謝料テーブルの参照エラー (等級: {medical_info.disability_grade}): {e}",
                user_message=f"後遺障害等級 第{medical_info.disability_grade}級 に対応する慰謝料データが見つかりませんでした。",
                severity=ErrorSeverity.MEDIUM,
                context={"medical_info": medical_info.to_dict() if hasattr(medical_info, 'to_dict') else str(medical_info), "original_error": str(e)}
            )
            self._error_handler.handle_exception(e, context=calc_err.context)
            return CalculationResult(
                item_name="後遺障害慰謝料",
                amount=Decimal('0'),
                calculation_details=f"計算エラー: {calc_err.user_message}",
                legal_basis="",
                notes="等級を確認してください"
            )
        except Exception as e:
            calc_err = CalculationError(
                message=f"後遺障害慰謝料計算エラー: {e}",
                user_message="後遺障害慰謝料の計算中に予期せぬエラーが発生しました。",
                severity=ErrorSeverity.HIGH,
                context={"medical_info": medical_info.to_dict() if hasattr(medical_info, 'to_dict') else str(medical_info), "original_error": str(e)}
            )
            self._error_handler.handle_exception(e, context=calc_err.context)
            return CalculationResult(
                item_name="後遺障害慰謝料",
                amount=Decimal('0'),
                calculation_details=f"計算エラー: {str(e)}",
                legal_basis="",
                notes="計算できませんでした"
            )
    
    def calculate_lost_income(self, income_info: IncomeInfo) -> CalculationResult:
        """休業損害の計算"""
        try:
            if income_info.lost_work_days == 0:
                return CalculationResult(
                    item_name="休業損害",
                    amount=Decimal('0'),
                    calculation_details="休業日数の入力なし",
                    legal_basis="",
                    notes=""
                )
            
            daily_income = income_info.daily_income
            lost_days = income_info.lost_work_days
            amount = daily_income * lost_days
            
            details = f"""
休業日数: {lost_days}日
日額基礎収入: {daily_income:,}円
計算式: {daily_income:,}円 × {lost_days}日
"""
            
            return CalculationResult(
                item_name="休業損害",
                amount=amount,
                calculation_details=details.strip(),
                legal_basis="民法第709条",
                notes="事故前3ヶ月の実収入を基に算定"
            )
            
        except TypeError as e: # daily_income や lost_work_days が不正な型の場合
            calc_err = CalculationError(
                message=f"休業損害計算時の型エラー: {e}",
                user_message="休業損害の計算に必要な数値データ（日額収入、休業日数）の形式が正しくありません。",
                severity=ErrorSeverity.MEDIUM,
                context={"income_info": income_info.to_dict() if hasattr(income_info, 'to_dict') else str(income_info), "original_error": str(e)}
            )
            self._error_handler.handle_exception(e, context=calc_err.context)
            return CalculationResult(
                item_name="休業損害",
                amount=Decimal('0'),
                calculation_details=f"計算エラー: {calc_err.user_message}",
                legal_basis="",
                notes="計算できませんでした"
            )
        except Exception as e:
            calc_err = CalculationError(
                message=f"休業損害計算エラー: {e}",
                user_message="休業損害の計算中に予期せぬエラーが発生しました。",
                severity=ErrorSeverity.HIGH,
                context={"income_info": income_info.to_dict() if hasattr(income_info, 'to_dict') else str(income_info), "original_error": str(e)}
            )
            self._error_handler.handle_exception(e, context=calc_err.context)
            return CalculationResult(
                item_name="休業損害",
                amount=Decimal('0'),
                calculation_details=f"計算エラー: {str(e)}",
                legal_basis="",
                notes="計算できませんでした"
            )
    
    def calculate_future_income_loss(self, person_info: PersonInfo, medical_info: MedicalInfo, income_info: IncomeInfo) -> CalculationResult:
        """後遺障害逸失利益の計算"""
        try:
            if medical_info.disability_grade == 0 or income_info.loss_period_years == 0:
                return CalculationResult(
                    item_name="後遺障害逸失利益",
                    amount=Decimal('0'),
                    calculation_details="後遺障害等級の認定なし、または労働能力喪失期間の入力なし",
                    legal_basis="",
                    notes=""
                )
            
            # 基礎収入の決定
            if person_info.occupation == "家事従事者":
                base_income = Decimal(str(self.housework_annual_income["全年齢平均"]))
            else:
                # UI・モデル・エンジン間で basic_annual_income に統一
                base_income = income_info.basic_annual_income or person_info.annual_income
            
            # 労働能力喪失率
            grade = medical_info.disability_grade
            if grade not in self.disability_loss_rate:
                return CalculationResult(
                    item_name="後遺障害逸失利益",
                    amount=Decimal('0'),
                    calculation_details=f"第{grade}級は対応範囲外です",
                    legal_basis="",
                    notes=""
                )
            loss_rate = Decimal(str(self.disability_loss_rate[grade])) / 100
            loss_period = income_info.loss_period_years
            # ライプニッツ係数
            leibniz = self.get_leibniz_coefficient(loss_period) # 修正: メソッド呼び出しに変更
            if leibniz is None: # get_leibniz_coefficient が None を返す可能性に対処
                raise CalculationError("ライプニッツ係数の取得に失敗しました。", user_message="計算に必要な係数を取得できませんでした。")

            # 逸失利益計算
            amount = base_income * loss_rate * leibniz
            amount = amount.quantize(Decimal('1'), rounding=ROUND_HALF_UP)
            
            # 計算詳細の説明を修正 (f-string を使用)
            details = f"""基礎収入: {base_income:,.0f}円/年
労働能力喪失率: {loss_rate*100:.0f}%（第{grade}級）
労働能力喪失期間: {loss_period}年
ライプニッツ係数: {leibniz}
計算式: {base_income:,.0f}円 × {loss_rate*100:.0f}% × {leibniz} = {amount:,.0f}円"""
            
            notes = ""
            if person_info.occupation == "家事従事者":
                notes = "家事従事者については全年齢平均の女性労働者の平均賃金を使用"
            return CalculationResult(
                item_name="後遺障害逸失利益",
                amount=amount,
                calculation_details=details.strip(),
                legal_basis="民法第709条、最高裁判例",
                notes=notes
            )
            
        except KeyError as e: # 労働能力喪失率やライプニッツ係数の参照エラー
            calc_err = CalculationError(
                message=f"逸失利益計算のためのデータ参照エラー: {e}",
                user_message="逸失利益の計算に必要なデータ（労働能力喪失率、ライプニッツ係数など）が見つかりませんでした。",
                severity=ErrorSeverity.HIGH,
                context={
                    "person_info": person_info.to_dict() if hasattr(person_info, 'to_dict') else str(person_info),
                    "medical_info": medical_info.to_dict() if hasattr(medical_info, 'to_dict') else str(medical_info),
                    "income_info": income_info.to_dict() if hasattr(income_info, 'to_dict') else str(income_info),
                    "original_error": str(e)
                }
            )
            self._error_handler.handle_exception(e, context=calc_err.context)
            return CalculationResult(
                item_name="後遺障害逸失利益",
                amount=Decimal('0'),
                calculation_details=f"計算エラー: {calc_err.user_message}",
                legal_basis="",
                notes="計算できませんでした"
            )
        except TypeError as e: # 数値計算時の型エラー
            calc_err = CalculationError(
                message=f"逸失利益計算時の型エラー: {e}",
                user_message="逸失利益の計算に必要な数値データの形式が正しくありません。",
                severity=ErrorSeverity.HIGH,
                context={
                    "person_info": person_info.to_dict() if hasattr(person_info, 'to_dict') else str(person_info),
                    "medical_info": medical_info.to_dict() if hasattr(medical_info, 'to_dict') else str(medical_info),
                    "income_info": income_info.to_dict() if hasattr(income_info, 'to_dict') else str(income_info),
                    "original_error": str(e)
                }
            )
            self._error_handler.handle_exception(e, context=calc_err.context)
            return CalculationResult(
                item_name="後遺障害逸失利益",
                amount=Decimal('0'),
                calculation_details=f"計算エラー: {calc_err.user_message}",
                legal_basis="",
                notes="計算できませんでした"
            )
        except Exception as e:
            calc_err = CalculationError(
                message=f"後遺障害逸失利益計算エラー: {e}",
                user_message="後遺障害逸失利益の計算中に予期せぬエラーが発生しました。",
                severity=ErrorSeverity.HIGH,
                context={
                    "person_info": person_info.to_dict() if hasattr(person_info, 'to_dict') else str(person_info),
                    "medical_info": medical_info.to_dict() if hasattr(medical_info, 'to_dict') else str(medical_info),
                    "income_info": income_info.to_dict() if hasattr(income_info, 'to_dict') else str(income_info),
                    "original_error": str(e)
                }
            )
            self._error_handler.handle_exception(e, context=calc_err.context)
            return CalculationResult(
                item_name="後遺障害逸失利益",
                amount=Decimal('0'),
                calculation_details=f"計算エラー: {str(e)}",
                legal_basis="",
                notes="計算できませんでした"
            )
    
    def calculate_medical_expenses(self, medical_info: MedicalInfo) -> CalculationResult:
        """治療費・医療関係費の計算"""
        try:
            if not all(isinstance(val, (int, float, Decimal)) for val in 
                       [medical_info.medical_expenses, medical_info.transportation_costs, medical_info.nursing_costs]):
                raise TypeError("医療費関連の数値が無効です。")

            total_amount = Decimal(str(medical_info.medical_expenses)) + \
                           Decimal(str(medical_info.transportation_costs)) + \
                           Decimal(str(medical_info.nursing_costs))
            
            details = f"""治療費: {medical_info.medical_expenses:,.0f}円
交通費: {medical_info.transportation_costs:,.0f}円
看護費: {medical_info.nursing_costs:,.0f}円"""
            
            return CalculationResult(
                item_name="治療費・医療関係費",
                amount=total_amount,
                calculation_details=details.strip(),
                legal_basis="民法第709条",
                notes="実際に支出した費用"
            )
            
        except TypeError as e: # 数値加算時の型エラー
            calc_err = CalculationError(
                message=f"医療費計算時の型エラー: {e}",
                user_message="治療費・医療関係費の計算に必要な数値データの形式が正しくありません。",
                severity=ErrorSeverity.MEDIUM,
                context={"medical_info": medical_info.to_dict() if hasattr(medical_info, 'to_dict') else str(medical_info), "original_error": str(e)}
            )
            self._error_handler.handle_exception(e, context=calc_err.context)
            return CalculationResult(
                item_name="治療費・医療関係費",
                amount=Decimal('0'),
                calculation_details=f"計算エラー: {calc_err.user_message}",
                legal_basis="",
                notes="計算できませんでした"
            )
        except Exception as e:
            calc_err = CalculationError(
                message=f"医療費計算エラー: {e}",
                user_message="治療費・医療関係費の計算中に予期せぬエラーが発生しました。",
                severity=ErrorSeverity.HIGH,
                context={"medical_info": medical_info.to_dict() if hasattr(medical_info, 'to_dict') else str(medical_info), "original_error": str(e)}
            )
            self._error_handler.handle_exception(e, context=calc_err.context)
            return CalculationResult(
                item_name="治療費・医療関係費",
                amount=Decimal('0'),
                calculation_details=f"計算エラー: {str(e)}",
                legal_basis="",
                notes="計算できませんでした"
            )
    
    def calculate_all(self, case_data: CaseData) -> Dict[str, CalculationResult]:
        """全損害項目の計算"""
        results = {}
        try:
            # 各項目の計算
            results['hospitalization'] = self.calculate_hospitalization_compensation(case_data.medical_info)
            results['disability'] = self.calculate_disability_compensation(case_data.medical_info)
            results['lost_income'] = self.calculate_lost_income(case_data.income_info)
            results['future_income_loss'] = self.calculate_future_income_loss(
                case_data.person_info, case_data.medical_info, case_data.income_info
            )
            results['medical_expenses'] = self.calculate_medical_expenses(case_data.medical_info)
            
            # 合計額の計算
            total_before_deduction = sum(result.amount for result in results.values() if result and isinstance(result.amount, Decimal))
            
            # 過失相殺
            fault_percentage = case_data.person_info.fault_percentage
            if not isinstance(fault_percentage, (int, float, Decimal)):
                 raise TypeError(f"過失割合は数値である必要がありますが、{type(fault_percentage)} を受け取りました。")
            fault_ratio = Decimal(str(fault_percentage)) / 100
            total_after_fault = total_before_deduction * (Decimal('1') - fault_ratio)
            total_after_fault = total_after_fault.quantize(Decimal('1'), rounding=ROUND_HALF_UP)
            
            # 弁護士費用の概算
            lawyer_fee = self._estimate_lawyer_fee(total_after_fault)
            
            # 最終支払見込額
            final_amount = total_after_fault + lawyer_fee
            
            # 合計情報
            results['summary'] = CalculationResult(
                item_name="総合計",
                amount=final_amount,
                calculation_details=f"""
損害合計（過失相殺前）: {total_before_deduction:,}円
被害者過失割合: {case_data.person_info.fault_percentage}%
損害合計（過失相殺後）: {total_after_fault:,}円
弁護士費用（概算）: {lawyer_fee:,}円
最終支払見込額: {final_amount:,}円
""".strip(),
                legal_basis="民法第709条、第722条",
                notes="弁護士費用は概算です。実際の費用は事務所の基準により異なります"
            )
            return results

        except CalculationError as e: # 既に処理済みの CalculationError
            self.logger.error(f"計算処理中にエラーが再送されました: {e.message}")
            # 必要に応じて、ここでさらに上位の処理を行うか、そのまま再送
            # ここでは、エラーが発生した項目以外の結果も返すため、エラー情報をsummaryに含める
            error_summary = f"計算エラー: {e.user_message} (詳細はログを確認してください)"
            if 'summary' not in results or not results['summary']:
                 results['summary'] = CalculationResult("総合計", Decimal('0'), error_summary, notes="一部計算に失敗しました")
            else:
                 results['summary'].notes += f"; {error_summary}"
                 results['summary'].amount = Decimal('0') # エラー時は合計0とするか、計算できた分だけにするか
            return results # 計算できた範囲で返す

        except Exception as e:
            calc_err = CalculationError(
                message=f"全体の損害額計算中に予期せぬエラー: {e}",
                user_message="損害賠償額全体の計算中に予期せぬエラーが発生しました。",
                severity=ErrorSeverity.CRITICAL,
                context={"case_data_summary": str(case_data)[:200], "original_error": str(e)}
            )
            self._error_handler.handle_exception(e, context=calc_err.context)
            # 全体計算エラー時は、空の結果またはエラー情報を含む結果を返す
            return {
                'summary': CalculationResult(
                    item_name="総合計", 
                    amount=Decimal('0'), 
                    calculation_details=f"計算エラー: {calc_err.user_message}",
                    notes="計算全体に失敗しました。"
                )
            }

    def _estimate_lawyer_fee(self, economic_benefit: Decimal) -> Decimal:
        """弁護士費用の概算（旧報酬基準参考）"""
        try:
            # 簡易的な計算（着手金+報酬金の概算）
            if economic_benefit <= 3000000:
                fee_rate = Decimal('0.24')  # 8% + 16%
                min_fee = Decimal('200000')
            elif economic_benefit <= 30000000:
                fee_rate = Decimal('0.15')  # 5% + 10%
                min_fee = Decimal('270000')  # 90,000 + 180,000
            else:
                fee_rate = Decimal('0.09')  # 3% + 6%
                min_fee = Decimal('2070000')  # 690,000 + 1,380,000
            
            estimated_fee = economic_benefit * fee_rate
            return max(estimated_fee, min_fee).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
            
        except TypeError as e: # economic_benefit が Decimal でない場合など
            calc_err = CalculationError(
                message=f"弁護士費用計算時の型エラー: {e}",
                user_message="弁護士費用の計算に必要な経済的利益の数値形式が正しくありません。",
                severity=ErrorSeverity.MEDIUM,
                context={"economic_benefit": str(economic_benefit), "original_error": str(e)}
            )
            self._error_handler.handle_exception(e, context=calc_err.context)
            return Decimal('0')
        except Exception as e:
            calc_err = CalculationError(
                message=f"弁護士費用計算エラー: {e}",
                user_message="弁護士費用の概算計算中に予期せぬエラーが発生しました。",
                severity=ErrorSeverity.MEDIUM,
                context={"economic_benefit": str(economic_benefit), "original_error": str(e)}
            )
            self._error_handler.handle_exception(e, context=calc_err.context)
            return Decimal('0')
