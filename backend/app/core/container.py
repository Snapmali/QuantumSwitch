"""Dependency injection container for managing global service instances."""
import threading
from typing import Optional, Type, TypeVar, Dict, Any, Callable

T = TypeVar('T')


class ServiceNotRegisteredError(Exception):
    """Service not registered error."""
    pass


class CircularDependencyError(Exception):
    """Circular dependency error."""
    pass


class Container:
    """
    Lightweight dependency injection container.

    Features:
    - Singleton lifecycle management
    - Lazy initialization
    - Circular dependency detection
    - Thread-safe
    """

    def __init__(self):
        self._registrations: Dict[Type, Callable[[], Any]] = {}
        self._singletons: Dict[Type, Any] = {}
        self._locks: Dict[Type, threading.Lock] = {}
        self._resolving: set = set()  # For circular dependency detection

    def register_singleton(self, interface: Type[T], factory: Callable[[], T]) -> None:
        """
        Register a singleton service.

        Args:
            interface: Service interface/type
            factory: Factory function to create instance
        """
        self._registrations[interface] = factory
        self._locks[interface] = threading.Lock()

    def register_instance(self, interface: Type[T], instance: T) -> None:
        """
        Register a pre-created instance directly.

        Args:
            interface: Service interface/type
            instance: Service instance
        """
        self._singletons[interface] = instance

    def resolve(self, interface: Type[T]) -> T:
        """
        Resolve a service instance.

        Args:
            interface: Service type to resolve

        Returns:
            Service instance

        Raises:
            ServiceNotRegisteredError: Service not registered
            CircularDependencyError: Circular dependency detected
        """
        # Check if instance already exists
        if interface in self._singletons:
            return self._singletons[interface]

        # Check if registered
        if interface not in self._registrations:
            raise ServiceNotRegisteredError(f"Service {interface.__name__} not registered")

        # Circular dependency detection
        if interface in self._resolving:
            raise CircularDependencyError(f"Circular dependency detected: {interface.__name__}")

        # Create instance (thread-safe)
        self._resolving.add(interface)
        try:
            with self._locks[interface]:
                # Double-check
                if interface not in self._singletons:
                    factory = self._registrations[interface]
                    self._singletons[interface] = factory()
            return self._singletons[interface]
        finally:
            self._resolving.discard(interface)

    def clear(self) -> None:
        """Clear all registrations and instances (mainly for testing)."""
        self._singletons.clear()
        self._resolving.clear()


# Global container instance
_container: Optional[Container] = None
_container_lock = threading.Lock()


def get_container() -> Container:
    """Get global container instance (singleton)."""
    global _container
    if _container is None:
        with _container_lock:
            if _container is None:
                _container = Container()
    return _container


def reset_container() -> None:
    """Reset container (mainly for testing)."""
    global _container
    with _container_lock:
        _container = None


def inject(interface: Type[T]) -> T:
    """
    Convenient dependency injection function.

    Example:
        pm = inject(ProcessManager)
    """
    return get_container().resolve(interface)
