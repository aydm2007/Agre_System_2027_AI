from dataclasses import dataclass, field
from typing import Any, Optional, Generic, TypeVar

T = TypeVar('T')

@dataclass(frozen=True)
class ServiceResult(Generic[T]):
    success: bool
    data: Optional[T] = None
    errors: dict[str, Any] = field(default_factory=dict)
    message: str = ""

    @classmethod
    def ok(cls, data: T, message: str = "Success") -> 'ServiceResult[T]':
        return cls(success=True, data=data, message=message)

    @classmethod
    def fail(cls, message: str, errors: dict[str, Any] = None) -> 'ServiceResult[Any]':
        return cls(success=False, errors=errors or {}, message=message)

    def __getattr__(self, item: str):
        if self.success and self.data is not None and hasattr(self.data, item):
            return getattr(self.data, item)
        raise AttributeError(item)

class BaseService:
    """Base class for all ERP services providing common utilities."""
    pass
