"""草图工具 — 绘制草图几何体"""

import math
from ..sw_connection import connection
from ..utils import ensure_callable

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


def _sketch_spline(points: list) -> str:
    """绘制样条曲线。

    Args:
        points: 控制点列表 [(x1,y1), (x2,y2), ...] 或 [x1,y1,z1, x2,y2,z2, ...] (mm)
                支持 2D 点 list 或扁平化坐标 list
    """
    model = _get_model()
    sm = model.SketchManager
    ensure_callable(sm, 'CreateSpline')

    # Flatten points to [x0,y0,z0, x1,y1,z1, ...] in meters
    import array
    flat = array.array('d')
    for p in points:
        if isinstance(p, (list, tuple)):
            if len(p) >= 3:
                flat.append(mm_to_m(p[0]))
                flat.append(mm_to_m(p[1]))
                flat.append(mm_to_m(p[2]))
            else:
                flat.append(mm_to_m(p[0]))
                flat.append(mm_to_m(p[1]))
                flat.append(0.0)
        else:
            # Bare float — assume already flattened
            flat.append(mm_to_m(p))

    sm.AddToDB = True
    sm.DisplayWhenAdded = False
    _safe_variant_call(sm.CreateSpline, flat)
    sm.AddToDB = False
    sm.DisplayWhenAdded = True
    model.ClearSelection2(True)

    n = len(points)
    return f"✅ 已绘制样条曲线: {n} 个控制点"


def _sketch_centerline(x1: float, y1: float, x2: float, y2: float) -> str:
    """绘制中心线（构造线），用作旋转特征的旋转轴。

    内部通过 ISketchManager::CreateCenterLine 创建，
    区别于普通 sketch_line：CreateCenterLine 返回的段自动标记为构造几何。

    中点坐标存储为函数属性 _sketch_centerline._last_centerline_mid_mm，
    供 feature_tools._revolve 选轴用。
    """
    model = _get_model()
    mx1, my1 = mm_to_m(x1), mm_to_m(y1)
    mx2, my2 = mm_to_m(x2), mm_to_m(y2)
    sm = model.SketchManager
    sm.AddToDB = True
    sm.DisplayWhenAdded = False
    _safe_variant_call(sm.CreateCenterLine, mx1, my1, 0, mx2, my2, 0)
    sm.AddToDB = False
    sm.DisplayWhenAdded = True
    # 存储中点坐标供 _revolve 选中旋转轴 (Mark=4)
    _sketch_centerline._last_centerline_mid_mm = ((x1 + x2) / 2.0, (y1 + y2) / 2.0, 0.0)
    model.ClearSelection2(True)
    return f"✅ 已绘制中心线: ({x1},{y1}) → ({x2},{y2}) mm"


def _sketch_fillet(x1: float, y1: float, x2: float, y2: float,
                   radius: float) -> str:
    """在两个草图段交点处创建圆角。

    选择靠近 (x1,y1) 和 (x2,y2) 的两个草图段，
    调用 ISketchManager::CreateFillet 生成切线弧并自动剪裁。
    (x1,y1) 和 (x2,y2) 应分别在形成交角的两条边上、靠近交点。

    对应 SOLIDWORKS: 草图 → 绘制圆角 (Sketch Fillet)
    """
    model = _get_model()
    mx1, my1 = mm_to_m(x1), mm_to_m(y1)
    mx2, my2 = mm_to_m(x2), mm_to_m(y2)
    m_radius = mm_to_m(radius)

    # 选中第一条段（不 append）
    model.ClearSelection2(True)
    if not model.Extension.SelectByID2("", "SKETCHSEGMENT", mx1, my1, 0, False, 0, None, 0):
        return f"❌ 未找到坐标 ({x1:.1f}, {y1:.1f}) 处的草图段"

    # 选中第二条段（append）
    if not model.Extension.SelectByID2("", "SKETCHSEGMENT", mx2, my2, 0, True, 0, None, 0):
        return f"❌ 未找到坐标 ({x2:.1f}, {y2:.1f}) 处的草图段"

    # swConstrainedCornerDeleteGeometry=0: 删除几何约束（最常用）
    _safe_variant_call(model.SketchManager.CreateFillet, m_radius, 0)
    model.ClearSelection2(True)
    return f"✅ 已创建草图圆角: 半径 {radius}mm"


