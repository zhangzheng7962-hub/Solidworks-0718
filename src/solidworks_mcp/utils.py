"""通用工具函数"""

from enum import IntEnum


class swDocType(IntEnum):
    """SOLIDWORKS 文档类型"""
    PART = 1        # swDocPART
    ASSEMBLY = 2    # swDocASSEMBLY
    DRAWING = 3     # swDocDRAWING


class swSelectType(IntEnum):
    """SOLIDWORKS 选择类型"""
    FACES = 2
    EDGES = 1
    VERTICES = 3
    PLANES = 4
    DATUMPLANES = 4
    SKETCHES = 9
    SKETCHPOINTS = 1
    SKETCHSEGMENTS = 1
    FEATURES = 7


class swPlane(IntEnum):
    """SOLIDWORKS 基准面"""
    FRONT = 1       # 前视基准面
    TOP = 2         # 上视基准面
    RIGHT = 3       # 右视基准面


# 文档类型到文件扩展名的映射
DOC_EXTENSIONS = {
    swDocType.PART: ".sldprt",
    swDocType.ASSEMBLY: ".sldasm",
    swDocType.DRAWING: ".slddrw",
}

# 常用单位转换
MM_TO_M = 0.001
M_TO_MM = 1000.0


def mm_to_m(mm: float) -> float:
    """毫米转米（SOLIDWORKS 内部单位是米）"""
    return mm * MM_TO_M


def m_to_mm(m: float) -> float:
    """米转毫米"""
    return m * M_TO_MM


def safe_call(func, *args, default=None):
    """安全调用 COM 方法，捕获异常"""
    try:
        return func(*args)
    except Exception:
        return default


def ensure_callable(obj, *names):
    """确保 comtypes 动态 _Dispatch 对象的无参方法可被 () 调用。

    comtypes 将无参 COM 方法默认为 property，调用 obj.Method() 会报
    'str not callable' 等错误。_FlagAsMethod 标记后 () 才触发 DISPATCH_METHOD。
    对已标记或非 _Dispatch 对象安全跳过。
    """
    for name in names:
        try:
            obj._FlagAsMethod(name)
        except Exception:
            pass
