import logging
import os
from typing import List
from typing import Optional

from clarin.sru.constants import SRUDiagnostics
from clarin.sru.diagnostic import SRUDiagnosticList
from clarin.sru.exception import SRUException
from clarin.sru.server.config import SRUServerConfig
from clarin.sru.server.request import SRURequest
from clarin.sru.server.result import SRUExplainResult
from clarin.sru.server.result import SRUScanResultSet
from clarin.sru.server.result import SRUSearchResultSet
from clarin.sru.server.server import SRUSearchEngine
from clarin.sru.server.wsgi import SRUServerApp
from clarin.sru.xml.writer import SRUXMLStreamWriter


class MySRUSearchResultSet(SRUSearchResultSet):
    def __init__(self, data: List[str], diagnostics: SRUDiagnosticList):
        super().__init__(diagnostics)
        self.data = data
        self.cur_record_idx = -1

    def get_total_record_count(self) -> int:
        return len(self.data)

    def get_record_count(self) -> int:
        return len(self.data)

    def get_record_schema_identifier(self) -> str:
        return "test"

    def assert_record_idx(self, raise_ex: bool = True) -> bool:
        if self.cur_record_idx == -1:
            raise SRUException(
                SRUDiagnostics.FIRST_RECORD_POSITION_OUT_OF_RANGE,
                message="Record cursor before first element!"
                " Initial call for 'next_term' required.",
            )
        if self.cur_record_idx >= len(self.data):
            if raise_ex:
                raise StopIteration("no more records")
            return False
        return True

    def next_record(self) -> bool:
        self.cur_record_idx += 1
        return self.assert_record_idx(False)

    def get_record_identifier(self) -> str:
        self.assert_record_idx()
        return f"{self.get_record_schema_identifier()}:{self.cur_record_idx}"

    def write_record(self, writer: SRUXMLStreamWriter) -> None:
        self.assert_record_idx()
        with writer.element("record", attrs={"no": str(self.cur_record_idx)}):
            writer.characters(self.data[self.cur_record_idx])


class MySRUSearchEngine(SRUSearchEngine):
    def search(
        self,
        config: SRUServerConfig,
        request: SRURequest,
        diagnostics: SRUDiagnosticList,
    ) -> SRUSearchResultSet:
        result = MySRUSearchResultSet(["a", "b"], diagnostics)
        return result

    def scan(
        self,
        config: SRUServerConfig,
        request: SRURequest,
        diagnostics: SRUDiagnosticList,
    ) -> Optional[SRUScanResultSet]:
        return None

    def explain(
        self,
        config: SRUServerConfig,
        request: SRURequest,
        diagnostics: SRUDiagnosticList,
    ) -> Optional[SRUExplainResult]:
        return None


def make_app():
    config_file = os.path.join(os.path.dirname(__file__), "./sru-server-config.xml")
    app = SRUServerApp(MySRUSearchEngine, config_file, dict(), develop=True)
    return app


if __name__ == "__main__":
    from werkzeug.serving import run_simple

    logging.basicConfig(level=logging.DEBUG)

    app = make_app()

    # use_reloader=False if debugging
    run_simple("localhost", 8080, app, use_reloader=True)

    """
    Queries:

    http://localhost:8080
    http://localhost:8080/?operation=searchRetrieve&query=Katze&x-indent-response=1
    http://localhost:8080/?operation=searchRetrieve&queryType=cql&query=Katze&x-indent-response=1&x-extra-stuff=123
    ? http://localhost:8080/?operation=searchRetrieve&version=1.2&queryType=cql&query=Katze&x-indent-response=1&x-extra-stuff=123
    """
