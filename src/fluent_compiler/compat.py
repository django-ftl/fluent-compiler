try:
    from enum import StrEnum
except ImportError:
    from backports.strenum import StrEnum  # type: ignore[reportMissingImports]

__all__ = ["StrEnum"]
