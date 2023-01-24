import pytest

from clarin.sru.constants import SRUDiagnostics
from clarin.sru.diagnostic import SRUDiagnostic
from clarin.sru.exception import SRUException

# ---------------------------------------------------------------------------


def test_SRUDiagnostic():
    with pytest.raises(TypeError):
        diag = SRUDiagnostic()

    diag = SRUDiagnostic("my-uri")
    assert diag.uri == "my-uri"
    assert diag.message is None
    assert diag.details is None

    # best to supply the URI via Enum
    diag = SRUDiagnostic(SRUDiagnostics.GENERAL_SYSTEM_ERROR)
    assert diag.uri == SRUDiagnostics.GENERAL_SYSTEM_ERROR.value
    assert isinstance(diag.uri, str)
    assert SRUDiagnostics in diag.uri.__class__.mro()
    assert str in diag.uri.__class__.mro()
    # message is set by Enum description
    assert diag.message == SRUDiagnostics.GENERAL_SYSTEM_ERROR.description
    assert diag.details is None

    # but can supply just the URI as string
    diag = SRUDiagnostic(SRUDiagnostics.GENERAL_SYSTEM_ERROR.value)
    assert diag.uri == SRUDiagnostics.GENERAL_SYSTEM_ERROR.value
    assert isinstance(diag.uri, str)
    assert SRUDiagnostics not in diag.uri.__class__.mro()
    assert str in diag.uri.__class__.mro()
    assert diag.message == SRUDiagnostics.GENERAL_SYSTEM_ERROR.description
    assert diag.details is None

    # overwrite message (don't use default)
    diag = SRUDiagnostic(SRUDiagnostics.GENERAL_SYSTEM_ERROR, message="test")
    assert diag.uri == SRUDiagnostics.GENERAL_SYSTEM_ERROR.value
    assert diag.message == "test"
    assert diag.details is None

    diag = SRUDiagnostic(
        SRUDiagnostics.GENERAL_SYSTEM_ERROR, details="abc", message="test"
    )
    assert diag.uri == SRUDiagnostics.GENERAL_SYSTEM_ERROR.value
    assert diag.message == "test"
    assert diag.details == "abc"

    diag = SRUDiagnostic(SRUDiagnostics.GENERAL_SYSTEM_ERROR, details="abc")
    assert diag.uri == SRUDiagnostics.GENERAL_SYSTEM_ERROR.value
    assert diag.message == SRUDiagnostics.GENERAL_SYSTEM_ERROR.description
    assert diag.details == "abc"


def test_diagnostic_from_error():
    exc = SRUException(
        SRUDiagnostics.AUTHENTICATION_ERROR, details="abc", message="def"
    )
    diag = exc.get_diagnostic()
    assert diag.uri == SRUDiagnostics.AUTHENTICATION_ERROR
    assert diag.details == "abc"
    assert diag.message == "def"

    exc = SRUException(SRUDiagnostics.AUTHENTICATION_ERROR)
    diag = exc.get_diagnostic()
    assert diag.uri == SRUDiagnostics.AUTHENTICATION_ERROR
    assert diag.details is None
    assert diag.message == SRUDiagnostics.AUTHENTICATION_ERROR.description


# ---------------------------------------------------------------------------
