from __future__ import annotations

import csv
import sqlite3
from pathlib import Path


class WealthScenarioAuditor:
    REQUIRED_FILES = {
        "transactions": "tigergraph/sample_data/phx_dm_transaction.csv",
        "accounts": "tigergraph/sample_data/phx_dm_account.csv",
        "households": "tigergraph/sample_data/phx_dm_household.csv",
        "monthly_aum": "tigergraph/sample_data/phx_dm_monthly_aum.csv",
        "monthly_product_revenue": "tigergraph/sample_data/phx_dm_monthly_product_revenue.csv",
        "monthly_eligibility": "tigergraph/sample_data/phx_dm_monthly_eligibility.csv",
        "net_cash_flow": "tigergraph/sample_data/phx_dm_net_cash_flow.csv",
        "net_new_money": "tigergraph/sample_data/phx_dm_net_new_money.csv",
    }

    REQUIRED_TRANSACTION_COLUMNS = [
        "trade_date", "settlement_date", "buy_sell_flag", "quantity",
        "principal_amount", "revenue_amount", "net_new_money_amount",
        "net_cash_flow_amount", "product_id", "account_id", "advisor_id",
    ]

    def __init__(self, root: str = ".") -> None:
        self.root = Path(root)

    def _read(self, rel: str) -> list[dict]:
        path = self.root / rel
        if not path.exists():
            return []
        with path.open(encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def audit(self) -> dict:
        file_results = {}
        for name, rel in self.REQUIRED_FILES.items():
            path = self.root / rel
            rows = self._read(rel)
            file_results[name] = {
                "path": rel,
                "exists": path.exists(),
                "row_count": len(rows),
            }

        txns = self._read(self.REQUIRED_FILES["transactions"])
        txn_columns = set(txns[0].keys()) if txns else set()
        missing_txn_cols = [c for c in self.REQUIRED_TRANSACTION_COLUMNS if c not in txn_columns]

        products = self._read("tigergraph/sample_data/phx_dm_product.csv")
        product_map = {p.get("product_id"): p for p in products}
        product_categories = sorted({(t.get("product_category") or product_map.get(t.get("product_id"), {}).get("major_category") or product_map.get(t.get("product_id"), {}).get("product_category_id") or "") for t in txns if (t.get("product_category") or product_map.get(t.get("product_id"), {}).get("major_category") or product_map.get(t.get("product_id"), {}).get("product_category_id") or "")})
        product_subcategories = sorted({(t.get("product_subcategory") or product_map.get(t.get("product_id"), {}).get("subcategory") or product_map.get(t.get("product_id"), {}).get("product_subcategory_id") or "") for t in txns if (t.get("product_subcategory") or product_map.get(t.get("product_id"), {}).get("subcategory") or product_map.get(t.get("product_id"), {}).get("product_subcategory_id") or "")})
        buy_sell_flags = sorted({t.get("buy_sell_flag", "") for t in txns if t.get("buy_sell_flag")})

        db_status = self._sqlite_scenario_status()

        failures = []
        for name, result in file_results.items():
            if not result["exists"] or result["row_count"] == 0:
                failures.append(f"{name} missing_or_empty")
        if missing_txn_cols:
            failures.append(f"transaction_columns_missing={missing_txn_cols}")
        if len(product_categories) < 3:
            failures.append("insufficient_product_category_variation")
        if len(product_subcategories) < 5:
            failures.append("insufficient_product_subcategory_variation")
        if len(buy_sell_flags) < 2:
            failures.append("insufficient_buy_sell_variation")
        if db_status["advisor_feature_vectors"] < 10:
            failures.append("insufficient_preloaded_advisor_features")

        return {
            "status": "passed" if not failures else "failed",
            "failures": failures,
            "files": file_results,
            "transaction_columns_missing": missing_txn_cols,
            "product_category_count": len(product_categories),
            "product_subcategory_count": len(product_subcategories),
            "buy_sell_flags": buy_sell_flags,
            "sqlite_status": db_status,
        }

    def _sqlite_scenario_status(self) -> dict:
        db = self.root / "data/sqlite/iperform.db"
        if not db.exists():
            return {"db_exists": False, "advisor_feature_vectors": 0, "recommendations": 0}
        conn = sqlite3.connect(db)
        try:
            return {
                "db_exists": True,
                "advisor_feature_vectors": conn.execute(
                    "SELECT COUNT(*) FROM phx_dm_feature_vector WHERE entity_type='Advisor'"
                ).fetchone()[0],
                "recommendations": conn.execute(
                    "SELECT COUNT(*) FROM phx_dm_local_recommendation"
                ).fetchone()[0],
                "opportunities": conn.execute(
                    "SELECT COUNT(*) FROM phx_dm_local_opportunity"
                ).fetchone()[0],
            }
        finally:
            conn.close()
