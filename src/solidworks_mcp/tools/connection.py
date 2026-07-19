"""连接管理工具 (MCP 1.x API)"""

from ..sw_connection import connection


def _connect_solidworks() -> str:
    result = connection.connect()
    if result["success"]:
        return f"✅ {result['message']}，版本: {result['version']}"
    return f"❌ {result['message']}"


CONNECTION_TOOLS = [
    {
        "name": "connect_solidworks",
        "description": "连接到正在运行的 SOLIDWORKS 实例。在执行任何其他操作前必须先调用此工具。",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
        "handler": _connect_solidworks,
    },
]
