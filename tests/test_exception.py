import pytest

from clarin.sru.constants import SRUDiagnostics
from clarin.sru.exception import SRUException

# ---------------------------------------------------------------------------


def test_exception_init():
    with pytest.raises(TypeError) as exc_info:
        raise SRUException()

    with pytest.raises(ValueError) as exc_info:
        raise SRUException(" ")

    with pytest.raises(ValueError) as exc_info:
        raise SRUException("")


def test_exception_chaining():
    uri = SRUDiagnostics.GENERAL_SYSTEM_ERROR.value

    with pytest.raises(
        SRUException, match=SRUDiagnostics.GENERAL_SYSTEM_ERROR.description
    ) as exc_info:
        raise SRUException(uri)

    with pytest.raises(
        SRUException, match=SRUDiagnostics.GENERAL_SYSTEM_ERROR.description
    ) as exc_info:
        try:
            raise Exception("test124")
        except Exception as ex:
            raise SRUException(uri)

    with pytest.raises(SRUException, match="test124") as exc_info:
        try:
            raise Exception("test124")
        except Exception as ex:
            raise SRUException(uri) from ex

    with pytest.raises(SRUException, match="abc98") as exc_info:
        try:
            raise Exception("test124")
        except Exception as ex:
            raise SRUException(uri, message="abc98")

    with pytest.raises(SRUException, match="abc98") as exc_info:
        try:
            raise Exception("test124")
        except Exception as ex:
            raise SRUException(uri, message="abc98") from ex

    # invalid uri
    with pytest.raises(SRUException, match=None) as exc_info:
        raise SRUException("abc")

    with pytest.raises(SRUException, match="ttt2") as exc_info:
        raise SRUException("abc", message="ttt2")

    # missing
    with pytest.raises(TypeError):
        raise SRUException(None)
    with pytest.raises(ValueError):
        raise SRUException("")
    with pytest.raises(ValueError):
        raise SRUException("   \n ")


# ---------------------------------------------------------------------------
