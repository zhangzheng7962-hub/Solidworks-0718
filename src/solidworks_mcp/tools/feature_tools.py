"""特征工具 — 拉伸/切除/阵列/倒角等特征操作"""

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


def _get_last_sketch_name(model):
    """遍历特征树找最新 ProfileFeature 的名称（O(n) 一次遍历取最大 ID）。

    FeatureRevolve2 需要先选中草图 (Mark=0)，此函数提供草图名称。
    """
    from comtypes.gen import SldWorks as SW
    last_name, last_id = None, -1
    feat = model.FirstFeature()
    while feat:
        try:
            cur = feat.QueryInterface(SW.IFeature)
        except Exception:
            feat = feat.GetNextFeature() if feat else None
            continue
        if cur and cur.GetTypeName2() == "ProfileFeature":
            cur_id = cur.GetID()
            if cur_id > last_id:
                last_id = cur_id
                last_name = cur.Name
        feat = cur.GetNextFeature() if cur else None
    return last_name


def _extrude(depth: float, reverse: bool = False, both_dirs: bool = False,
             through_all: bool = False, merge_result: bool = False,
             start_offset: float = 0.0, start_offset_reverse: bool = False,
             *, _return_feature: bool = False):
    """拉伸凸台。返回 (msg, feat_id, feat_name) 当 _return_feature=True，否则返回 msg。

    start_offset > 0: 从距草图面偏移指定距离处开始拉伸 (T0=3 swStartOffset).
    使用 FeatureExtrusion3 (23 params, SW 2001Plus+) 支持起始偏移。
    """
    model = _get_model()
    # 先关闭草图（和 _cut_extrude 一致）
    model.InsertSketch2(True)
    m_depth = mm_to_m(depth)
    fm = model.FeatureManager
    dir_param = True if reverse else False
    end_cond = 1 if through_all else 0

    # T0: 起始条件 — 0=从草图面, 3=swStartOffset(等距起始)
    t0 = 3 if start_offset > 0 else 0
    so_m = mm_to_m(start_offset) if start_offset > 0 else 0.0

    feat = _safe_variant_call(
        fm.FeatureExtrusion3,
        not both_dirs,   # Sd: 单向
        False,           # Flip
        dir_param,       # Dir: 反向
        end_cond,        # T1: 终止条件
        0,               # T2
        m_depth,         # D1
        0,               # D2
        False, False, False, False,  # Dchk1/2, Ddir1/2
        0, 0,            # Dang1/2
        False, False,    # OffsetReverse1/2
        False, False,    # TranslateSurface1/2
        merge_result,    # Merge
        True, True,      # UseFeatScope, UseAutoSelect
        t0,              # T0: 起始条件
        so_m,            # StartOffset (米)
        start_offset_reverse,  # FlipStartOffset
    )
    direction = " (反向)" if reverse else ""
    both = " 双向" if both_dirs else ""
    thru = " 贯穿" if through_all else ""
    so = f" 等距起始{start_offset}mm" if start_offset > 0 else ""
    msg = f"✅ 拉伸凸台完成，深度: {depth}mm{direction}{both}{thru}{so}"
    if _return_feature:
        if feat is not None:
            return msg, feat.GetID(), feat.Name or ""
        return "❌ 拉伸凸台失败（FeatureExtrusion3 返回 None）", -1, ""
    return msg


