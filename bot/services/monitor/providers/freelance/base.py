from __future__ import annotations

from typing import TypedDict


class FreelanceOpportunity(TypedDict):
    title: str
    client_or_company: str
    platform: str
    budget: str
    skills: list[str]
    location: str
    remote: bool
    url: str
    external_id: str

