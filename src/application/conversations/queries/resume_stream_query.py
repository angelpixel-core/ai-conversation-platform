"""Resume stream query DTO."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ResumeStreamQuery:
    """Query DTO for requesting resumption of a conversational stream."""

    stream_id: str
    last_event_id: int | None = None

    def __post_init__(self) -> None:
        if not self.stream_id or not self.stream_id.strip():
            raise ValueError("stream_id cannot be empty.")
        if self.last_event_id is not None and self.last_event_id < -1:
            raise ValueError("last_event_id must be >= -1.")
