"""SOLIDWORKS MCP 工具 — 统一注册表 (MCP 1.x API)

18 个基础建模工具:
    连接: connect_solidworks
    文档: get_active_document / new_part / save_document
    草图: create_sketch_on_plane / sketch_rectangle / sketch_circle /
          sketch_line / sketch_polygon / sketch_slot / sketch_centerline
    特征: extrude / cut_extrude / revolve / fillet / chamfer / circular_pattern
    外观: set_color
"""

from .connection import CONNECTION_TOOLS
from .documents import DOCUMENT_TOOLS

from .sketch_tools import (
    _create_sketch_on_plane,
    _sketch_rectangle,
    _sketch_circle,
    _sketch_line,
    _sketch_centerline,
    _sketch_polygon,
    _sketch_slot,
)
from .feature_tools import (
    _extrude,
    _cut_extrude,
    _revolve,
    _circular_pattern,
    _fillet,
    _chamfer,
)
from .appearance_tools import _set_color


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
        "name": "sketch_centerline",
        "description": "在当前草图中绘制中心线（构造线），用作旋转特征(revolve)的旋转轴。调用后 revolve 自动识别此线为旋转轴",
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
        "handler": _sketch_centerline,
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
    {
        "name": "revolve",
        "description": "旋转凸台/切除。需先创建草图→绘制轮廓→sketch_centerline画中心线，再调用此工具。逆时针为正角度",
        "inputSchema": {
            "type": "object",
            "properties": {
                "angle": {"type": "number", "description": "旋转角度(度), 默认 360", "default": 360.0},
                "is_cut": {"type": "boolean", "description": "True=旋转切除, False=旋转凸台", "default": False},
                "reverse_dir": {"type": "boolean", "description": "反向旋转", "default": False},
                "both_dirs": {"type": "boolean", "description": "双向旋转", "default": False},
                "dir2_angle": {"type": "number", "description": "方向2角度(度)，仅 both_dirs=True 时生效", "default": 0.0},
                "mid_plane": {"type": "boolean", "description": "中间平面对称旋转", "default": False},
                "merge_result": {"type": "boolean", "description": "合并到现有实体", "default": True},
            },
        },
        "handler": _revolve,
    },
    {
        "name": "fillet",
        "description": "对选中的边倒圆角，单位: 毫米",
        "inputSchema": {
            "type": "object",
            "properties": {
                "radius": {"type": "number", "description": "圆角半径 (mm)"},
            },
            "required": ["radius"],
        },
        "handler": _fillet,
    },
    {
        "name": "chamfer",
        "description": "对选中的边倒角。需先选中边。支持: angle_distance(距离+角度)/equal_distance(等距45°)/distance_distance(两边不等距)/vertex(顶点倒角)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "distance": {"type": "number", "description": "倒角距离/宽度 (mm)", "default": 1.0},
                "angle": {"type": "number", "description": "倒角角度(度), angle_distance模式默认45; vertex模式下用作第三边距离(mm)", "default": 45.0},
                "distance2": {"type": "number", "description": "第二边距离(mm), 仅 distance_distance/vertex 模式使用", "default": 0.0},
                "chamfer_type": {
                    "type": "string",
                    "enum": ["angle_distance", "equal_distance", "distance_distance", "vertex"],
                    "description": "倒角类型: angle_distance=距离角度, equal_distance=等距45°, distance_distance=两边不等距, vertex=顶点倒角",
                    "default": "angle_distance",
                },
                "flip": {"type": "boolean", "description": "翻转倒角方向", "default": False},
            },
        },
        "handler": _chamfer,
    },
    {
        "name": "circular_pattern",
        "description": "圆周阵列。需先选好种子特征和旋转轴（参考轴）。对应 SOLIDWORKS: 插入→阵列/镜像→圆周阵列",
        "inputSchema": {
            "type": "object",
            "properties": {
                "num_instances": {
                    "type": "integer",
                    "description": "实例数（含原始），默认 3",
                    "default": 3,
                },
                "spacing_deg": {
                    "type": "number",
                    "description": "间距角度(度)。equal_spacing=True 时为总角度，默认 360°",
                    "default": 360.0,
                },
                "equal_spacing": {
                    "type": "boolean",
                    "description": "等间距分布，默认 true",
                    "default": True,
                },
                "flip_direction": {
                    "type": "boolean",
                    "description": "翻转阵列方向，默认 false",
                    "default": False,
                },
                "geometry_pattern": {
                    "type": "boolean",
                    "description": "仅几何阵列（不重新求解），默认 false",
                    "default": False,
                },
                "seed_feature": {
                    "type": "string",
                    "description": "种子特征名称（如 '切除-拉伸2'）。为空时自动选中最后一个特征",
                    "default": "",
                },
                "axis_type": {
                    "type": "string",
                    "description": "旋转轴类型: axis(参考轴,默认) / edge(边) / cylindrical_face(圆柱面)",
                    "default": "axis",
                },
                "axis_name": {
                    "type": "string",
                    "description": "参考轴名称（如 'Axis1'），axis_type='axis' 时使用",
                    "default": "",
                },
            },
        },
        "handler": _circular_pattern,
    },
    {
        "name": "set_color",
        "description": "设置面/特征/零件的颜色。R/G/B 范围 0-255。不选特征时设置整个零件颜色。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "r": {"type": "integer", "description": "红色 (0-255)"},
                "g": {"type": "integer", "description": "绿色 (0-255)"},
                "b": {"type": "integer", "description": "蓝色 (0-255)"},
                "feature_name": {
                    "type": "string",
                    "description": "特征名称（可选）。为空时设置整个零件颜色",
                    "default": "",
                },
                "transparency": {
                    "type": "number",
                    "description": "透明度 (0.0=不透明, 1.0=全透明)，默认 0",
                    "default": 0.0,
                },
            },
            "required": ["r", "g", "b"],
        },
        "handler": _set_color,
    },
]


ALL_TOOLS = CONNECTION_TOOLS + DOCUMENT_TOOLS + FEATURE_TOOLS
