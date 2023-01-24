import logging

from werkzeug.test import Client
from werkzeug.testapp import test_app

from clarin.sru.queryparser import SRUQueryParserRegistry
from clarin.sru.server.config import SRUServerConfig
from clarin.sru.server.config import SRUServerConfigKey
from clarin.sru.server.server import SRUServer

logging.basicConfig(level=logging.DEBUG)


class FakeSE:
    def explain(self, *args, **kwargs):
        return None


params = {
    SRUServerConfigKey.SRU_TRANSPORT: "http",
    SRUServerConfigKey.SRU_HOST: "localhost",
    SRUServerConfigKey.SRU_PORT: "80",
    SRUServerConfigKey.SRU_DATABASE: "test",
    SRUServerConfigKey.SRU_ALLOW_OVERRIDE_INDENT_RESPONSE: "true",
}

config = SRUServerConfig.parse(params, "src/clarin/sru/xml/sru-server-config.xml")
query_parsers = SRUQueryParserRegistry.Builder(True).build()
server = SRUServer(config, query_parsers, FakeSE())

client = Client(test_app)
response = client.get(
    "?operation=explain&x-fcs-endpoint-description=true&x-indent-response=1"
)
request = response.request

server.handle_request(request, response)
