"""COM 工具函数 — 提取重复的 COM 相关代码"""

from __future__ import annotations

import ctypes
from typing import Any, Callable, TypeVar

T = TypeVar('T')


def safe_variant_call(func: Callable[..., T], *args: Any) -> T | None:
    """安全调用返回 VARIANT 数组的 COM 方法。

    comtypes 处理 VARIANT* out 参数时，若返回类型为
    VT_DISPATCH|VT_ARRAY 会因 _vartype_to_ctype 缺失映射而抛 KeyError。
    实际 COM 方法已执行成功，只需要抑制这个 Python 端解析错误。

    Args:
        func: COM 方法
        *args: 方法参数

    Returns:
        方法返回值，或 None（如果发生 KeyError）
    """
    try:
        return func(*args)
    except KeyError:
        # comtypes VARIANT out-param 转换 bug，方法调用本身已成功
        return None


def patch_comtypes_dispatch() -> None:
    """Monkey-patch comtypes: 添加 VT_DISPATCH(9) → POINTER(IDispatch) 映射。

    comtypes 无法解析 VT_ARRAY|VT_DISPATCH 类型的 VARIANT out 参数，
    会抛 KeyError: 9。SW API 的 GetBodies2/GetEdges 等方法返回此类型。

    必须在模块顶部调用此函数，确保每个使用 SW API 的模块都包含。

    Example:
        >>> from common.com_utils import patch_comtypes_dispatch
        >>> patch_comtypes_dispatch()  # 在模块顶部调用
    """
    try:
        from comtypes.automation import _vartype_to_ctype, VT_DISPATCH, VT_ARRAY
        _vartype_to_ctype.setdefault(VT_DISPATCH, ctypes.POINTER(__import__("comtypes").IUnknown))
        _vartype_to_ctype.setdefault(VT_ARRAY | VT_DISPATCH, ctypes.POINTER(__import__("comtypes").IUnknown))
    except Exception:
        pass
