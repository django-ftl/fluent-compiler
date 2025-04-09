try:
    from enum import StrEnum
except ImportError:
    from backports.strenum import StrEnum  # type: ignore[reportMissingImports]

try:
    from typing import TypeAlias
except ImportError:
    from typing_extensions import TypeAlias  # type: ignore[reportMissingImports]

__all__ = ["StrEnum", "TypeAlias"]
