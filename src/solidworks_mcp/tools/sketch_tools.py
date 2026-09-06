"""草图工具 — 绘制草图几何体"""

import math
from ..sw_connection import connection

# 导入公共模块
from common.com_utils import safe_variant_call as _safe_variant_call
from common.unit_utils import mm_to_m


def _get_model():
    """获取 IModelDoc2 接口，无文档时抛异常"""
    model = connection.get_model()
    if model is None:
        raise RuntimeError("没有打开的文档，请先调用 connect_solidworks 并打开/新建文档")
    return model


def _create_sketch_on_plane(plane: str = "front") -> str:
    """在指定基准面上创建新草图

    plane 为空字符串时，直接在当前已选平面上插入草图（配合 add_reference_plane 使用）。
    """
    model = _get_model()

    if plane:
        # 中文 SW 基准面名称（comtypes 需要精确匹配）
        plane_map = {
            "front":  "前视基准面",
            "top":    "上视基准面",
            "right":  "右视基准面",
            "front plane":  "前视基准面",
            "top plane":    "上视基准面",
            "right plane":  "右视基准面",
        }
        plane_name = plane_map.get(plane.lower(), plane)

        model.ClearSelection2(True)
        ok = model.Extension.SelectByID2(plane_name, "PLANE", 0, 0, 0, False, 0, None, 0)
        if not ok:
            return f"❌ 无法选择基准面: {plane_name}"

    # 关闭可能存在的旧草图（InsertSketch2 是 toggle，不是「关闭」：
    # 草图开着时调用会关闭、关着时调用会打开。若上个草图还开着，直接调用
    # 会把它关掉而不是打开新草图 → 下一段实体画进上一个草图）
    try:
        if model.GetActiveSketch2() is not None:
            model.InsertSketch2(True)
    except Exception:
        pass

    # 打开新草图
    model.InsertSketch2(True)
    label = plane if plane else "当前选定面"
    return f"✅ 已在 {label} 上创建草图"


def _sketch_rectangle(x1: float, y1: float, x2: float, y2: float) -> str:
    """绘制矩形"""
    model = _get_model()
    mx1, my1 = mm_to_m(x1), mm_to_m(y1)
    mx2, my2 = mm_to_m(x2), mm_to_m(y2)
    _safe_variant_call(
        model.SketchManager.CreateCornerRectangle,
        mx1, my1, 0, mx2, my2, 0,
    )
    model.ClearSelection2(True)
    return f"✅ 已绘制矩形: ({x1},{y1}) → ({x2},{y2}) mm"


def _sketch_circle(center_x: float, center_y: float, radius: float) -> str:
    """绘制圆"""
    model = _get_model()
    mcx, mcy = mm_to_m(center_x), mm_to_m(center_y)
    mr = mm_to_m(radius)
    sm = model.SketchManager
    # AddToDB=True 关闭推理吸附，避免小偏移被 snap 到原点
    sm.AddToDB = True
    sm.DisplayWhenAdded = False
    _safe_variant_call(sm.CreateCircleByRadius, mcx, mcy, 0, mr)
    sm.AddToDB = False
    sm.DisplayWhenAdded = True
    model.ClearSelection2(True)
    return f"✅ 已绘制圆: 圆心({center_x},{center_y})mm, 半径{radius}mm"


def _sketch_line(x1: float, y1: float, x2: float, y2: float) -> str:
    """绘制直线"""
    model = _get_model()
    mx1, my1 = mm_to_m(x1), mm_to_m(y1)
    mx2, my2 = mm_to_m(x2), mm_to_m(y2)
    sm = model.SketchManager
    sm.AddToDB = True
    sm.DisplayWhenAdded = False
    _safe_variant_call(sm.CreateLine, mx1, my1, 0, mx2, my2, 0)
    sm.AddToDB = False
    sm.DisplayWhenAdded = True
    model.ClearSelection2(True)
    return f"✅ 已绘制直线: ({x1},{y1}) → ({x2},{y2}) mm"


def _sketch_polygon(center_x: float, center_y: float, radius: float, sides: int = 6) -> str:
    """绘制正多边形"""
    model = _get_model()
    if sides < 3:
        return "❌ 多边形至少需要 3 条边"
    mcx, mcy = mm_to_m(center_x), mm_to_m(center_y)
    mr = mm_to_m(radius)
    points = []
    for i in range(sides):
        a = 2 * math.pi * i / sides - math.pi / 2
        points.append((mcx + mr * math.cos(a), mcy + mr * math.sin(a)))
    for i in range(sides):
        p1, p2 = points[i], points[(i + 1) % sides]
        _safe_variant_call(
            model.SketchManager.CreateLine,
            p1[0], p1[1], 0, p2[0], p2[1], 0,
        )
    model.ClearSelection2(True)
    return f"✅ 已绘制正{sides}边形: 中心({center_x},{center_y})mm, 半径{radius}mm"


def _sketch_slot(center_x: float, center_y: float, length: float, width: float,
                 angle: float = 0) -> str:
    """绘制跑道形/腰形孔轮廓（调用 SOLIDWORKS 自带 CreateSketchSlot API，自动闭合）。

    草图坐标中，angle=0 时跑道形沿 X 轴方向（水平）。
    length 是总长度（含两端圆弧），width 是宽度（圆弧直径）。
    """
    if length <= width:
        return f"❌ 总长({length}mm) 必须大于宽度({width}mm)"
    if width <= 0:
        return "❌ 宽度必须 > 0"

    model = _get_model()

    half_straight = (length - width) / 2.0
    r = width / 2.0

    # 旋转
    rad = math.radians(angle)
    cos_a, sin_a = math.cos(rad), math.sin(rad)

    def _rotate(px, py):
        wx = center_x + px * cos_a - py * sin_a
        wy = center_y + px * sin_a + py * cos_a
        return wx, wy

    # 中心线: 从 (-half_straight, 0) 到 (half_straight, 0)，旋转后
    x1, y1 = _rotate(-half_straight, 0)
    x2, y2 = _rotate( half_straight, 0)
    # 宽度参考点: 垂直于中心线，距起点一个半宽
    x3, y3 = _rotate(-half_straight,  r)

    # CreateSketchSlot 参数 (SW2020, 14 params):
    # SlotCreationType, SlotLengthType, Width, X1,Y1,Z1, X2,Y2,Z2, X3,Y3,Z3, CenterArcDirection, AddDimension
    _safe_variant_call(
        model.SketchManager.CreateSketchSlot,
        0,              # SlotCreationType: 0=直槽口
        0,              # SlotLengthType: 0=中心到中心
        mm_to_m(width), # Width (米)
        mm_to_m(x1), mm_to_m(y1), 0.0,  # 中心线起点
        mm_to_m(x2), mm_to_m(y2), 0.0,  # 中心线终点
        mm_to_m(x3), mm_to_m(y3), 0.0,  # 宽度参考点
        0,              # CenterArcDirection: 0 for straight
        False,          # AddDimension
    )

    model.ClearSelection2(True)
    return (f"✅ 已绘制跑道形: 中心({center_x},{center_y})mm, "
            f"总长{length}mm, 宽{width}mm, 旋转{angle}°")
