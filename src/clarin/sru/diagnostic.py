from abc import ABCMeta
from abc import abstractmethod
from dataclasses import dataclass
from typing import Optional

from . import constants

# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SRUDiagnostic:
    """Class to hold a SRU diagnostic.

    See also:
        * SRU Diagnostics: http://www.loc.gov/standards/sru/diagnostics/
        * SRU Diagnostics List: http://www.loc.gov/standards/sru/diagnostics/diagnosticsList.html
    """

    uri: str
    """Diagnostic's identifying URI."""

    details: Optional[str] = None
    """Supplementary information available, often in a format
    specified by the diagnostic or ``None``."""

    message: Optional[str] = None
    """Human readable message to display to the end user or ``None``."""

    def __post_init__(self):
        if not self.message or not self.message.strip():
            object.__setattr__(
                self, "message", self.get_default_error_message(self.uri)
            )

    @staticmethod
    def get_default_error_message(uri: str):
        diag = constants.SRUDiagnostics.get_by_uri(uri)
        if diag:
            return diag.description
        return None


# ---------------------------------------------------------------------------


class SRUDiagnosticList(metaclass=ABCMeta):
    """Container for non surrogate diagnostics for the request. The
    will be put in the ``diagnostics`` part of the response."""

    @abstractmethod
    def add_diagnostic(
        self, uri: str, details: Optional[str] = None, message: Optional[str] = None
    ) -> None:
        """Add a non surrogate diagnostic to the response.

        Args:
            uri: the diagnostic's identifying URI
            details: supplementary information available, often
                in a format specified by the diagnostic or ``None``
            message: human readable message to display to the
                end user or ``None``
        """


# ---------------------------------------------------------------------------
