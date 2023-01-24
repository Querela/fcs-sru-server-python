from typing import Optional

from .diagnostic import SRUDiagnostic

# ---------------------------------------------------------------------------


class SRUException(Exception):
    """An exception raised, if something went wrong processing the
    request. For diagnostic codes, see constants in `SRUConstant`.

    See also:
        SRUConstant
    """

    def __init__(
        self,
        uri: str,
        details: Optional[str] = None,
        message: Optional[str] = None,
        *args
    ):
        if uri is None:
            raise TypeError("uri is None")
        if not uri.strip():
            raise ValueError("uri is empty")

        super().__init__(message, *args)
        self.uri = uri
        self.details = details

    def __str__(self):
        # check whether no message was supplied
        if not self.args[0]:
            # check whether this exception was chained (raised as wrapper)
            # then use the message of the 'inner' exception
            #   e.g. with raise SRUException() from exception
            if self.__cause__:
                return self.__cause__.args[0]
            # otherwise get diagnostics message from `uri`
            return SRUDiagnostic.get_default_error_message(self.uri)
        # message was supplied to constructor
        return super().__str__()

    def get_diagnostic(self) -> SRUDiagnostic:
        """Create a SRU diagnostic from this exception."""
        return SRUDiagnostic(self.uri, self.details, self.args[0])


# ---------------------------------------------------------------------------


class SRUConfigException(Exception):
    """An exception raised, if some error occurred with the SRUServer
    configuration."""


# ---------------------------------------------------------------------------
