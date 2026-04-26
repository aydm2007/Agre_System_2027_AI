from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ConnectorDescriptor:
    name: str
    ready: bool
    mode: str
    notes: str

    def to_dict(self) -> dict[str, str | bool]:
        return {
            'name': self.name,
            'ready': self.ready,
            'mode': self.mode,
            'notes': self.notes,
        }
