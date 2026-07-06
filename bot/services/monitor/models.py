from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class MonitorItem:
    type: str
    title: str
    url: str
    source: str
    summary: str = ""
    metadata: dict[str, str] = field(default_factory=dict)

