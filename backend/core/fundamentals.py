from typing import Dict, Any, List
import datetime as dt
import pandas as pd
from .tushare_client import (
    fina_indicator, income, balancesheet, cashflow,
    daily_basic, forecast, express,
    # 5000积分VIP接口
    income_vip, balancesheet_vip, cashflow_vip
)


def fetch_fundamentals(ts_code: str, force: bool = False) -> Dict[str, Any]:
    out: Dict[str, Any] = {}

    # 获取每日指标（估值）
    today = dt.date.today().strftime("%Y%m%d")
    db = daily_basic(ts_code=ts_code, force=force)
    if not db.empty:
        # 按日期排序获取最新数据
        db = db.sort_values("trade_date", ascending=False)
    
    if not db.empty:
        db = db.sort_values("trade_date", ascending=False).reset_index(drop=True)
        latest_db = db.iloc[0].to_dict()
        valuation_keys = [
            "trade_date", "pe", "pe_ttm", "pb", "ps", "ps_ttm", 
            "dv_ratio", "dv_ttm", "total_mv", "circ_mv", 
            "turnover_rate", "turnover_rate_f", "volume_ratio"
        ]
        out["valuation"] = {k: latest_db.get(k) for k in valuation_keys if latest_db.get(k) is not None}
    
    # 获取业绩预告
    fc = forecast(ts_code, force=force)
    if not fc.empty:
        fc = fc.sort_values("ann_date", ascending=False).reset_index(drop=True)
        latest_fc = fc.iloc[0].to_dict()
        out["forecast"] = {
            "ann_date": latest_fc.get("ann_date"),
            "end_date": latest_fc.get("end_date"),
            "type": latest_fc.get("type"),
            "p_change_min": latest_fc.get("p_change_min"),
            "p_change_max": latest_fc.get("p_change_max"),
            "net_profit_min": latest_fc.get("net_profit_min"),
            "net_profit_max": latest_fc.get("net_profit_max"),
            "summary": latest_fc.get("summary"),
        }
    
    # 获取业绩快报
    exp = express(ts_code, force=force)
    if not exp.empty:
        exp = exp.sort_values("ann_date", ascending=False).reset_index(drop=True)
        latest_exp = exp.iloc[0].to_dict()
        out["express"] = {
            "ann_date": latest_exp.get("ann_date"),
            "end_date": latest_exp.get("end_date"),
            "revenue": latest_exp.get("revenue"),
            "operate_profit": latest_exp.get("operate_profit"),
            "total_profit": latest_exp.get("total_profit"),
            "n_income": latest_exp.get("n_income"),
            "eps": latest_exp.get("eps"),
        }

    fi = fina_indicator(ts_code, force=force)
    if not fi.empty:
        fi = fi.sort_values("end_date", ascending=False).reset_index(drop=True)
        latest = fi.iloc[0].to_dict()
        keep = [
            "end_date",
            "roe",
            "roa",
            "grossprofit_margin",
            "netprofit_margin",
            "asset_turn",
            "op_yoy",
            "or_yoy",
            "profit_dedt",
            "q_dtprofit",
            "q_profit_yoy",
            "q_gr_yoy",
            "current_ratio",  # 新增流动比率
            "quick_ratio",    # 新增速动比率
            "debt_to_eqt",    # 新增产权比率
        ]
        out["fina_indicator_latest"] = {k: latest.get(k) for k in keep if latest.get(k) is not None}

    # 尝试使用5000积分VIP接口获取更详细的利润表数据
    try:
        inc = income_vip(ts_code=ts_code, force=force)
        print(f"[基本面] 使用VIP接口获取利润表数据: {len(inc) if not inc.empty else 0}条记录")
    except Exception as e:
        print(f"[基本面] VIP接口失败，使用普通接口: {e}")
        inc = income(ts_code, force=force)

    if not inc.empty:
        inc = inc.sort_values("end_date", ascending=False)
        cols = [
            "end_date", "revenue", "n_income", "n_income_attr_p",
            "total_profit", "operate_profit", "basic_eps", "diluted_eps",
            # VIP接口额外字段
            "total_revenue", "grossprofit_margin", "sell_exp", "admin_exp", "fin_exp"
        ]
        # 只选择存在的列
        available_cols = [col for col in cols if col in inc.columns]
        out["income_recent"] = inc[available_cols].head(6).to_dict(orient="records")

    # 尝试使用5000积分VIP接口获取资产负债表数据
    try:
        bal = balancesheet_vip(ts_code=ts_code, force=force)
        print(f"[基本面] 使用VIP接口获取资产负债表: {len(bal) if not bal.empty else 0}条记录")
    except Exception as e:
        print(f"[基本面] 资产负债表VIP接口失败，使用普通接口: {e}")
        bal = balancesheet(ts_code, force=force)

    if not bal.empty:
        bal = bal.sort_values("end_date", ascending=False)
        rows: List[Dict[str, Any]] = []
        for _, r in bal.iterrows():
            ta = r.get("total_assets")
            tl = r.get("total_liab")
            lev = (
                float(tl) / float(ta)
                if pd.notna(ta) and pd.notna(tl) and float(ta) != 0
                else None
            )
            rows.append(
                {
                    "end_date": r.get("end_date"),
                    "total_assets": ta,
                    "total_liab": tl,
                    "debt_ratio": lev,
                    # VIP接口额外数据
                    "money_cap": r.get("money_cap"),  # 货币资金
                    "inventories": r.get("inventories"),  # 存货
                    "fix_assets": r.get("fix_assets"),  # 固定资产
                    "goodwill": r.get("goodwill"),  # 商誉
                }
            )
        out["balance_recent"] = rows

    # 尝试使用5000积分VIP接口获取现金流量表数据
    try:
        cf = cashflow_vip(ts_code=ts_code, force=force)
        print(f"[基本面] 使用VIP接口获取现金流量表: {len(cf) if not cf.empty else 0}条记录")
    except Exception as e:
        print(f"[基本面] 现金流量表VIP接口失败，使用普通接口: {e}")
        cf = cashflow(ts_code, force=force)

    if not cf.empty:
        cf = cf.sort_values("end_date", ascending=False)
        rows: List[Dict[str, Any]] = []
        for _, r in cf.iterrows():
            cfo = r.get("n_cashflow_act")
            capex = r.get("procure_fixed_assets")
            fcf = (
                float(cfo) - float(capex) if pd.notna(cfo) and pd.notna(capex) else None
            )
            rows.append(
                {
                    "end_date": r.get("end_date"),
                    "n_cashflow_act": cfo,
                    "procure_fixed_assets": capex,
                    "rough_fcf": fcf,
                    # VIP接口额外数据
                    "c_fr_sale_sg": r.get("c_fr_sale_sg"),  # 销售商品、提供劳务收到的现金
                    "c_paid_goods_s": r.get("c_paid_goods_s"),  # 购买商品、接受劳务支付的现金
                    "c_paid_to_for_empl": r.get("c_paid_to_for_empl"),  # 支付给职工以及为职工支付的现金
                }
            )
        out["cashflow_recent"] = rows

    return out


