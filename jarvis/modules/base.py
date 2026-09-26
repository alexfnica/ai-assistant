from dataclasses import dataclass


@dataclass(frozen=True)
class Module:
    id: str
    label: str
    description: str
    example: str
