"""依赖注入容器，统一管理全局服务实例。"""
from typing import Optional, Type, TypeVar, Dict, Any, Callable
from functools import wraps
import threading

T = TypeVar('T')


class ServiceNotRegisteredError(Exception):
    """服务未注册错误。"""
    pass


class CircularDependencyError(Exception):
    """循环依赖错误。"""
    pass


class Container:
    """
    轻量级依赖注入容器。

    特性：
    - 单例生命周期管理
    - 延迟初始化
    - 循环依赖检测
    - 线程安全
    """

    def __init__(self):
        self._registrations: Dict[Type, Callable[[], Any]] = {}
        self._singletons: Dict[Type, Any] = {}
        self._locks: Dict[Type, threading.Lock] = {}
        self._resolving: set = set()  # 用于循环依赖检测

    def register_singleton(self, interface: Type[T], factory: Callable[[], T]) -> None:
        """
        注册单例服务。

        Args:
            interface: 服务接口/类型
            factory: 创建实例的工厂函数
        """
        self._registrations[interface] = factory
        self._locks[interface] = threading.Lock()

    def register_instance(self, interface: Type[T], instance: T) -> None:
        """
        直接注册已创建的实例。

        Args:
            interface: 服务接口/类型
            instance: 服务实例
        """
        self._singletons[interface] = instance

    def resolve(self, interface: Type[T]) -> T:
        """
        解析服务实例。

        Args:
            interface: 要解析的服务类型

        Returns:
            服务实例

        Raises:
            ServiceNotRegisteredError: 服务未注册
            CircularDependencyError: 检测到循环依赖
        """
        # 检查是否已有实例
        if interface in self._singletons:
            return self._singletons[interface]

        # 检查是否已注册
        if interface not in self._registrations:
            raise ServiceNotRegisteredError(f"服务 {interface.__name__} 未注册")

        # 循环依赖检测
        if interface in self._resolving:
            raise CircularDependencyError(f"检测到循环依赖: {interface.__name__}")

        # 创建实例（线程安全）
        self._resolving.add(interface)
        try:
            with self._locks[interface]:
                # 双重检查
                if interface not in self._singletons:
                    factory = self._registrations[interface]
                    self._singletons[interface] = factory()
            return self._singletons[interface]
        finally:
            self._resolving.discard(interface)

    def clear(self) -> None:
        """清空所有注册和实例（主要用于测试）。"""
        self._singletons.clear()
        self._resolving.clear()


# 全局容器实例
_container: Optional[Container] = None
_container_lock = threading.Lock()


def get_container() -> Container:
    """获取全局容器实例（单例）。"""
    global _container
    if _container is None:
        with _container_lock:
            if _container is None:
                _container = Container()
    return _container


def reset_container() -> None:
    """重置容器（主要用于测试）。"""
    global _container
    with _container_lock:
        _container = None


def inject(interface: Type[T]) -> T:
    """
    便捷的依赖注入函数。

    示例:
        pm = inject(ProcessManager)
    """
    return get_container().resolve(interface)
