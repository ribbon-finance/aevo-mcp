from __future__ import annotations


def parse_int_field(value: str | int, field_name: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be integer-like") from exc
