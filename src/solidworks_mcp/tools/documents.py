"""文档操作工具 (comtypes)"""

import os
from ..sw_connection import connection


def _get_active_document() -> str:
    status = connection.get_status()
    if not status["connected"]:
        return "❌ 未连接到 SOLIDWORKS"
    model = connection.get_model()
    if model is None:
        return "📭 当前没有打开的文档"
    name = model.GetTitle()
    doc_type = model.GetType()
    path = model.GetPathName()
    type_names = {1: "零件", 2: "装配体", 3: "工程图"}
    return (f"📄 当前文档信息:\n"
            f"  名称: {name}\n"
            f"  类型: {type_names.get(doc_type, '未知')}\n"
            f"  路径: {path if path else '未保存'}")


def _new_part() -> str:
    sw = connection.app
    try:
        doc = sw.INewPart()
        if doc:
            return "✅ 已创建新零件文档"
        return "❌ 创建零件失败"
    except Exception as e:
        return f"❌ 创建零件失败: {str(e)}"


def _save_document(save_path: str = "") -> str:
    model = connection.get_model()
    if model is None:
        return "❌ 没有打开的文档"
    try:
        if save_path:
            dir_path = os.path.dirname(save_path)
            if dir_path and not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)
            # SaveAs3 返回 HRESULT (int), 0 = S_OK = 成功
            hr = model.SaveAs3(save_path, 0, 0)
            if hr == 0:
                return f"✅ 文档已保存到: {save_path}"
            return f"❌ 保存失败 (HRESULT: 0x{hr:08X})"
        else:
            # Save3 返回 HRESULT (int), 0 = S_OK = 成功
            hr = model.Save3(1, 0, None)
            if hr == 0:
                path = model.GetPathName()
                return f"✅ 文档已保存: {path}"
            return f"❌ 保存失败 (HRESULT: 0x{hr:08X})"
    except Exception as e:
        return f"❌ 保存失败: {str(e)}"


DOCUMENT_TOOLS = [
    {
        "name": "get_active_document",
        "description": "获取当前活跃文档信息（名称、类型、路径）",
        "inputSchema": {"type": "object", "properties": {}},
        "handler": _get_active_document,
    },
    {
        "name": "new_part",
        "description": "新建零件文档",
        "inputSchema": {"type": "object", "properties": {}},
        "handler": _new_part,
    },
    {
        "name": "save_document",
        "description": "保存当前文档",
        "inputSchema": {
            "type": "object",
            "properties": {
                "save_path": {"type": "string", "description": "保存路径(可选)", "default": ""},
            },
        },
        "handler": _save_document,
    },
]
