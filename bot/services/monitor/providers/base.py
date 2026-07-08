from __future__ import annotations

from typing import NotRequired, TypedDict


class JobProviderFilters(TypedDict, total=False):
    areas: list[str]
    levels: list[str]
    models: list[str]


class JobProviderResult(TypedDict):
    title: str
    company: str
    location: str
    remote: str
    technologies: list[str]
    url: str
    source: str
    external_id: str
    region: NotRequired[str]
    seniority: NotRequired[str]
