"""外观工具 — 颜色、透明度等"""

import array
from ..sw_connection import connection
from ..utils import ensure_callable

# 导入公共模块
from common.com_utils import patch_comtypes_dispatch
from common.unit_utils import mm_to_m

# Monkey-patch comtypes（必须在模块顶部调用）
patch_comtypes_dispatch()


# 特征名缓存：避免每次上色都遍历特征树
_feature_cache: dict[str, object] = {}


def _build_feature_cache(model):
    """构建特征名→特征对象的缓存"""
    global _feature_cache
    if _feature_cache:
        return
    from comtypes.gen import SldWorks as SW
    feat = model.FirstFeature()
    while feat:
        try:
            cur = feat.QueryInterface(SW.IFeature)
            if cur and cur.Name:
                _feature_cache[cur.Name] = cur
            nxt = cur.GetNextFeature() if cur else None
            feat = nxt
        except Exception:
            break


def _get_model():
    """获取 IModelDoc2 接口，无文档时抛异常"""
    model = connection.get_model()
    if model is None:
        raise RuntimeError("没有打开的文档，请先调用 connect_solidworks 并打开/新建文档")
    return model


def _set_color(r: int, g: int, b: int,
               feature_name: str = "", transparency: float = 0.0,
               redraw: bool = True) -> str:
    """设置特征/面的颜色。R/G/B 范围 0-255，feature_name 为空则设置整个零件颜色。

    API 参考: IModelDoc2::MaterialPropertyValues（零件级）
              IFace2::MaterialPropertyValues（面级）
              IFeature::GetFaces() → 遍历面逐个着色

    颜色数组格式: [R, G, B, Ambient, Diffuse, Specular, Shininess, Transparency, Emission]

    Args:
        redraw: 是否调用 GraphicsRedraw2()。批量上色时传 False，最后统一重绘。
    """
    global _feature_cache
    model = _get_model()
    from comtypes.gen import SldWorks as SW

    vals = [
        max(0.0, min(1.0, r / 255.0)),      # R
        max(0.0, min(1.0, g / 255.0)),      # G
        max(0.0, min(1.0, b / 255.0)),      # B
        1.0,                                  # Ambient
        1.0,                                  # Diffuse
        0.5,                                  # Specular
        0.88,                                 # Shininess
        max(0.0, min(1.0, transparency)),     # Transparency
        0.0,                                  # Emission
    ]

    if not feature_name:
        # 整个零件着色 — 遍历所有实体的所有面
        try:
            part = model.QueryInterface(SW.IPartDoc)
            bodies = part.GetBodies2(0, False)
            count = 0
            for bdisp in bodies:
                try:
                    body = bdisp.QueryInterface(SW.IBody2)
                    for fdisp in body.GetFaces():
                        try:
                            face = fdisp.QueryInterface(SW.IFace2)
                            face.MaterialPropertyValues = array.array('d', vals)
                            count += 1
                        except Exception:
                            pass
                except Exception:
                    pass
            if redraw:
                model.GraphicsRedraw2()
            _feature_cache.clear()  # 零件变更后清空缓存
            return f"✅ 零件颜色: {count} 个面 → RGB({r},{g},{b}) ≈ #{r:02x}{g:02x}{b:02x}"
        except Exception as e:
            return f"❌ 零件着色失败: {e}"

    # 特征着色: 用缓存查找特征，避免 O(n) 树遍历
    try:
        _build_feature_cache(model)
        feat = _feature_cache.get(feature_name)

        if not feat:
            # 缓存未命中，清空重建一次
            _feature_cache.clear()
            _build_feature_cache(model)
            feat = _feature_cache.get(feature_name)

        if not feat:
            return f"❌ 未找到特征: {feature_name}"

        faces = feat.GetFaces()
        if not faces:
            return f"❌ 特征 {feature_name} 无面"

        count = 0
        for fdisp in faces:
            try:
                face = fdisp.QueryInterface(SW.IFace2)
                if face:
                    face.MaterialPropertyValues = array.array('d', vals)
                    count += 1
            except Exception:
                pass

        if count > 0:
            if redraw:
                model.GraphicsRedraw2()
            return f"✅ 特征 {feature_name}: {count} 个面 → RGB({r},{g},{b})"
        return f"❌ 特征 {feature_name}: 无法着色面"
    except Exception as e:
        return f"❌ 着色失败: {e}"
