from contextlib import contextmanager
from collections.abc import Iterator


class Telemetry:
    """Minimal telemetry abstraction.

    This intentionally avoids coupling the application to OpenTelemetry yet.
    An OpenTelemetry adapter can implement the same boundary later.
    """

    @contextmanager
    def span(self, name: str) -> Iterator[None]:
        yield
