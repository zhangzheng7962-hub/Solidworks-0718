"""文档操作工具 (comtypes)"""

from ..sw_connection import connection


def _new_part() -> str:
    sw = connection.app
    try:
        doc = sw.INewPart()
        if doc:
            return "✅ 已创建新零件文档"
        return "❌ 创建零件失败"
    except Exception as e:
        return f"❌ 创建零件失败: {str(e)}"


DOCUMENT_TOOLS = [
    {
        "name": "new_part",
        "description": "新建零件文档",
        "inputSchema": {"type": "object", "properties": {}},
        "handler": _new_part,
    },
]
