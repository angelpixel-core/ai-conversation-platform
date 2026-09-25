import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, Field

from src.domain.shared.aggregate_root import AggregateRoot


class DummyEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    occurred_on: datetime = Field(default_factory=lambda: datetime.now(UTC))
    name: str = "dummy_event"


class DummyAggregate(AggregateRoot):
    def __init__(self, entity_id: str):
        super().__init__()
        self.id = entity_id

    def do_something(self):
        self.record_event(DummyEvent())


def test_aggregate_root_initializes_with_no_events():
    aggregate = DummyAggregate(entity_id="test-1")
    assert len(aggregate.pull_events()) == 0


def test_aggregate_root_records_and_pulls_events():
    aggregate = DummyAggregate(entity_id="test-1")
    aggregate.do_something()

    events = aggregate.pull_events()
    assert len(events) == 1
    assert events[0].name == "dummy_event"


def test_pull_events_clears_the_list():
    aggregate = DummyAggregate(entity_id="test-1")
    aggregate.do_something()

    aggregate.pull_events()

    # Second pull should be empty
    events_after_pull = aggregate.pull_events()
    assert len(events_after_pull) == 0
