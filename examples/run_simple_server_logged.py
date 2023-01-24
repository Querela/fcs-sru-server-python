import contextvars
import logging
import os
import threading
import uuid  # noqa: F401

import werkzeug
from run_simple_server import MySRUSearchEngine
from werkzeug.middleware.shared_data import SharedDataMiddleware

from clarin.sru.server.config import SRUServerConfigKey
from clarin.sru.server.wsgi import SRUServerApp


def make_app():
    here = os.path.dirname(__file__)
    config_file = os.path.join(here, "./sru-server-config.xml")
    app = SRUServerApp(
        MySRUSearchEngine,
        config_file,
        {SRUServerConfigKey.SRU_ECHO_REQUESTS: "true"},
        develop=True,
    )
    app = SharedDataMiddleware(app, {"/": os.path.join(here, "xslt")})
    return app


LOCAL = threading.local()
REQUEST_ID = contextvars.ContextVar("request_id", default="-")
# REQUEST_ID.set("-")


if __name__ == "__main__":
    from werkzeug.serving import run_simple

    logging.basicConfig(
        level=logging.DEBUG,
        format="[%(levelname).1s][%(request_id)s][%(name)s] %(message)s",
    )

    class RequestFilter(logging.Filter):
        def filter(self, record):
            record.request_id = REQUEST_ID.get("-")
            return record

    handler = logging.root.handlers[0]
    handler.addFilter(RequestFilter())

    app = make_app()

    # _wsgi_app = app.app.wsgi_app
    # def wsgi_app_wrapper(environ, start_response):
    #     token = REQUEST_ID.set(f'{environ["REMOTE_ADDR"]}:{environ["REMOTE_PORT"]}') #uuid.uuid4().hex[:4])
    #     try:
    #         return _wsgi_app(environ, start_response)
    #     finally:
    #         REQUEST_ID.reset(token)
    # app.app.wsgi_app = wsgi_app_wrapper

    class MyWSGIRequestHandler(werkzeug.serving.WSGIRequestHandler):
        counter = 1  # not thread-safe I think, see contextvars/threading stuff

        def handle_one_request(self) -> None:
            MyWSGIRequestHandler.counter += 1
            token = REQUEST_ID.set(
                f"{MyWSGIRequestHandler.counter:04x}"
            )  # uuid.uuid4().hex[:4])
            try:
                return super().handle_one_request()
            finally:
                REQUEST_ID.reset(token)

    # use_reloader=False if debugging
    run_simple(
        "localhost", 8080, app, use_reloader=True, request_handler=MyWSGIRequestHandler
    )

    """
    Queries:

    http://localhost:8080
    http://localhost:8080/?operation=searchRetrieve&query=Katze&x-indent-response=1
    http://localhost:8080/?operation=searchRetrieve&queryType=cql&query=Katze&x-indent-response=1&x-extra-stuff=123
    ? http://localhost:8080/?operation=searchRetrieve&version=1.2&queryType=cql&query=Katze&x-indent-response=1&x-extra-stuff=123

    http://localhost:8080/?version=1.2&stylesheet=xslt/explainResponse.xsl
    """
