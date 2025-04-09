from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FtlResource:
    """
    Represents an (unparsed) FTL file (contents and optional filename)
    """

    text: str
    filename: str | None = None

    @classmethod
    def from_string(cls, text):
        return cls(text)

    @classmethod
    def from_file(cls, filename, encoding="utf-8"):
        with open(filename, "rb") as f:
            return cls(text=f.read().decode(encoding), filename=filename)
