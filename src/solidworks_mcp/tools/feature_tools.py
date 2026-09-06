"""特征工具 — 拉伸凸台 / 拉伸切除"""

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