def _cut_extrude(depth: float = 10, through_all: bool = False,
                 reverse: bool = False, both_dirs: bool = False,
                 *, _return_feature: bool = False,
                 end_cond: int = 0, offset_distance: float = 0.0,
                 offset_reverse: bool = False,
                 ref_x: float = 0.0, ref_y: float = 0.0, ref_z: float = 0.0,
                 start_offset: float = 0.0, start_offset_reverse: bool = False,
                 depth_d2: float = 0.0):
    """拉伸切除。支持 Blind/ThroughAll/OffsetFromSurface/MidPlane/StartOffset。

    使用 IFeatureManager::FeatureCut4 (SW 2017+, 27 params).
    depth_d2 > 0 时启用双向不等深: D1=depth, D2=depth_d2, Sd=False.
    """

    # ... (implementation stays the same, just add T0=3 logic) ...
    model = _get_model()
    from comtypes.gen import SldWorks as SW

    # ── 1. 关闭草图并找到草图名 ──
    model.InsertSketch2(True)

    sketch_name = None
    fd = model.FirstFeature()
    while fd:
        try:
            cur = fd.QueryInterface(SW.IFeature)
        except Exception:
            fd = fd.GetNextFeature() if fd else None
            continue
        if cur and cur.GetTypeName2() == "ProfileFeature":
            sketch_name = cur.Name
        fd = cur.GetNextFeature() if cur else None

    if not sketch_name:
        if _return_feature:
            return "❌ 未找到草图", -1, ""
        return "❌ 未找到草图"

    # ── 2. 选中草图(Mark=0) ──
    model.ClearSelection2(True)
    if not model.Extension.SelectByID2(sketch_name, "SKETCH", 0, 0, 0, False, 0, None, 0):
        if _return_feature:
            return f"❌ 无法选中草图: {sketch_name}", -1, ""
        return f"❌ 无法选中草图: {sketch_name}"

    # ── 3. OffsetFromSurface: 选中参考面(Mark=1) ──
    if end_cond == 4:
        mx, my, mz = mm_to_m(ref_x), mm_to_m(ref_y), mm_to_m(ref_z)
        if not model.Extension.SelectByID2("", "FACE", mx, my, mz, True, 1, None, 0):
            if _return_feature:
                return f"❌ 无法选中参考面 ({ref_x}, {ref_y}, {ref_z}) mm", -1, ""
            return f"❌ 无法选中参考面 ({ref_x}, {ref_y}, {ref_z}) mm"

    # ── 4. 确定终止条件和深度 ──
    fm = model.FeatureManager
    dir_reverse = True if reverse else False

    if through_all or end_cond == 1:
        t1, d1 = 1, 0.0  # swEndCondThroughAll
    elif end_cond == 4:
        t1 = 4  # swEndCondOffsetFromSurface
        d1 = mm_to_m(offset_distance if offset_distance > 0 else depth)
    elif end_cond == 6:
        t1 = 6  # swEndCondMidPlane
        d1 = mm_to_m(depth)
    else:
        t1 = 0  # swEndCondBlind
        d1 = mm_to_m(depth)

    # ── 5. 起始条件 ──
    if start_offset > 0:
        t0 = 3          # swStartOffset
        so_m = mm_to_m(start_offset)
        flip_so = start_offset_reverse
    else:
        t0 = 0          # swStartSketchPlane
        so_m = 0.0
        flip_so = False

    # ── 6. FeatureCut4 ──
    if depth_d2 > 0:
        # 双向不等深
        sd = False   # not single direction
        t1, d1 = t1, d1
        t2 = 0       # Blind for reverse
        d2 = mm_to_m(depth_d2)
    else:
        sd = not both_dirs
        t2 = 0
        d2 = 0.0
    feat = _safe_variant_call(fm.FeatureCut4,
        sd,              # Sd: single direction
        False,           # Flip: don't flip side to cut
        dir_reverse,     # Dir: reverse direction
        t1, t2,          # T1, T2: end conditions
        d1, d2,          # D1, D2: depths (meters)
        False, False,    # Dchk1, Dchk2: draft
        False, False,    # Ddir1, Ddir2: draft direction
        0.0, 0.0,        # Dang1, Dang2: draft angles
        offset_reverse,  # OffsetReverse1
        False,           # OffsetReverse2
        False,           # TranslateSurface1 (false = true offset)
        False,           # TranslateSurface2
        False,           # NormalCut
        True, True,      # UseFeatScope, UseAutoSelect
        False, False,    # AssemblyFeatureScope, AutoSelectComponents
        False,           # PropagateFeatureToParts
        t0,              # T0: start condition
        so_m,            # StartOffset: offset distance (meters)
        flip_so,         # FlipStartOffset
        False,           # OptimizeGeometry (sheet metal)
    )

    if feat is None:
        if _return_feature:
            return "❌ FeatureCut4 返回 None", -1, ""
        return "❌ FeatureCut4 返回 None"

    # ── 7. 构建描述 ──
    if start_offset > 0:
        prefix = f"从草图面偏移 {start_offset:.1f}mm"
        if start_offset_reverse:
            prefix += " (反向)"
        prefix += " 开始, "
    else:
        prefix = ""

    if through_all:
        desc = "完全贯穿"
    elif end_cond == 4:
        desc = f"距面({ref_x:.1f},{ref_y:.1f},{ref_z:.1f})偏移 {offset_distance if offset_distance > 0 else depth:.1f}mm"
        if offset_reverse:
            desc += " (反向)"
    elif end_cond == 6:
        desc = "中间平面"
    elif depth_d2 > 0:
        desc = f"深度 {depth:.1f}mm (上侧) / {depth_d2:.1f}mm (下侧)"
    else:
        desc = f"深度 {depth:.1f}mm"

    if reverse:
        desc += " (反向)"
    if both_dirs and depth_d2 == 0:
        desc += " 双向"

    msg = f"✅ 拉伸切除完成，{prefix}{desc}"
    if _return_feature:
        return msg, feat.GetID(), feat.Name or ""
    return msg


