"""Read-only analytics against the approved synthetic Supplier Risk DSS SQLite schema."""
import sqlite3
from pathlib import Path
import pandas as pd

SCENARIOS = (3, 5, 7)

def connect(db_path):
    p = Path(db_path).expanduser().resolve()
    if not p.is_file():
        raise FileNotFoundError(f"Database not found: {p}")
    con = sqlite3.connect(f"file:{p.as_posix()}?mode=ro", uri=True)
    con.execute("PRAGMA query_only=ON")
    return con

def review_dates(db_path):
    with connect(db_path) as con:
        return [r[0] for r in con.execute("SELECT DISTINCT Review_Date FROM DSS_Assessments ORDER BY Review_Date DESC")]

def review_queue(db_path, date):
    # Historical eligibility is established by the precomputed point-in-time assessments.
    sql = """SELECT a.PO_ID, a.Review_Date, p.Promised_Delivery_Date, p.PO_Date,
           p.Supplier_ID, s.Supplier_Name, p.Item_ID, i.Item_Name, i.Item_Criticality,
           p.Location_ID, l.Location_Name, p.Order_Quantity,
           a.Management_Review_Flag, a.Priority_Reason, a.Predicted_Late_Probability,
           MAX(a.Incremental_Shortage_Units) AS Max_Incremental_Shortage_Units,
           MAX(a.Incremental_Stockout_Days) AS Max_Incremental_Stockout_Days,
           MAX(a.Estimated_Emergency_Procurement_Cost) AS Max_Emergency_Premium
           FROM DSS_Assessments a JOIN Purchase_Orders p ON p.PO_ID=a.PO_ID
           JOIN Suppliers s ON s.Supplier_ID=p.Supplier_ID
           JOIN Items i ON i.Item_ID=p.Item_ID
           JOIN Locations l ON l.Location_ID=p.Location_ID
           WHERE a.Review_Date=?
           GROUP BY a.PO_ID, a.Review_Date
           ORDER BY (a.Management_Review_Flag IS NULL), a.Management_Review_Flag DESC,
                    Max_Incremental_Shortage_Units DESC, p.Promised_Delivery_Date"""
    with connect(db_path) as con:
        return pd.read_sql_query(sql, con, params=(date,))

def po_details(db_path, po_id):
    with connect(db_path) as con:
        df = pd.read_sql_query("""SELECT p.*, s.Supplier_Name, s.Supplier_Type,
          i.Item_Name, i.Item_Category, i.Item_Criticality,
          i.Patient_Care_Operational_Consequence, i.Suitable_Alternative_Available,
          i.Time_To_Replace_Days, l.Location_Name FROM Purchase_Orders p
          JOIN Suppliers s ON p.Supplier_ID=s.Supplier_ID
          JOIN Items i ON p.Item_ID=i.Item_ID
          JOIN Locations l ON p.Location_ID=l.Location_ID WHERE p.PO_ID=?""",con,params=(po_id,))
    return df.iloc[0].to_dict() if len(df) else None

def scenario_rows(db_path, po_id, date):
    with connect(db_path) as con:
        return pd.read_sql_query("""SELECT Delay_Scenario_Days, Baseline_Stockout_Days,
          Delayed_Stockout_Days, Incremental_Stockout_Days,
          Baseline_Unmet_Demand_Units, Delayed_Unmet_Demand_Units,
          Incremental_Shortage_Units, Estimated_Emergency_Procurement_Cost,
          Management_Review_Flag, Priority_Reason, Suggested_Mitigations,
          Predicted_Late_Probability FROM DSS_Assessments
          WHERE PO_ID=? AND Review_Date=? ORDER BY Delay_Scenario_Days""",con,params=(po_id,date))

def supplier_history(db_path, supplier_id, date):
    # Only deliveries actually known at review date can enter historical metrics.
    with connect(db_path) as con:
        r = con.execute("""SELECT COUNT(*), SUM(CASE WHEN Actual_Delivery_Date>Promised_Delivery_Date THEN 1 ELSE 0 END)
          FROM Purchase_Orders WHERE Supplier_ID=? AND Actual_Delivery_Date IS NOT NULL
          AND Actual_Delivery_Date<=? AND Actual_Delivery_Date>date(?, '-90 days')""",
          (int(supplier_id),date,date)).fetchone()
    n, late = r[0] or 0, r[1] or 0
    return {"completed_last_90_days":n, "late_last_90_days":late,
            "late_rate_last_90_days": late/n if n else None}

def inventory_demand(db_path,item_id,location_id,date):
    with connect(db_path) as con:
        inv=con.execute("""SELECT Available_Inventory,Safety_Stock_Level FROM Inventory_Snapshots
           WHERE Item_ID=? AND Location_ID=? AND Snapshot_Date=?""",(int(item_id),int(location_id),date)).fetchone()
        demand=con.execute("""SELECT COUNT(*),AVG(Demand_Units),SUM(Demand_Units) FROM Demand_Observations
          WHERE Item_ID=? AND Location_ID=? AND Demand_Date BETWEEN date(?, '-29 days') AND ?""",
          (int(item_id),int(location_id),date,date)).fetchone()
    return {"inventory": inv[0] if inv else None, "safety_stock": inv[1] if inv else None,
            "demand_days":demand[0],"mean_daily_demand":demand[1] if demand[0]==30 else None}

def screening_check(rows, criticality):
    """Independent display-level screening consistency check, not replacement for validator."""
    if len(rows)!=3 or set(rows.Delay_Scenario_Days)!={3,5,7}:
        return None
    if rows['Incremental_Shortage_Units'].isna().any() or rows['Baseline_Unmet_Demand_Units'].isna().any():
        return None
    mr01=bool((rows.Incremental_Shortage_Units>0).any())
    mr02=bool(criticality=='High' and (rows.Baseline_Unmet_Demand_Units>0).any())
    return mr01 or mr02
