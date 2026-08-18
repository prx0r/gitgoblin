from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable

from gitgoblin.models import Entity, Observation


class Collector(ABC):
    source_name: str
    source_family: str

    @abstractmethod
    def collect(self, *args, **kwargs) -> tuple[list[Entity], list[Observation]]:
        """Return normalized entities and observations; network failures must raise."""
        raise NotImplementedError
