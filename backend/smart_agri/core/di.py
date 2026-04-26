from typing import Dict, Type, TypeVar, Any, Optional

T = TypeVar("T")

class ServiceContainer:
    """
    Lightweight Service Container for Dependency Injection.
    Provides a simple registry for application services.
    """
    _services: Dict[Type[Any], Any] = {}

    @classmethod
    def register(cls, interface: Type[T], implementation: T) -> None:
        """Register a concrete implementation for an interface."""
        cls._services[interface] = implementation

    @classmethod
    def get(cls, interface: Type[T]) -> T:
        """Resolve a service by its interface."""
        service = cls._services.get(interface)
        if not service:
            raise KeyError(f"Service not registered for interface: {interface}")
        return service

    @classmethod
    def clear(cls) -> None:
        """Clear all registered services (useful for testing)."""
        cls._services.clear()

# Singleton instance (though class methods make it effectively global)
container = ServiceContainer
