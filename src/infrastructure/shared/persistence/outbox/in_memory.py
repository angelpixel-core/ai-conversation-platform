class InMemoryOutbox:
    """Local outbox placeholder.

    PostgreSQL implementation should persist outbox records in the same
    transaction as aggregate state to preserve atomicity.
    """

    def __init__(self) -> None:
        self.messages: list[object] = []

    def add(self, event: object) -> None:
        self.messages.append(event)
