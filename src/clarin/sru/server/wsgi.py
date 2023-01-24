import logging
import typing
from typing import Dict
from typing import Iterable
from typing import Optional
from typing import Type
from typing import Union

from werkzeug import Request
from werkzeug import Response

from clarin.sru.constants import SRUVersion
from clarin.sru.exception import SRUConfigException
from clarin.sru.queryparser import SRUQueryParserRegistry
from clarin.sru.server.auth import SRUAuthenticationInfoProvider
from clarin.sru.server.auth import SRUAuthenticationInfoProviderFactory
from clarin.sru.server.config import SRUServerConfig
from clarin.sru.server.config import SRUServerConfigKey
from clarin.sru.server.server import SRUSearchEngine
from clarin.sru.server.server import SRUServer

if typing.TYPE_CHECKING:
    # import typing_extensions as te
    # wsgiref.types  # only 3.11
    # from _typeshed.wsgi import WSGIApplication
    from _typeshed.wsgi import StartResponse
    from _typeshed.wsgi import WSGIEnvironment


LOGGER = logging.getLogger(__name__)


# ---------------------------------------------------------------------------


class SRUServerApp:  # WSGIApplication
    def __init__(
        self,
        SRUSearchEngine_clazz: Union[Type[SRUSearchEngine], SRUSearchEngine],
        config_file: str,
        params: Dict[Union[SRUServerConfigKey, str], str],
        develop: bool = False,
    ):
        self.SRUSearchEngine_clazz = SRUSearchEngine_clazz
        self.config_file = config_file
        self.params = dict(params)
        self.develop = develop

        self.init()

    # ----------------------------------------------------

    def set_default_params(self) -> None:
        # set defaults
        if self.develop:
            LOGGER.warning("Using >develop< mode!")

            def _set_default(name, value):
                if name not in self.params:
                    self.params[name] = value
                    LOGGER.warning(
                        "Using default '%s' for parameter '%s'"
                        ", because it was not defined in configuration",
                        value,
                        name,
                    )
                    LOGGER.warning("THIS IS NOT RECOMMENDED FOR PRODUCTION DEPLOYMENT!")

            _set_default(SRUServerConfigKey.SRU_TRANSPORT, "http")
            _set_default(SRUServerConfigKey.SRU_HOST, "127.0.0.1")
            _set_default(SRUServerConfigKey.SRU_PORT, "8080")
            _set_default(SRUServerConfigKey.SRU_DATABASE, "/")

            # allowed indented responses
            self.params.setdefault(
                SRUServerConfigKey.SRU_ALLOW_OVERRIDE_INDENT_RESPONSE, "true"
            )

        # set to SRU 2.0 version
        self.params.setdefault(
            SRUServerConfigKey.SRU_SUPPORTED_VERSION_DEFAULT, SRUVersion.VERSION_2_0
        )
        self.params.setdefault(
            SRUServerConfigKey.SRU_SUPPORTED_VERSION_MAX, SRUVersion.VERSION_2_0
        )

    def init(self) -> None:
        # Set some defaults (aka "plug and play" for development deployment)
        # Override those for a production deployment through the params parameter
        self.set_default_params()

        # now go ahead and setup everything ...

        try:
            # parse SRU server configuration
            config = SRUServerConfig.parse(self.params, self.config_file)

            # create an instance of the search engine ...
            LOGGER.debug(
                "Creating new search engine from class %s", self.SRUSearchEngine_clazz
            )
            # TODO: create from package.class name (str) ?
            try:
                if not self.SRUSearchEngine_clazz:
                    raise TypeError("SRUSearchEngine_clazz is None")

                # check that of class type and correct class
                if isinstance(self.SRUSearchEngine_clazz, type):
                    if SRUSearchEngine not in self.SRUSearchEngine_clazz.mro():
                        raise ValueError(
                            "Parameter 'SRUSearchEngine_clazz' not of type SRUSearchEngine"
                        )

                    self.search_engine = self.SRUSearchEngine_clazz()
                else:
                    if not isinstance(self.SRUSearchEngine_clazz, SRUSearchEngine):
                        raise ValueError(
                            "Invalid value for 'SRUSearchEngine_clazz' argument."
                        )

                    # got instance of class instead of type
                    self.search_engine = self.SRUSearchEngine_clazz
            except Exception as ex:
                raise SRUConfigException("Error creating search engine") from ex

            # initialize search engine ...
            qpr_builder = SRUQueryParserRegistry.Builder()
            self.search_engine.init(config, qpr_builder, self.params)

            # create authentication provider
            auth_provider: Optional[SRUAuthenticationInfoProvider] = None
            if isinstance(self.search_engine, SRUAuthenticationInfoProviderFactory):
                LOGGER.debug("Creating new authentication info provider")
                auth_provider = self.search_engine.create_SRUAuthenticationInfoProvider(
                    self.params
                )

            # finally create the sru server ...
            self.server = SRUServer(
                config=config,
                query_parsers=qpr_builder.build(),
                search_engine=self.search_engine,
                authentication_info_provider=auth_provider,
            )

        except SRUConfigException as ex:
            raise RuntimeError(
                f"error configuring or inializing the server: {str(ex)}"
            ) from ex

    def destroy(self) -> None:
        """Destroy the SRU server application"""
        if self.search_engine:
            self.search_engine.destroy()

    # ----------------------------------------------------

    def wsgi_app(
        self, environ: "WSGIEnvironment", start_response: "StartResponse"
    ) -> Iterable[bytes]:
        request = Request(environ)
        response = Response()
        self.server.handle_request(request, response)
        return response(environ, start_response)

    def __call__(
        self, environ: "WSGIEnvironment", start_response: "StartResponse"
    ) -> Iterable[bytes]:
        return self.wsgi_app(environ, start_response)


# ---------------------------------------------------------------------------
