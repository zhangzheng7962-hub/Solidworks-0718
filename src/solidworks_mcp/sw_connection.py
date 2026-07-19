"""SOLIDWORKS COM 连接管理 (comtypes — 强类型 COM 绑定)"""

import comtypes.client

# 导入公共基类
from common.connection_base import ConnectionBase

# 注意: 不能在模块顶层 `from comtypes.gen import SldWorks` ——
# comtypes.gen.SldWorks 是 comtypes 首次连接 SW COM 对象时自动生成的缓存，
# 全新机器上还不存在，顶层导入会直接 ImportError 导致服务无法启动。
# 因此统一在连接建立后按需导入（见 _sldworks()）。


def _sldworks():
    """获取 comtypes 生成的 SldWorks 强类型模块（连接建立后才可用）"""
    from comtypes.gen import SldWorks
    return SldWorks


class SWConnection(ConnectionBase):
    """SOLIDWORKS 应用程序连接管理器"""

    def __init__(self):
        super().__init__()

    def _get_app_name(self) -> str:
        """返回应用程序名称"""
        return "SOLIDWORKS"

    def _get_version(self) -> str:
        """获取版本号"""
        version = self._app.RevisionNumber()
        return version.strip() if isinstance(version, str) else version

    def _is_alive(self):
        """检测连接是否有效

        执行 RevisionNumber() 轻量 COM 调用检测指针是否悬空。
        """
        self._app.RevisionNumber()

    def _get_active_object(self):
        """获取已运行的 SOLIDWORKS COM 对象

        comtypes 会在此处自动从 SW 类型库生成 comtypes.gen.SldWorks 缓存。
        """
        return comtypes.client.GetActiveObject("SldWorks.Application")

    def _create_object(self):
        """创建新的 SOLIDWORKS COM 对象"""
        return comtypes.client.CreateObject("SldWorks.Application")

    def _set_visible(self, visible: bool):
        """设置 SOLIDWORKS 可见性"""
        self._app.Visible = visible

    def _get_active_document_name(self) -> str:
        """获取当前活动文档名称"""
        active_doc = self._app.ActiveDoc
        if active_doc:
            model = active_doc.QueryInterface(_sldworks().IModelDoc2)
            return model.GetTitle()
        return "无"

    def get_active_doc(self):
        """获取当前活跃文档 (IPartDoc/IAssemblyDoc/IDrawingDoc)"""
        try:
            return self._app.ActiveDoc
        except Exception:
            return None

    def get_model(self):
        """获取 IModelDoc2 接口 — 所有文档对象的通用 API 接口

        IPartDoc/IAssemblyDoc/IDrawingDoc 都实现了 IModelDoc2，
        通过 QueryInterface 获取通用接口以调用 Extension, SketchManager 等。

        访问前验证连接有效性，防止 SW 重启后 COM 指针悬空。
        """
        if not self._connected or self._app is None:
            return None
        try:
            self._is_alive()  # 轻量存活检查
        except Exception:
            self._connected = False
            self._app = None
            return None

        doc = self.get_active_doc()
        if doc is None:
            return None
        return doc.QueryInterface(_sldworks().IModelDoc2)


# 全局连接实例
connection = SWConnection()
