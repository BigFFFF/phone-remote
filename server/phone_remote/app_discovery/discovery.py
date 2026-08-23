from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import Protocol

from .app_paths import AppPathsProvider
from .known_apps import apply_known_app
from .models import DiscoveredApp, candidate_identity
from .msix import MsixProvider
from .registry import RegistryProvider
from .start_menu import StartMenuProvider


class Provider(Protocol):
    source: str

    def discover(self) -> list[DiscoveredApp]: ...


class ApplicationDiscovery:
    def __init__(
        self,
        providers: Iterable[Provider] | None = None,
        logger: logging.Logger | None = None,
    ):
        self.providers = list(
            (
                StartMenuProvider(),
                AppPathsProvider(),
                RegistryProvider(),
                MsixProvider(),
            )
            if providers is None
            else providers
        )
        self.logger = logger or logging.getLogger("phone_remote.app_discovery")

    def scan(self) -> list[DiscoveredApp]:
        collected = []
        for provider in self.providers:
            try:
                collected.extend(provider.discover())
            except Exception:
                self.logger.exception(
                    "application discovery provider failed source=%s", provider.source
                )
        return merge_candidates(collected)


def merge_candidates(candidates: Iterable[DiscoveredApp]) -> list[DiscoveredApp]:
    merged: dict[str, DiscoveredApp] = {}
    for candidate in candidates:
        identity = candidate_identity(candidate)
        existing = merged.get(identity)
        if existing is None:
            candidate.sources = sorted(set(candidate.sources or [candidate.source]))
            merged[identity] = apply_known_app(candidate)
            continue
        existing.sources = sorted(set([*existing.sources, candidate.source, *candidate.sources]))
        if candidate.confidence > existing.confidence:
            candidate.sources = existing.sources
            merged[identity] = apply_known_app(candidate)
        elif not existing.icon and candidate.icon:
            existing.icon = candidate.icon
        if not existing.known_app_id:
            apply_known_app(existing)
    return sorted(
        merged.values(),
        key=lambda item: (-item.confidence, item.name.casefold(), item.discovery_id),
    )
