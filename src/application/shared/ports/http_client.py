from abc import ABC, abstractmethod
from typing import Any


class HttpClient(ABC):
    """Outbound HTTP port.

    AI provider adapters will depend on this abstraction instead of a concrete
    HTTP library, making provider integrations easy to test.
    """

    @abstractmethod
    async def request(self, method: str, url: str, **kwargs: Any) -> Any:
        raise NotImplementedError
