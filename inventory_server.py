"""MCP Server：假库存柜台。课上打开这个文件，指「Server」。"""

from __future__ import annotations

import json
from pathlib import Path

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

DATA_PATH = Path(__file__).resolve().parent / "data" / "inventory.json"

inventory_server = MCPServer(
    name="inventory-server",
    title="Fake inventory counter",
    instructions="Look up fake stock for heavy machinery. This is not a real warehouse.",
)


def _load_table() -> dict:
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


@inventory_server.tool(
    name="check_inventory",
    title="Check inventory",
    description="按设备型号查询当前库存数量。",
)
def check_inventory(model: str) -> dict:
    model_id = (model or "").strip()
    if not model_id:
        raise ToolError("model is required")
    if model_id.upper() == "FAIL":
        raise ToolError("inventory service unavailable")

    table = _load_table()
    item = table.get(model_id.upper()) or table.get(model_id)
    if not item:
        return {
            "model": model_id,
            "in_stock": False,
            "qty": 0,
            "note": "this model is not in the catalog",
        }
    qty = int(item.get("qty") or 0)
    return {
        "model": model_id.upper(),
        "in_stock": qty > 0,
        "qty": qty,
        "note": item.get("note") or "",
    }