def _revolve(angle: float = 360.0, is_cut: bool = False,
             reverse_dir: bool = False, both_dirs: bool = False,
             dir2_angle: float = 0.0, mid_plane: bool = False,
             merge_result: bool = True, *, _return_feature: bool = False):
    """旋转凸台/切除。需先绘制轮廓 + sketch_centerline 画中心线。

    对应 SOLIDWORKS: 插入 → 凸台/基体 → 旋转 / 插入 → 切除 → 旋转

    FeatureRevolve2 不会自动消耗活动草图 — 需要先关闭草图，
    再通过 SelectByID2 选中草图(Mark=0) + 中心线(Mark=4)。

    Args:
        angle: 旋转角度 (度), 默认 360
        is_cut: True=旋转切除, False=旋转凸台
        reverse_dir: 反向旋转
        both_dirs: 双向旋转
        dir2_angle: 方向2角度 (度), 仅 both_dirs=True 时生效
        mid_plane: 中间平面对称旋转 (SingleDir=False, Dir1Type=5)
        merge_result: 合并到现有实体
        _return_feature: 内部使用, 返回 (msg, feature_id, feature_name)
    """
    model = _get_model()

    # ── 1. 关闭草图 ──
    # FeatureRevolve2 与 FeatureExtrusion2 不同：不自动消耗活动草图。
    # 必须先 InsertSketch2(True) 关闭草图，再 SelectByID2 选中。
    model.InsertSketch2(True)

    # ── 2. 查找草图名称 ──
    sketch_name = _get_last_sketch_name(model)
    if not sketch_name:
        return "❌ 未找到草图，请先 create_sketch_on_plane → 绘制轮廓 → sketch_centerline"

    # ── 3. 选中草图 (Mark=0) ──
    model.ClearSelection2(True)
    if not model.Extension.SelectByID2(sketch_name, "SKETCH", 0, 0, 0, False, 0, None, 0):
        return f"❌ 无法选中草图: {sketch_name}"

    # ── 4. 选中中心线作为旋转轴 (Mark=4) ──
    # 从 sketch_tools 模块获取最后绘制的中心线中点
    from . import sketch_tools
    if hasattr(sketch_tools, '_sketch_centerline') and hasattr(sketch_tools._sketch_centerline, '_last_centerline_mid_mm'):
        stored_mid = sketch_tools._sketch_centerline._last_centerline_mid_mm
        if stored_mid is not None:
            mx, my, mz = mm_to_m(stored_mid[0]), mm_to_m(stored_mid[1]), mm_to_m(stored_mid[2])
            sketch_tools._sketch_centerline._last_centerline_mid_mm = None  # 消费后清除

            # 尝试多种类型字符串选中中心线
            axis_ok = model.Extension.SelectByID2(
                "", "EXTSKETCHSEGMENT", mx, my, mz, True, 4, None, 0)
            if not axis_ok:
                axis_ok = model.Extension.SelectByID2(
                    "", "SKETCHSEGMENT", mx, my, mz, True, 4, None, 0)
            if not axis_ok:
                return (f"❌ 无法在坐标 ({stored_mid[0]:.1f}, {stored_mid[1]:.1f}, "
                        f"{stored_mid[2]:.1f}) 处选中中心线作为旋转轴")
    # else: 没有中心线 — 让 FeatureRevolve2 自动检测旋转轴（原图模式）

    # ── 5. 计算 FeatureRevolve2 参数 ──
    # 终止条件: swEndCondBlind=0, swEndCondThroughAll=1, swEndCondMidPlane=5
    angle_rad = angle * math.pi / 180.0
    dir2_rad = dir2_angle * math.pi / 180.0

    if mid_plane:
        single_dir = False
        dir1_type = 5   # swEndCondMidPlane
        dir2_type = 0
        dir1_rad = angle_rad
        dir2_rad = 0.0
    elif both_dirs:
        single_dir = False
        dir1_type = 0   # swEndCondBlind
        dir2_type = 0   # swEndCondBlind
        dir1_rad = angle_rad
        # dir2_rad already set above
    else:
        single_dir = True
        dir1_type = 0   # swEndCondBlind
        dir2_type = 0
        dir1_rad = angle_rad
        dir2_rad = 0.0

    # ── 6. 调用 FeatureRevolve2 ──
    feat = _safe_variant_call(
        model.FeatureManager.FeatureRevolve2,
        single_dir,          # SingleDir
        True,                # IsSolid (solid revolve, not thin)
        False,               # IsThin
        is_cut,              # IsCut
        reverse_dir,         # ReverseDir
        False,               # BothDirectionUpToSameEntity
        dir1_type,           # Dir1Type (swEndConditions_e)
        dir2_type,           # Dir2Type
        dir1_rad,            # Dir1Angle (radians)
        dir2_rad,            # Dir2Angle (radians)
        False,               # OffsetReverse1
        False,               # OffsetReverse2
        0.0,                 # OffsetDistance1
        0.0,                 # OffsetDistance2
        0,                   # ThinType (not thin wall)
        0.0,                 # ThinThickness1
        0.0,                 # ThinThickness2
        merge_result,        # Merge
        True,                # UseFeatScope
        True,                # UseAutoSelect
    )

    if feat is None:
        label = "旋转切除" if is_cut else "旋转凸台"
        return f"❌ {label}失败（FeatureRevolve2 返回 None）"

    # ── 构建结果描述 ──
    desc_parts = []
    if is_cut:
        desc_parts.append("旋转切除")
    else:
        desc_parts.append("旋转凸台")

    if mid_plane:
        desc_parts.append(f"中间平面对称 {angle}°")
    elif both_dirs:
        desc_parts.append(f"方向1={angle}° 方向2={dir2_angle}°")
    else:
        desc_parts.append(f"{angle}°")

    if reverse_dir:
        desc_parts.append("(反向)")

    msg = f"✅ {' '.join(desc_parts)}"
    if _return_feature:
        return msg, feat.GetID(), feat.Name or ""
    return msg


