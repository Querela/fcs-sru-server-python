from typing import Dict
from typing import Optional
from typing import Union

import pytest

from clarin.sru.diagnostic import SRUDiagnosticList
from clarin.sru.server.config import SRUServerConfig
from clarin.sru.server.config import SRUServerConfigKey
from clarin.sru.server.request import SRURequest
from clarin.sru.server.result import SRUExplainResult
from clarin.sru.server.result import SRUScanResultSet
from clarin.sru.server.result import SRUSearchResultSet
from clarin.sru.xml.writer import SRUXMLStreamWriter

ConfigParamDict = Dict[Union[SRUServerConfigKey, str], str]


# ---------------------------------------------------------------------------


@pytest.fixture(scope="function")
def config_params() -> ConfigParamDict:
    # minimal required params
    return {
        SRUServerConfigKey.SRU_TRANSPORT: "http",
        SRUServerConfigKey.SRU_HOST: "localhost",
        SRUServerConfigKey.SRU_PORT: "80",
        SRUServerConfigKey.SRU_DATABASE: "test",
        SRUServerConfigKey.SRU_ALLOW_OVERRIDE_INDENT_RESPONSE: "true",
    }


# ---------------------------------------------------------------------------


def test_server(server_config_file, config_params):
    import logging

    from werkzeug.test import Client
    from werkzeug.testapp import test_app

    from clarin.sru.queryparser import SRUQueryParserRegistry
    from clarin.sru.server.server import SRUServer

    logging.basicConfig(level=logging.DEBUG)

    class FakeSE:
        def explain(self, *args, **kwargs):
            return None

    config = SRUServerConfig.parse(config_params, server_config_file)
    query_parsers = SRUQueryParserRegistry.Builder(True).build()
    server = SRUServer(config, query_parsers, FakeSE())

    client = Client(test_app)
    response = client.get(
        "?operation=explain&x-fcs-endpoint-description=true&x-indent-response=1"
    )
    request = response.request

    server.handle_request(request, response)

    print(response.get_data().decode())

    assert len(response.get_data()) == 1776


def test_server_app_check(server_config_file, config_params):
    from clarin.sru.exception import SRUConfigException
    from clarin.sru.server.wsgi import SRUServerApp

    class FakeSE:
        def explain(self, *args, **kwargs):
            return None

    err_msg = "Error creating search engine"
    err_msg2 = "Parameter 'SRUSearchEngine_clazz' not of type SRUSearchEngine"
    with pytest.raises(
        RuntimeError, match=f"error configuring or inializing the server: {err_msg}"
    ) as exc_info:
        SRUServerApp(FakeSE, server_config_file, config_params, develop=False)
    assert isinstance(exc_info.value.__cause__, SRUConfigException)
    assert exc_info.value.__cause__.args[0] == err_msg
    assert isinstance(exc_info.value.__cause__.__cause__, ValueError)
    assert exc_info.value.__cause__.__cause__.args[0] == err_msg2


def test_server_app_explain(server_config_file, config_params):
    import logging

    from werkzeug.test import Client

    from clarin.sru.server.server import SRUSearchEngine
    from clarin.sru.server.wsgi import SRUServerApp

    logging.basicConfig(level=logging.DEBUG)

    class TestSE(SRUSearchEngine):
        def explain(
            self,
            config: SRUServerConfig,
            request: SRURequest,
            diagnostics: SRUDiagnosticList,
        ) -> Optional[SRUExplainResult]:
            return None

        def scan(
            self,
            config: SRUServerConfig,
            request: SRURequest,
            diagnostics: SRUDiagnosticList,
        ) -> Optional[SRUScanResultSet]:
            return None

        def search(
            self,
            config: SRUServerConfig,
            request: SRURequest,
            diagnostics: SRUDiagnosticList,
        ) -> SRUSearchResultSet:
            return super().search(config, request, diagnostics)

    app = SRUServerApp(TestSE, server_config_file, config_params, develop=False)

    client = Client(app)

    response = client.get()
    print(response.get_data().decode())
    assert len(response.get_data()) == 1726

    response = client.get("?operation=explain&x-fcs-endpoint-description=true")
    print(response.get_data().decode())
    assert len(response.get_data()) == 1726

    response = client.get(
        "?operation=explain&x-fcs-endpoint-description=true&x-indent-response=1"
    )
    print(response.get_data().decode())
    assert len(response.get_data()) == 1943


def test_server_app_search(server_config_file, config_params):
    import logging

    from werkzeug.test import Client

    from clarin.sru.server.server import SRUSearchEngine
    from clarin.sru.server.wsgi import SRUServerApp

    logging.basicConfig(level=logging.DEBUG)

    class TestSRS(SRUSearchResultSet):
        def __init__(self, diagnostics: SRUDiagnosticList) -> None:
            super().__init__(diagnostics)
            self.is_first_result = True

        def get_record_count(self) -> int:
            return 1

        def get_record_identifier(self) -> str:
            return "t1"

        def get_record_schema_identifier(self) -> str:
            return "test"

        def get_total_record_count(self) -> int:
            return 1

        def next_record(self) -> bool:
            if self.is_first_result:
                self.is_first_result = False
                return True
            return False

        def write_record(self, writer: SRUXMLStreamWriter) -> None:
            writer.characters("test1")

    class TestSE(SRUSearchEngine):
        def explain(
            self,
            config: SRUServerConfig,
            request: SRURequest,
            diagnostics: SRUDiagnosticList,
        ) -> Optional[SRUExplainResult]:
            return None

        def scan(
            self,
            config: SRUServerConfig,
            request: SRURequest,
            diagnostics: SRUDiagnosticList,
        ) -> Optional[SRUScanResultSet]:
            return None

        def search(
            self,
            config: SRUServerConfig,
            request: SRURequest,
            diagnostics: SRUDiagnosticList,
        ) -> SRUSearchResultSet:
            return TestSRS(diagnostics)

    app = SRUServerApp(TestSE, server_config_file, config_params, develop=False)

    client = Client(app)

    response = client.get()
    print(response.get_data().decode())
    assert len(response.get_data()) == 1726

    response = client.get("?operation=searchRetrieve&query=dog&x-indent-response=1")
    data = response.get_data()
    print(data.decode())
    assert len(data) == 1101
    assert b"<sruResponse:recordData>test1</sruResponse:recordData>" in data
    assert b"<sruResponse:numberOfRecords>1</sruResponse:numberOfRecords>" in data
