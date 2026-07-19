"""连接管理器基类 — 提取 SOLIDWORKS 和 AutoCAD 连接管理器的公共逻辑"""

from abc import ABC, abstractmethod


class ConnectionBase(ABC):
    """CAD 应用程序连接管理器基类

    提供通用的连接管理逻辑：
    - 连接状态跟踪
    - 自动重连检测
    - 统一的接口规范

    子类需要实现：
    - _get_app_name(): 返回应用程序名称
    - _get_version(): 获取版本号
    - _is_alive(): 检测连接是否有效
    - _create_object(): 创建新的 COM 对象
    - _get_active_object(): 获取已运行的 COM 对象
    """

    def __init__(self):
        self._app = None
        self._connected = False

    @property
    def app(self):
        """获取应用程序接口指针，自动验证连接有效性

        每次访问时执行轻量 COM 调用检测指针是否悬空。
        应用程序关闭后 COM 指针失效，再次访问时自动标记断开并抛出异常。

        Returns:
            应用程序接口指针

        Raises:
            RuntimeError: 连接已断开或未连接
        """
        if not self._connected or self._app is None:
            raise RuntimeError(f"未连接到 {self._get_app_name()}，请先调用连接命令")
        # 轻量 COM 调用验证指针有效性
        try:
            self._is_alive()
        except Exception:
            self._connected = False
            self._app = None
            raise RuntimeError(
                f"{self._get_app_name()} 连接已断开（COM 指针失效），请重新调用连接命令"
            )
        return self._app

    @property
    def connected(self) -> bool:
        """检查是否已连接

        Returns:
            True 如果已连接，False 否则
        """
        return self._connected

    def connect(self) -> dict:
        """连接到应用程序实例（先尝试附加已运行的，失败则启动新的）

        Returns:
            连接结果字典：
            - success: bool
            - message: str
            - version: str (仅成功时)

        Example:
            >>> conn = SWConnection()
            >>> result = conn.connect()
            >>> print(result["success"])
            True
        """
        try:
            # 尝试附加已运行的实例
            try:
                self._app = self._get_active_object()
            except OSError:
                # 没有运行的实例，创建新的
                self._app = self._create_object()
                self._set_visible(True)

            self._connected = True
            version = self._get_version()

            return {
                "success": True,
                "message": f"已连接到 {self._get_app_name()}",
                "version": version,
            }
        except Exception as e:
            self._connected = False
            return {
                "success": False,
                "message": f"连接失败: {str(e)}",
            }

    def disconnect(self):
        """断开连接（不关闭应用程序）"""
        self._app = None
        self._connected = False

    def get_status(self) -> dict:
        """获取连接状态

        Returns:
            状态字典：
            - connected: bool
            - message: str
            - version: str (仅连接时)
            - active_document: str (仅连接时)
        """
        if not self._connected:
            return {"connected": False, "message": "未连接"}

        try:
            version = self._get_version()
            active_doc = self._get_active_document_name()
            return {
                "connected": True,
                "version": version,
                "active_document": active_doc,
            }
        except Exception as e:
            self._connected = False
            return {"connected": False, "message": f"连接已断开: {str(e)}"}

    @abstractmethod
    def _get_app_name(self) -> str:
        """返回应用程序名称

        Returns:
            应用程序名称，如 "SOLIDWORKS" 或 "AutoCAD"
        """
        pass

    @abstractmethod
    def _get_version(self) -> str:
        """获取版本号

        Returns:
            版本号字符串
        """
        pass

    @abstractmethod
    def _is_alive(self):
        """检测连接是否有效

        执行轻量 COM 调用，如果连接断开会抛出异常。
        """
        pass

    @abstractmethod
    def _get_active_object(self):
        """获取已运行的 COM 对象

        Returns:
            COM 对象

        Raises:
            OSError: 没有运行的实例
        """
        pass

    @abstractmethod
    def _create_object(self):
        """创建新的 COM 对象

        Returns:
            COM 对象
        """
        pass

    @abstractmethod
    def _set_visible(self, visible: bool):
        """设置应用程序可见性

        Args:
            visible: True 显示，False 隐藏
        """
        pass

    @abstractmethod
    def _get_active_document_name(self) -> str:
        """获取当前活动文档名称

        Returns:
            文档名称，如果没有活动文档返回 "无"
        """
        pass

    @abstractmethod
    def get_active_doc(self):
        """获取当前活动文档

        Returns:
            文档对象，如果没有活动文档返回 None
        """
        pass