def _circular_pattern(num_instances: int = 3, spacing_deg: float = 360.0,
                      equal_spacing: bool = True, flip_direction: bool = False,
                      geometry_pattern: bool = False,
                      seed_feature: str = "", axis_type: str = "axis",
                      axis_name: str = "") -> str:
    """圆周阵列。

    对应 SOLIDWORKS: 插入 → 阵列/镜像 → 圆周阵列

    调用前需确保种子特征和旋转轴可被选中。

    Args:
        num_instances: 实例数（含原始），默认 3
        spacing_deg: 间距(度)。equal_spacing=True 时为总角度（默认 360° 全圆）
        equal_spacing: 等间距分布（默认 True）
        flip_direction: 翻转阵列方向
        geometry_pattern: 仅几何阵列（不重新求解特征）
        seed_feature: 种子特征名称（如 "切除-拉伸2"）。为空时自动选中最后一个特征
        axis_type: 旋转轴类型 — "axis"(默认, 参考轴), "edge"(边), "cylindrical_face"(圆柱面)
        axis_name: 旋转轴名称（仅 axis_type="axis" 时使用，如 "Axis1"）
    """
    from comtypes.gen import SldWorks as SW
    model = _get_model()

    # ── 1. 选中种子特征 (Mark=4) ──
    model.ClearSelection2(True)

    if seed_feature:
        ok = model.Extension.SelectByID2(
            seed_feature, "BODYFEATURE", 0, 0, 0, False, 4, None, 0)
        if not ok:
            return f"❌ 无法选中种子特征: {seed_feature}"
    else:
        # 自动选中最后一个特征
        feat = model.FirstFeature()
        if feat is None:
            return "❌ 模型中没有特征"
        ensure_callable(feat, 'GetNextFeature')
        last_feat = feat
        while feat:
            last_feat = feat
            nd = feat.GetNextFeature()
            feat = nd.QueryInterface(SW.IFeature) if nd else None
        if not last_feat.Select2(False, 4):
            return "❌ 无法自动选中最后一个特征作为种子"
        seed_feature = last_feat.Name or "(自动)"

    # ── 2. 选中旋转轴 (Mark=1) ──
    if axis_type == "axis":
        axis_id = axis_name if axis_name else "Axis1"
        ok = model.Extension.SelectByID2(
            axis_id, "AXIS", 0, 0, 0, True, 1, None, 0)
        if not ok:
            return f"❌ 无法选中参考轴: {axis_id}。请先用两个基准面 InsertAxis2 创建轴"
    elif axis_type == "edge":
        # 选中最近的边作为轴 — 需要用户提供边上的点
        return "❌ axis_type='edge' 暂不支持，请使用 'axis' 或 'cylindrical_face'"
    elif axis_type == "cylindrical_face":
        return "❌ axis_type='cylindrical_face' 暂不支持，请使用 'axis'"
    else:
        return f"❌ 未知 axis_type: {axis_type}"

    # ── 3. 计算参数 ──
    spacing_rad = spacing_deg * math.pi / 180.0

    # ── 4. 调用 FeatureCircularPattern4 ──
    feat = _safe_variant_call(
        model.FeatureManager.FeatureCircularPattern4,
        num_instances,       # Number (含原始实例)
        spacing_rad,         # Spacing (弧度)
        flip_direction,      # FlipDirection
        "NULL",              # DName (角度尺寸名, "NULL" 用默认)
        geometry_pattern,    # GeometryPattern
        equal_spacing,       # EqualSpacing
        False,               # VaryInstance
    )

    if feat is None:
        return "❌ 圆周阵列失败（FeatureCircularPattern4 返回 None）"

    spacing_desc = f"总角度={spacing_deg}°" if equal_spacing else f"间距={spacing_deg}°"
    return f"✅ 圆周阵列成功: {num_instances}实例, {spacing_desc}, 种子={seed_feature}"


