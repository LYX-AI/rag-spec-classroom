"""MCP Client：问柜台有什么工具，再按名字调用。课上打开这个文件，指「Client」。"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from mcp.client import Client

from inventory_server import inventory_server


def _run(coro):
    return asyncio.run(coro)


def _schema_to_dict(schema) -> dict[str, Any] | None:
    if schema is None:
        return None
    if hasattr(schema, "model_dump"):
        return schema.model_dump(by_alias=True, exclude_none=True)
    if isinstance(schema, dict):
        return schema
    return None


def _parameters_from_schema(schema) -> list[dict[str, Any]]:
    dumped = _schema_to_dict(schema) or {}
    properties = dumped.get("properties") or {}
    required = set(dumped.get("required") or [])
    parameters = []
    for name, spec in properties.items():
        spec = spec or {}
        parameters.append(
            {
                "name": name,
                "type": spec.get("type") or "string",
                "required": name in required,
            }
        )
    return parameters


def _tool_to_dict(tool) -> dict[str, Any]:
    schema = getattr(tool, "input_schema", None)
    return {
        "name": tool.name,
        "title": getattr(tool, "title", None) or tool.name,
        "description": tool.description or "",
        "parameters": _parameters_from_schema(schema),
    }


def _parse_tool_payload(result) -> dict[str, Any]:
    texts = []
    for block in result.content or []:
        text = getattr(block, "text", None)
        if text:
            texts.append(text)
    raw_text = "\n".join(texts) if texts else ""
    data = result.structured_content
    if isinstance(data, dict) and "result" in data and len(data) == 1:
        data = data.get("result")
    if not isinstance(data, dict):
        try:
            data = json.loads(raw_text) if raw_text else {}
        except json.JSONDecodeError:
            data = {}
    if not isinstance(data, dict):
        data = {}
    is_error = bool(result.is_error)
    return {
        "ok": not is_error,
        "message": raw_text if is_error else "",
        "model": data.get("model") or "",
        "in_stock": data.get("in_stock"),
        "qty": data.get("qty"),
        "note": data.get("note") or "",
    }


async def _list_tools() -> list[dict[str, Any]]:
    async with Client(inventory_server) as client:
        result = await client.list_tools()
        return [_tool_to_dict(tool) for tool in result.tools]


async def _call_check_inventory(model: str) -> dict[str, Any]:
    async with Client(inventory_server) as client:
        result = await client.call_tool("check_inventory", {"model": model})
        return _parse_tool_payload(result)


def list_inventory_tools() -> list[dict[str, Any]]:
    return _run(_list_tools())


def call_check_inventory(model: str) -> dict[str, Any]:
    return _run(_call_check_inventory(model))
