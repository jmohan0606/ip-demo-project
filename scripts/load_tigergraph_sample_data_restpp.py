from __future__ import annotations
import csv, json, os
from pathlib import Path
from typing import Any
import requests

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "tigergraph" / "sample_data"
GRAPH = os.getenv("TG_GRAPHNAME") or os.getenv("TIGERGRAPH_GRAPH") or "iperform_insights_coaching_demo"
RESTPP = (os.getenv("TIGERGRAPH_RESTPP_URL") or "").rstrip("/")
TG_HOST = (os.getenv("TG_HOST") or os.getenv("TIGERGRAPH_HOST") or "http://127.0.0.1").rstrip("/")
TG_RESTPP_PORT = os.getenv("TG_RESTPP_PORT", "9000")
if not RESTPP:
    RESTPP = TG_HOST if ":" in TG_HOST.split("//", 1)[-1] else f"{TG_HOST}:{TG_RESTPP_PORT}"
TOKEN = os.getenv("TG_JWT_TOKEN") or os.getenv("TG_API_TOKEN") or os.getenv("TIGERGRAPH_TOKEN") or ""
HEADERS = {"Content-Type": "application/json"}
if TOKEN: HEADERS["Authorization"] = f"Bearer {TOKEN}"

def read_csv(name: str):
    with (DATA_DIR/name).open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def coerce(v):
    s = str(v).strip()
    if s.lower() in {"true","false"}: return s.lower()=="true"
    try: return float(s) if "." in s else int(s)
    except Exception: return s

def post_graph(payload, label):
    url = f"{RESTPP}/graph/{GRAPH}"
    r = requests.post(url, headers=HEADERS, json=payload, timeout=30)
    try: data = r.json()
    except Exception: data = {"text": r.text}
    result = {"label": label, "http_status": r.status_code, "ok": r.ok, "response": data}
    if not r.ok: raise RuntimeError(json.dumps(result, indent=2))
    return result

def upsert_vertices(vtype, id_field, rows, exclude=set()):
    return post_graph({"vertices": {vtype: {row[id_field]: {k: coerce(v) for k,v in row.items() if k != id_field and k not in exclude} for row in rows}}}, f"vertices:{vtype}:{len(rows)}")

def upsert_edges(etype, from_type, from_field, to_type, to_field, rows):
    edges = {}; count=0
    for row in rows:
        src, tgt = row.get(from_field), row.get(to_field)
        if not src or not tgt: continue
        edges.setdefault(from_type, {}).setdefault(src, {}).setdefault(etype, {}).setdefault(to_type, {})[tgt] = {}
        count += 1
    if count == 0: return {"label": f"edges:{etype}", "ok": True, "count": 0}
    return post_graph({"edges": edges}, f"edges:{etype}:{count}")

def query(name, params):
    r = requests.get(f"{RESTPP}/query/{GRAPH}/{name}", headers=HEADERS, params=params, timeout=30)
    try: data = r.json()
    except Exception: data = {"text": r.text}
    return {"query": name, "http_status": r.status_code, "ok": r.ok, "response": data}

def main():
    report = {"graph": GRAPH, "restpp": RESTPP, "steps": []}
    firm=read_csv("phx_dm_firm.csv"); div=read_csv("phx_dm_division.csv"); reg=read_csv("phx_dm_region.csv")
    market=read_csv("phx_dm_market.csv"); adv=read_csv("phx_dm_advisor.csv"); hh=read_csv("phx_dm_household.csv")
    acc=read_csv("phx_dm_account.csv"); prod=read_csv("phx_dm_product.csv"); txn=read_csv("phx_dm_transaction.csv")
    for args in [
        ("phx_dm_firm","firm_id",firm,set()), ("phx_dm_division","division_id",div,{"firm_id"}),
        ("phx_dm_region","region_id",reg,{"division_id"}), ("phx_dm_market","market_id",market,{"region_id"}),
        ("phx_dm_advisor","advisor_id",adv,{"market_id"}), ("phx_dm_household","household_id",hh,{"advisor_id"}),
        ("phx_dm_product","product_id",prod,set()), ("phx_dm_account","account_id",acc,{"household_id","product_id"}),
        ("phx_dm_revenue_transaction","transaction_id",txn,{"account_id"}),
    ]: report["steps"].append(upsert_vertices(*args))
    for args in [
        ("phx_dm_has_division","phx_dm_firm","firm_id","phx_dm_division","division_id",div),
        ("phx_dm_has_region","phx_dm_division","division_id","phx_dm_region","region_id",reg),
        ("phx_dm_has_market","phx_dm_region","region_id","phx_dm_market","market_id",market),
        ("phx_dm_has_advisor","phx_dm_market","market_id","phx_dm_advisor","advisor_id",adv),
        ("phx_dm_serves_household","phx_dm_advisor","advisor_id","phx_dm_household","household_id",hh),
        ("phx_dm_owns_account","phx_dm_household","household_id","phx_dm_account","account_id",acc),
        ("phx_dm_holds_product","phx_dm_account","account_id","phx_dm_product","product_id",acc),
        ("phx_dm_generated_revenue","phx_dm_account","account_id","phx_dm_revenue_transaction","transaction_id",txn),
    ]: report["steps"].append(upsert_edges(*args))
    report["validation_queries"] = [query("phx_dm_get_advisor_context", {"advisor_id":"ADV0001"}), query("phx_dm_get_revenue_summary", {"scope_type":"Advisor","scope_id":"ADV0001","period":"YTD"})]
    out = ROOT/"docs/restpp_sample_data_load_report.json"; out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
if __name__ == "__main__": main()
