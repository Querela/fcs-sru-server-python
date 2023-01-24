from abc import ABCMeta
from abc import abstractmethod
from typing import Dict
from typing import Optional

from werkzeug import Request

# ---------------------------------------------------------------------------


class SRUAuthenticationInfo(metaclass=ABCMeta):
    @property
    @abstractmethod
    def authentication_method(self) -> str:
        pass

    @property
    @abstractmethod
    def subject(self) -> str:
        pass


# ---------------------------------------------------------------------------


class SRUAuthenticationInfoProvider(metaclass=ABCMeta):
    @abstractmethod
    def get_AuthenticationInfo(
        self, request: Request
    ) -> Optional[SRUAuthenticationInfo]:
        # TODO: create wrapper around werkzeug.Request to allow more backends
        # TODO: or just use request headers as dict?
        pass


# ---------------------------------------------------------------------------


class SRUAuthenticationInfoProviderFactory(metaclass=ABCMeta):
    @abstractmethod
    def create_SRUAuthenticationInfoProvider(
        self, params: Dict[str, str]
    ) -> Optional[SRUAuthenticationInfoProvider]:
        """Create a authentication info provider."""
        pass


# ---------------------------------------------------------------------------
