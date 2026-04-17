"""Armature MCP Server -- stdio transport entry point.

Usage:
    python -m armature.mcp.server

Reads JSON-RPC messages from stdin, dispatches to tool handlers,
writes responses to stdout. Follows the Model Context Protocol spec.
"""

from __future__ import annotations

import json
import sys

from armature.mcp.server import get_tool_definitions, handle_tool_call


def _read_message() -> dict | None:
    """Read a single JSON-RPC message from stdin."""
    line = sys.stdin.readline()
    if not line:
        return None
    try:
        return json.loads(line.strip())
    except json.JSONDecodeError:
        return None


def _write_message(msg: dict) -> None:
    """Write a JSON-RPC response to stdout."""
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()


def _handle_request(request: dict) -> dict:
    """Route a JSON-RPC request to the appropriate handler."""
    method = request.get("method", "")
    req_id = request.get("id")
    params = request.get("params", {})

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {
                    "name": "armature",
                    "version": "0.1.0",
                },
                "capabilities": {
                    "tools": {"listChanged": False},
                },
            },
        }

    if method == "notifications/initialized":
        return {}

    if method == "tools/list":
        tools = get_tool_definitions()
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": tools},
        }

    if method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        try:
            result = handle_tool_call(tool_name, arguments)
        except Exception as e:
            result = {"error": str(e)}

        is_error = "error" in result
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result, indent=2),
                    }
                ],
                "isError": is_error,
            },
        }

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {
            "code": -32601,
            "message": f"Method not found: {method}",
        },
    }


def main() -> None:
    """Run the MCP server stdio transport loop."""
    while True:
        request = _read_message()
        if request is None:
            break

        response = _handle_request(request)
        if response:
            _write_message(response)


if __name__ == "__main__":
    main()
