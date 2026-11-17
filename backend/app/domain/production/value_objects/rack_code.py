"""Value object: Rack / container code."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RackCode:
    value: str

    def __post_init__(self) -> None:
        cleaned = (self.value or "").strip()
        if not cleaned:
            raise ValueError("Mã rack (container_code) không được để trống.")
        object.__setattr__(self, "value", cleaned)

    def __str__(self) -> str:
        return self.value
