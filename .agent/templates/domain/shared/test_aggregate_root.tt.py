"""
Template canónico para Pruebas Unitarias de AggregateRoot.
Reglas:
- Verifica acumulación de eventos y vaciado de eventos mediante pull_events().
"""

from src.domain.shared.aggregate_root import AggregateRoot


class DummyAggregate(AggregateRoot):
    pass


def test_aggregate_root_records_and_pulls_events() -> None:
    aggregate = DummyAggregate()
    aggregate.record_event({"type": "TestEvent"})

    events = aggregate.pull_events()
    assert len(events) == 1
    assert events[0] == {"type": "TestEvent"}

    # Garantizar que se limpiaron los eventos tras el pull
    assert len(aggregate.pull_events()) == 0
