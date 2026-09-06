"""SOLIDWORKS MCP 工具 — 统一注册表 (MCP 1.x API)

精简版 — 10 个基础建模工具（连接 + 草绘 + 拉伸 + 切除，足以构建大多数棱柱类零件）:
    连接: connect_solidworks
    文档: new_part
    草图: create_sketch_on_plane / sketch_rectangle / sketch_circle /
          sketch_line / sketch_polygon / sketch_slot
    特征: extrude / cut_extrude
"""

from .connection import CONNECTION_TOOLS
from .documents import DOCUMENT_TOOLS

from .sketch_tools import (
    _create_sketch_on_plane,
    _sketch_rectangle,
    _sketch_circle,
    _sketch_line,
    _sketch_polygon,
    _sketch_slot,
)
from .feature_tools import (
    _extrude,
    _cut_extrude,
)


# ==================== 工具注册 ====================

FEATURE_TOOLS = [
    {
        "name": "create_sketch_on_plane",
        "description": "在指定基准面上创建新草图。画任何图形前必须先调用此工具",
        "inputSchema": {
            "type": "object",
            "properties": {
                "plane": {
                    "type": "string",
                    "description": "基准面: front(前视), top(上视), right(右视)",
                    "default": "front",
                },
            },
        },
        "handler": _create_sketch_on_plane,
    },
    {
        "name": "sketch_rectangle",
        "description": "在当前草图中绘制矩形(对角点)，单位: 毫米",
        "inputSchema": {
            "type": "object",
            "properties": {
                "x1": {"type": "number", "description": "左下 X (mm)"},
                "y1": {"type": "number", "description": "左下 Y (mm)"},
                "x2": {"type": "number", "description": "右上 X (mm)"},
                "y2": {"type": "number", "description": "右上 Y (mm)"},
            },
            "required": ["x1", "y1", "x2", "y2"],
        },
        "handler": _sketch_rectangle,
    },
    {
        "name": "sketch_circle",
        "description": "在当前草图中绘制圆，单位: 毫米",
        "inputSchema": {
            "type": "object",
            "properties": {
                "center_x": {"type": "number", "description": "圆心 X (mm)"},
                "center_y": {"type": "number", "description": "圆心 Y (mm)"},
                "radius": {"type": "number", "description": "半径 (mm)"},
            },
            "required": ["center_x", "center_y", "radius"],
        },
        "handler": _sketch_circle,
    },
    {
        "name": "sketch_line",
        "description": "在当前草图中绘制直线，单位: 毫米",
        "inputSchema": {
            "type": "object",
            "properties": {
                "x1": {"type": "number", "description": "起点 X (mm)"},
                "y1": {"type": "number", "description": "起点 Y (mm)"},
                "x2": {"type": "number", "description": "终点 X (mm)"},
                "y2": {"type": "number", "description": "终点 Y (mm)"},
            },
            "required": ["x1", "y1", "x2", "y2"],
        },
        "handler": _sketch_line,
    },
    {
        "name": "sketch_polygon",
        "description": "在当前草图中绘制正多边形，单位: 毫米",
        "inputSchema": {
            "type": "object",
            "properties": {
                "center_x": {"type": "number", "description": "中心 X (mm)"},
                "center_y": {"type": "number", "description": "中心 Y (mm)"},
                "radius": {"type": "number", "description": "外接圆半径 (mm)"},
                "sides": {"type": "integer", "description": "边数", "default": 6},
            },
            "required": ["center_x", "center_y", "radius"],
        },
        "handler": _sketch_polygon,
    },
    {
        "name": "sketch_slot",
        "description": "在当前草图中绘制跑道形/腰形孔轮廓（两条直线+两个半圆弧，自动闭合），单位: 毫米。angle=0水平，angle=90垂直",
        "inputSchema": {
            "type": "object",
            "properties": {
                "center_x": {"type": "number", "description": "中心 X (mm)"},
                "center_y": {"type": "number", "description": "中心 Y (mm)"},
                "length": {"type": "number", "description": "总长度，含两端圆弧 (mm)，必须 > width"},
                "width": {"type": "number", "description": "宽度 = 圆弧直径 (mm)"},
                "angle": {"type": "number", "description": "绕中心旋转角度(度), 0=水平", "default": 0},
            },
            "required": ["center_x", "center_y", "length", "width"],
        },
        "handler": _sketch_slot,
    },
    {
        "name": "extrude",
        "description": "对当前草图执行拉伸凸台，单位: 毫米。支持等距起始(start_offset>0)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "depth": {"type": "number", "description": "拉伸深度 (mm)"},
                "reverse": {"type": "boolean", "description": "是否反向", "default": False},
                "both_dirs": {"type": "boolean", "description": "双向拉伸", "default": False},
                "through_all": {"type": "boolean", "description": "完全贯穿", "default": False},
                "merge_result": {"type": "boolean", "description": "是否合并到现有实体（默认否，用于多实体建模）", "default": False},
                "start_offset": {"type": "number", "description": "从草图面偏移多少距离开始拉伸 mm (>0 启用等距起始)", "default": 0.0},
                "start_offset_reverse": {"type": "boolean", "description": "反转起始偏移方向", "default": False},
            },
            "required": ["depth"],
        },
        "handler": _extrude,
    },
    {
        "name": "cut_extrude",
        "description": "拉伸切除。end_cond: 0=盲切(默认)/1=贯穿/4=距面偏移(ref_x/y/z=参考面点坐标)/6=中间平面。start_offset>0 启用从草图面等距偏移起始",
        "inputSchema": {
            "type": "object",
            "properties": {
                "depth": {"type": "number", "description": "切除深度 (mm)", "default": 10},
                "through_all": {"type": "boolean", "description": "完全贯穿", "default": False},
                "reverse": {"type": "boolean", "description": "反向", "default": False},
                "both_dirs": {"type": "boolean", "description": "双向切除", "default": False},
                "end_cond": {
                    "type": "integer",
                    "description": "终止条件: 0=Blind(默认), 1=ThroughAll, 4=OffsetFromSurface, 6=MidPlane",
                    "default": 0,
                },
                "offset_distance": {"type": "number", "description": "距参考面偏移(mm), end_cond=4时生效", "default": 0.0},
                "offset_reverse": {"type": "boolean", "description": "偏移方向翻转", "default": False},
                "ref_x": {"type": "number", "description": "参考面上一点X(mm), end_cond=4时生效", "default": 0.0},
                "ref_y": {"type": "number", "description": "参考面上一点Y(mm), end_cond=4时生效", "default": 0.0},
                "ref_z": {"type": "number", "description": "参考面上一点Z(mm), end_cond=4时生效", "default": 0.0},
                "start_offset": {"type": "number", "description": "从草图面偏移多少距离开始拉伸 mm (>0 启用等距起始)", "default": 0.0},
                "start_offset_reverse": {"type": "boolean", "description": "反转起始偏移方向", "default": False},
            },
        },
        "handler": _cut_extrude,
    },
]


ALL_TOOLS = CONNECTION_TOOLS + DOCUMENT_TOOLS + FEATURE_TOOLS
