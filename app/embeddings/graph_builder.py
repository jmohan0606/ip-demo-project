from __future__ import annotations

import csv
from pathlib import Path
import networkx as nx


class DemoGraphBuilder:
    def __init__(self) -> None:
        self.sample_data_dir = Path("tigergraph/sample_data")

    def _read(self, file_name: str) -> list[dict]:
        with (self.sample_data_dir / file_name).open(encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def build_graph(self) -> nx.Graph:
        g = nx.Graph()

        advisors = self._read("phx_dm_advisor.csv")
        households = self._read("phx_dm_household.csv")
        accounts = self._read("phx_dm_account.csv")
        advisor_household = self._read("edges_phx_dm_advisor_serves_household.csv")
        household_account = self._read("edges_phx_dm_household_has_account.csv")
        transactions = self._read("phx_dm_transaction.csv")

        for a in advisors:
            g.add_node(f"Advisor:{a['advisor_id']}", entity_type="Advisor", entity_id=a["advisor_id"], agp=a.get("agp_enrolled") == "true")
        for h in households:
            g.add_node(f"Household:{h['household_id']}", entity_type="Household", entity_id=h["household_id"], segment=h.get("segment"), risk_profile=h.get("risk_profile"))
        for a in accounts:
            g.add_node(f"Account:{a['account_id']}", entity_type="Account", entity_id=a["account_id"], managed=a.get("managed_flag") == "true")

        for e in advisor_household:
            g.add_edge(f"Advisor:{e['from_id']}", f"Household:{e['to_id']}", relation="serves")
        for e in household_account:
            g.add_edge(f"Household:{e['from_id']}", f"Account:{e['to_id']}", relation="has_account")

        # sample product/account links via transactions for performance
        for t in transactions[:150000]:
            product_node = f"Product:{t['product_id']}"
            g.add_node(product_node, entity_type="Product", entity_id=t["product_id"])
            g.add_edge(f"Account:{t['account_id']}", product_node, relation="transacted_product")

        return g