def _mirror_feature(feature_name: str = "", mirror_plane: str = "",
                    mirror_plane_type: str = "plane",
                    geometry_pattern: bool = False) -> str:
    """镜像特征。

    对应 SOLIDWORKS: 插入 → 阵列/镜像 → 镜像

    调用前需确保要镜像的特征和镜像基准面可被选中。

    Args:
        feature_name: 要镜像的特征名称（如 "凸台-拉伸3"）。为空时自动选中最后一个特征
        mirror_plane: 镜像基准面名称（如 "右视基准面"）或面上一点坐标 "x,y,z"
        mirror_plane_type: 基准面类型 — "plane"(参考基准面), "face"(实体面)
        geometry_pattern: 仅镜像几何
    """
    from comtypes.gen import SldWorks as SW
    model = _get_model()

    # ── 1. 选中要镜像的特征 (Mark=1) ──
    model.ClearSelection2(True)

    if feature_name:
        ok = model.Extension.SelectByID2(
            feature_name, "BODYFEATURE", 0, 0, 0, False, 1, None, 0)
        if not ok:
            return f"❌ 无法选中特征: {feature_name}"
    else:
        # 自动选中最后一个特征
        feat = model.FirstFeature()
        if feat is None:
            return "❌ 模型中没有特征"
        ensure_callable(feat, 'GetNextFeature')
        last_feat = feat
        while feat:
            last_feat = feat
            nd = feat.GetNextFeature()
            feat = nd.QueryInterface(SW.IFeature) if nd else None
        if not last_feat.Select2(False, 1):
            return "❌ 无法自动选中最后一个特征"
        feature_name = last_feat.Name or "(自动)"

    # ── 2. 选中镜像基准面 (Mark=2) ──
    if mirror_plane_type == "plane":
        # 标准基准面名称
        plane_name = mirror_plane if mirror_plane else "右视基准面"
        ok = model.Extension.SelectByID2(
            plane_name, "PLANE", 0, 0, 0, True, 2, None, 0)
        if not ok:
            # 尝试英文名
            en_names = {"右视基准面": "Right Plane", "前视基准面": "Front Plane",
                        "上视基准面": "Top Plane"}
            en_name = en_names.get(plane_name, plane_name)
            ok = model.Extension.SelectByID2(
                en_name, "PLANE", 0, 0, 0, True, 2, None, 0)
        if not ok:
            return f"❌ 无法选中镜像基准面: {plane_name}"
    elif mirror_plane_type == "face":
        # mirror_plane 格式: "x,y,z"（面上一点的世界坐标 mm）
        try:
            parts = [float(v.strip()) for v in mirror_plane.split(",")]
            fx, fy, fz = mm_to_m(parts[0]), mm_to_m(parts[1]), mm_to_m(parts[2])
        except (ValueError, IndexError):
            return f"❌ face 模式下 mirror_plane 需为 'x,y,z' 格式，收到: {mirror_plane}"
        ok = model.Extension.SelectByID2(
            "", "FACE", fx, fy, fz, True, 2, None, 0)
        if not ok:
            return f"❌ 无法在 ({parts[0]}, {parts[1]}, {parts[2]}) 处选中面"
    else:
        return f"❌ 未知 mirror_plane_type: {mirror_plane_type}"

    # ── 3. 调用 InsertMirrorFeature2 ──
    feat = _safe_variant_call(
        model.FeatureManager.InsertMirrorFeature2,
        False,               # BMirrorBody (False=镜像特征, True=镜像实体)
        geometry_pattern,    # BGeometryPattern
        False,               # BMerge
        False,               # BKnit
        0,                   # ScopeOptions (swFeatureScope_AllBodies=0)
    )

    if feat is None:
        return f"❌ 镜像失败（InsertMirrorFeature2 返回 None）"

    return f"✅ 镜像成功: 特征={feature_name}, 基准面={mirror_plane or '右视基准面'}"


