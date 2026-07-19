"""单位转换工具 — 统一的单位转换函数"""

# 转换常量
MM_TO_M = 0.001
M_TO_MM = 1000.0


def mm_to_m(mm: float) -> float:
    """毫米转米（SOLIDWORKS/AutoCAD 内部单位是米）

    Args:
        mm: 毫米值

    Returns:
        米值

    Example:
        >>> mm_to_m(100)
        0.1
        >>> mm_to_m(1000)
        1.0
    """
    return mm * MM_TO_M


def m_to_mm(m: float) -> float:
    """米转毫米

    Args:
        m: 米值

    Returns:
        毫米值

    Example:
        >>> m_to_mm(0.1)
        100.0
        >>> m_to_mm(1.0)
        1000.0
    """
    return m * M_TO_MM