def _sketch_trim(option: str = "closest", x: float = 0.0, y: float = 0.0) -> str:
    """剪裁/延伸草图段。

    option 对应 SW Trim PropertyManager:
      - closest    — 剪裁到最近交点（需先选 1 条段）
      - corner     — 延伸/剪裁两段形成角（需先选 2 条段）
      - inside     — 剪裁内部（需选边界2段+被剪段≥1）
      - outside    — 剪裁外部
      - point      — 在指定点处剪裁 (需传 x,y)
      - two_entities — 第一段剪到第二段(选中顺序决定)

    调用方式：先用 SelectByID2 选中要剪裁的段，再调此函数。
    或者传 x,y 坐标 + option=point 精确裁剪。

    对应 SOLIDWORKS: 草图 → 剪裁实体 (Trim Entities)
    """
    model = _get_model()

    option_map = {
        "closest": 0,     # swSketchTrimClosest
        "corner": 1,      # swSketchTrimCorner
        "entities": 2,    # swSketchTrimEntities (power trim)
        "point": 3,       # swSketchTrimEntityPoint
        "inside": 4,      # swSketchTrimInside
        "outside": 5,     # swSketchTrimOutside
        "two_entities": 6,  # swSketchTrimTwoEntities
    }
    opt_val = option_map.get(option.lower(), 0)

    if option.lower() == "point":
        mx, my = mm_to_m(x), mm_to_m(y)
    else:
        mx, my = 0.0, 0.0

    # ISketchManager::SketchTrim 返回 bool (True=成功)
    # 不用 _safe_variant_call 包装（它会干扰 COM 返回值的解析）
    try:
        ok = model.SketchManager.SketchTrim(opt_val, mx, my, 0.0)
    except Exception:
        ok = False

    if not ok:
        return f"❌ 草图剪裁失败: {option}（请确认已选中正确的草图段）"
    return f"✅ 草图剪裁完成: {option}"


def _sketch_arc(center_x: float, center_y: float,
               start_x: float, start_y: float,
               end_x: float, end_y: float,
               direction: int = 1) -> str:
    """画圆弧。direction: 1=逆时针(CCW), -1=顺时针(CW)"""
    model = _get_model()
    sm = model.SketchManager
    sm.AddToDB = True
    sm.DisplayWhenAdded = False
    _safe_variant_call(
        sm.CreateArc,
        mm_to_m(center_x), mm_to_m(center_y), 0,
        mm_to_m(start_x), mm_to_m(start_y), 0,
        mm_to_m(end_x), mm_to_m(end_y), 0,
        direction,
    )
    sm.AddToDB = False
    sm.DisplayWhenAdded = True
    model.ClearSelection2(True)
    dir_str = "逆时针" if direction >= 0 else "顺时针"
    return f"✅ 已绘制圆弧: 圆心({center_x},{center_y}) {start_x},{start_y}→{end_x},{end_y} ({dir_str})"


def _sketch_offset(distance: float, both_directions: bool = False,
                   chain: bool = True, cap_ends: int = 2) -> str:
    """等距实体 — 将已选中的草图实体偏移指定距离。

    对应 SOLIDWORKS: 工具 → 草图工具 → 等距实体
    使用 ISketchManager::SketchOffset2 (SW 2016+)

    调用流程:
      1. 先用 SelectByID2 选中要偏移的草图实体（如圆、线段）
      2. 调用 _sketch_offset(distance)

    Args:
        distance: 偏移距离 mm，负值向内/反向偏移
        both_directions: 是否双向偏移
        chain: 是否偏移整个链（相连实体一起偏移）
        cap_ends: 端盖类型 0=无, 1=圆弧端盖, 2=直线端盖(默认，自动封闭)
    """
    model = _get_model()
    sm = model.SketchManager
    ensure_callable(sm, 'SketchOffset2')

    m_dist = mm_to_m(abs(distance))
    # 负距离 = 反向偏移
    offset_val = -m_dist if distance < 0 else m_dist

    # ISketchManager::SketchOffset2(Offset, BothDirections, Chain, CapEnds, MakeConstruction, AddDimensions)
    ok = sm.SketchOffset2(offset_val, both_directions, chain, cap_ends, 0, False)

    if not ok:
        return f"❌ 等距实体失败: distance={distance}mm（请确认已选中草图实体）"
    return f"✅ 等距实体完成: 偏移 {distance}mm"


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
