"""Base class for detection backends."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from detection.element_model import DetectedElement


class DetectionBackend(ABC):
    """Interface each detection backend must implement."""

    name: str = "base"

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if this backend can run on the current system."""

    @abstractmethod
    def list_elements(
        self,
        window_title: Optional[str] = None,
        max_depth: int = 5,
        role: Optional[str] = None,
        tree_mode: str = "control",
        include_offscreen: bool = False,
    ) -> list[DetectedElement]:
        ...

    @abstractmethod
    def find_elements(
        self,
        name: Optional[str] = None,
        role: Optional[str] = None,
        automation_id: Optional[str] = None,
        class_name: Optional[str] = None,
        window_title: Optional[str] = None,
        tree_mode: str = "control",
        include_offscreen: bool = False,
        index: int = 0,
    ) -> list[DetectedElement]:
        ...

    def element_at_point(self, x: int, y: int) -> Optional[DetectedElement]:
        return None

    def get_properties(self, element: DetectedElement) -> dict:
        return element.to_dict()
