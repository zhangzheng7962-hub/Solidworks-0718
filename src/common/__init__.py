"""公共工具模块 — COM 工具 / 连接管理 / 单位转换"""

from .com_utils import safe_variant_call, patch_comtypes_dispatch
from .connection_base import ConnectionBase
from .unit_utils import mm_to_m, m_to_mm, MM_TO_M, M_TO_MM

__all__ = [
    # COM 工具
    'safe_variant_call',
    'patch_comtypes_dispatch',

    # 连接管理
    'ConnectionBase',

    # 单位转换
    'mm_to_m',
    'm_to_mm',
    'MM_TO_M',
    'M_TO_MM',
]
