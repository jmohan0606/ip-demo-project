from __future__ import annotations

import asyncio
import os


async def main() -> None:
    """Run tigergraph-mcp with an existing AsyncTigerGraphConnection."""
    from pyTigerGraph import AsyncTigerGraphConnection
    from tigergraph_mcp import ConnectionManager, serve

    async with AsyncTigerGraphConnection(
        host=os.getenv("TG_HOST", "http://127.0.0.1"),
        graphname=os.getenv("TG_GRAPHNAME", "iPerformInsights"),
        username=os.getenv("TG_USERNAME", "tigergraph"),
        password=os.getenv("TG_PASSWORD", "tigergraph"),
        apiToken=os.getenv("TG_API_TOKEN") or None,
    ) as conn:
        ConnectionManager.set_default_connection(conn)
        await serve()


if __name__ == "__main__":
    asyncio.run(main())
