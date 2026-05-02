from uuid import UUID, uuid4


def new_uuid() -> UUID:
    return uuid4()


def parse_uuid(value: str) -> UUID:
    try:
        return UUID(value)
    except ValueError as exc:
        raise ValueError(f"Invalid UUID: {value}") from exc