def _fillet(radius: float) -> str:
    """倒圆角"""
    model = _get_model()
    m_radius = mm_to_m(radius)
    # ⚠️ model.FeatureFillet() 无选中边时也返回 0 (S_OK)，假成功。
    # 改用 FeatureManager.FeatureFillet3(Options, R1, R2, Rho, Ftyp, ...) — 实测可靠。
    # Options=195: constant radius + no propagate + keep features
    empty = []
    before = model.FeatureManager.GetFeatureCount(True)
    feat = _safe_variant_call(
        model.FeatureManager.FeatureFillet3,
        195,           # Options: constant radius
        m_radius,      # R1
        0,             # R2
        0,             # Rho
        0,             # Ftyp (0=simple)
        0,             # OverflowType
        0,             # ConicRhoType
        empty,         # Radii
        empty,         # Dist2Arr
        empty,         # RhoArr
        empty,         # SetBackDistances
        empty,         # PointRadiusArray
        empty,         # PointDist2Array
        empty,         # PointRhoArray
    )
    after = model.FeatureManager.GetFeatureCount(True)
    if after > before:
        return f"✅ 倒圆角完成，半径: {radius}mm"
    return f"❌ 倒圆角失败（特征数未变化 {before}→{after}）"


def _chamfer(distance: float = 1.0, angle: float = 45.0,
             distance2: float = 0.0,
             chamfer_type: str = "angle_distance",
             flip: bool = False) -> str:
    """对选中的边倒角。需先用 SelectByID2 选中目标边。

    chamfer_type 支持:
      - angle_distance:   距离+角度 (distance=d1, angle=45°)
      - equal_distance:   两边等距 (distance=d1, 45°倒角)
      - distance_distance: 两边不等距 (distance=d1, distance2=d2)
      - vertex:           顶点倒角 (distance/distance2/angle → d1/d2/d3)
    """
    model = _get_model()

    m_dist = mm_to_m(distance)
    angle_rad = angle * math.pi / 180.0
    m_dist2 = mm_to_m(distance2)

    # InsertFeatureChamfer(Options, ChamferType, Width, Angle, OtherDist,
    #                      VertexChamDist1, VertexChamDist2, VertexChamDist3)
    # FeatureChamferType(ChamferType, Width, Angle, Flip, OtherDist,
    #                     VertexChamDist1, VertexChamDist2, VertexChamDist3)
    #
    # angle_distance/equal_distance → InsertFeatureChamfer
    # distance_distance/vertex       → FeatureChamferType (内建 flip 支持)

    if chamfer_type == "angle_distance":
        # FeatureChamferType(1=angle-distance, Width=d, Angle=a, Flip, ...)
        _safe_variant_call(model.FeatureChamferType,
                           1, m_dist, angle_rad, flip, 0.0, 0.0, 0.0, 0.0)
        feat = True
    elif chamfer_type == "equal_distance":
        # FeatureChamferType: Type=4 (swChamferEqualDistance), d1=Width
        _safe_variant_call(model.FeatureChamferType,
                           4, m_dist, 0.0, flip, 0.0, 0.0, 0.0, 0.0)
        feat = True
    elif chamfer_type == "distance_distance":
        # FeatureChamferType: Type=2, Width=d1, Angle=d2, Flip, OtherDist=0
        _safe_variant_call(model.FeatureChamferType,
                           2, m_dist, m_dist2, flip, 0.0, 0.0, 0.0, 0.0)
        feat = True  # void method, no return value
    elif chamfer_type == "vertex":
        m_angle_as_d3 = mm_to_m(angle)  # angle 字段用作第三边距离
        _safe_variant_call(model.FeatureChamferType,
                           3, 0.0, 0.0, flip, 0.0,
                           m_dist, m_dist2, m_angle_as_d3)
        feat = True
    else:
        return f"❌ 未知倒角类型: {chamfer_type}"

    if feat is None:
        return f"❌ 倒角失败（请确认已选中正确的边）"

    # 描述
    ctype_labels = {
        "angle_distance": f"{distance}mm × {angle}°",
        "equal_distance": f"{distance}mm (等距)",
        "distance_distance": f"{distance}mm × {distance2}mm",
        "vertex": f"顶点: {distance}mm × {distance2}mm × {angle}mm",
    }
    desc = ctype_labels.get(chamfer_type, chamfer_type)
    flip_s = " (翻转)" if flip else ""
    return f"✅ 倒角完成: {desc}{flip_s}"
