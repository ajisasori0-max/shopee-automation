"""Shared mapping primitives for marketplace connectors and the ingestion sync engine.

These types are intentionally placed in the connector core (rather than ingestion)
because marketplace-specific mappers live in the connector context and depend on
them. The ingestion sync engine then consumes the abstract Mapper interface, which
preserves the dependency direction:

    connectors.core.mapper  (shared kernel)
         ↓        ↑
  connectors.shopee.mappers   ingestion.sync_engine
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CanonicalEntity:
    """Lightweight container for a canonical entity before persistence."""

    entity_type: str
    external_entity_id: str
    model_class: type
    data: Dict[str, Any]
    children: List["CanonicalEntity"] = field(default_factory=list)
    parent_external_id: Optional[str] = None
    parent_field: Optional[str] = None


class Mapper(ABC):
    """Abstract mapper from raw marketplace payload to canonical entity/entities."""

    @abstractmethod
    def map(self, raw_payload: Dict[str, Any]) -> List[CanonicalEntity]:
        """Map a raw payload to one or more canonical entities."""
        raise NotImplementedError
