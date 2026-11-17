"""Value object: Location code on the shop floor / map."""

from dataclasses import dataclass


@dataclass(frozen=True)
class LocationCode:
    value: str

    def __post_init__(self) -> None:
        cleaned = (self.value or "").strip()
        if not cleaned:
            raise ValueError("Mã vị trí (location_code) không được để trống.")
        object.__setattr__(self, "value", cleaned)

    def __str__(self) -> str:
        return self.value
