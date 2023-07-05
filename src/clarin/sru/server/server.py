# from: https://pythonbasics.org/webserver/
# from http.server import BaseHTTPRequestHandler, HTTPServer

import io
import logging
from abc import ABCMeta
from abc import abstractmethod
from dataclasses import dataclass
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from xml.sax import SAXException

import cql
from werkzeug.wrappers import Request
from werkzeug.wrappers import Response

from ..constants import RESPONSE_CONTENT_TYPE
from ..constants import RESPONSE_ENCODING
from ..constants import SRU_DIAGNOSTIC_RECORD_SCHEMA
from ..constants import SRUDiagnostics
from ..constants import SRUOperation
from ..constants import SRUQueryType
from ..constants import SRURecordPacking
from ..constants import SRURecordXmlEscaping
from ..constants import SRUVersion
from ..diagnostic import SRUDiagnostic
from ..diagnostic import SRUDiagnosticList
from ..exception import SRUException
from ..queryparser import SRUQuery
from ..queryparser import SRUQueryParserRegistry
from ..xml.writer import SRUXMLStreamWriter
from .auth import SRUAuthenticationInfoProvider
from .config import DatabaseInfo
from .config import IndexInfo
from .config import LegacyNamespaceMode
from .config import LocalizedString
from .config import SchemaInfo
from .config import SRUServerConfig
from .request import SRURequest
from .request import SRURequestImpl
from .result import SRUExplainResult
from .result import SRUScanResultSet
from .result import SRUSearchResultSet

# ---------------------------------------------------------------------------


LOGGER = logging.getLogger(__name__)


SRU_NS = "http://www.loc.gov/zing/srw/"
SRU_PREFIX = "sru"
SRU_RESPONSE_NS = "http://docs.oasis-open.org/ns/search-ws/sruResponse"
SRU_RESPONSE_PREFIX = "sruResponse"
SRU_SCAN_NS = "http://docs.oasis-open.org/ns/search-ws/scan"
SRU_SCAN_PREFIX = "scan"
SRU_DIAGNOSIC_NS = "http://docs.oasis-open.org/ns/search-ws/diagnostic"
SRU_DIAGNOSTIC_PREFIX = "diag"
SRU_EXPLAIN_NS = "http://explain.z3950.org/dtd/2.0/"
SRU_EXPLAIN_PREFIX = "zr"
SRU_XCQL_NS = "http://docs.oasis-open.org/ns/search-ws/xcql"


@dataclass(frozen=True)
class SRUNamespaces:
    """Interface for decoupling SRU namespaces from implementation to
    allow to support SRU 1.1/1.2 and SRU 2.0."""

    response_NS: str
    """The namespace URI for encoding **explain** and
    **searchRetrieve** operation responses."""

    response_prefix: str
    """The namespace prefix for encoding **explain** and
    **searchRetrieve**"""

    scan_NS: str
    """The namespace URI for encoding **scan** operation responses."""

    scan_prefix: str
    """The namespace prefix for encoding **scan** operation
    responses."""

    diagnostic_NS: str
    """The namespace URI for encoding SRU diagnostics."""

    XCQL_NS: str
    """The namespace URI for encoding XCQL fragments"""

    diagnostic_prefix: str = SRU_DIAGNOSTIC_PREFIX
    """The namespace prefix for encoding SRU diagnostics."""

    explain_NS: str = SRU_EXPLAIN_NS
    """The namespace URI for encoding explain record data fragments."""

    explain_prefix: str = SRU_EXPLAIN_PREFIX
    """The namespace prefix for encoding explain record data
    fragments."""

    # ----------------------------------------------------

    @staticmethod
    def for_legacy_LOC() -> "SRUNamespaces":
        return SRUNamespaces(
            response_NS=SRU_NS,
            response_prefix=SRU_PREFIX,
            scan_NS=SRU_NS,
            scan_prefix=SRU_PREFIX,
            diagnostic_NS="http://www.loc.gov/zing/srw/diagnostic/",
            XCQL_NS="http://www.loc.gov/zing/cql/xcql/",
        )

    @staticmethod
    def for_1_2_OASIS() -> "SRUNamespaces":
        return SRUNamespaces(
            response_NS=SRU_RESPONSE_NS,
            response_prefix=SRU_RESPONSE_PREFIX,
            scan_NS=SRU_SCAN_NS,
            scan_prefix=SRU_SCAN_PREFIX,
            diagnostic_NS=SRU_DIAGNOSIC_NS,
            XCQL_NS=SRU_XCQL_NS,
        )

    @staticmethod
    def for_2_0() -> "SRUNamespaces":
        return SRUNamespaces(
            response_NS=SRU_RESPONSE_NS,
            response_prefix=SRU_RESPONSE_PREFIX,
            scan_NS=SRU_SCAN_NS,
            scan_prefix=SRU_SCAN_PREFIX,
            diagnostic_NS=SRU_DIAGNOSIC_NS,
            XCQL_NS=SRU_XCQL_NS,
        )

    @staticmethod
    def get_namespaces(
        version: SRUVersion, legacy_ns_mode: LegacyNamespaceMode
    ) -> "SRUNamespaces":
        if version is None:
            raise TypeError("version is None")

        if version in (SRUVersion.VERSION_1_1, SRUVersion.VERSION_1_2):
            if legacy_ns_mode == LegacyNamespaceMode.LOC:
                return SRUNamespaces.for_legacy_LOC()
            if legacy_ns_mode == LegacyNamespaceMode.OASIS:
                return SRUNamespaces.for_1_2_OASIS()
            raise ValueError(f"invalid legacy mode: {legacy_ns_mode}")
        if version == SRUVersion.VERSION_2_0:
            return SRUNamespaces.for_2_0()
        raise ValueError(f"invalid version: {version}")


# ---------------------------------------------------------------------------


# TODO: update docstring when SRUServerApp (WSGI) is ready
# SRUSearchEngine + SRUSearchEngineBase
class SRUSearchEngine(metaclass=ABCMeta):
    """Interface for connecting the SRU protocol implementation to an
    actual search engine. Base class required for an `SRUSearchEngine`
    implementation to be used with the `SRUServerApp`.

    Implementing the `explain` and `scan` is optional, but implementing
    `search` is mandatory.

    The implementation of these methods **must** be thread-safe.
    """

    @abstractmethod
    def explain(
        self,
        config: SRUServerConfig,
        request: SRURequest,
        diagnostics: SRUDiagnosticList,
    ) -> Optional[SRUExplainResult]:
        """Handle an **explain** operation. Implementing this method
        is optional, but is required, if the **writeExtraResponseData**
        block of the SRU response needs to be filled. The arguments
        for this operation are provides by the `SRURequest` object.

        The implementation of this method **must** be thread-safe.

        Args:
            config: the `SRUEndpointConfig` object that contains the
                endpoint configuration
            request: the `SRURequest` object that contains the
                request made to the endpoint
            diagnostics: the `SRUDiagnosticList` object for storing
                non-fatal diagnostics

        Returns:
            SRUExplainResult: a `SRUExplainResult` object or ``None``
                if the search engine does not want to provide
                `write_extra_response_data`

        Raises:
            `SRUException`: if an fatal error occurred
        """

    @abstractmethod
    def search(
        self,
        config: SRUServerConfig,
        request: SRURequest,
        diagnostics: SRUDiagnosticList,
    ) -> SRUSearchResultSet:
        """Handle a **searchRetrieve** operation. Implementing this
        method is mandatory. The arguments for this operation are
        provides by the `SRURequest` object.

        The implementation of this method **must** be thread-safe.

        Args:
            config: the `SRUEndpointConfig` object that contains the
                endpoint configuration
            request: the `SRURequest` object that contains the
                request made to the endpoint
            diagnostics: the `SRUDiagnosticList` object for storing
                non-fatal diagnostics

        Returns:
            SRUSearchResultSet: a `SRUSearchResultSet` object

        Raises:
            `SRUException`: if an fatal error occurred
        """

    @abstractmethod
    def scan(
        self,
        config: SRUServerConfig,
        request: SRURequest,
        diagnostics: SRUDiagnosticList,
    ) -> Optional[SRUScanResultSet]:
        """Handle a **scan** operation. Implementing this method is
        optional. If you don't need to handle the **scan** operation,
        just return ``None`` and the SRU server will return the
        appropiate diagnostic to the client. The arguments for this
        operation are provides by the `SRURequest` object.

        The implementation of this method **must** be thread-safe.

        Args:
            config: the `SRUEndpointConfig` object that contains the
                endpoint configuration
            request: the `SRURequest` object that contains the
                request made to the endpoint
            diagnostics: the `SRUDiagnosticList` object for storing
                non-fatal diagnostics

        Returns:
            SRUScanResultSet: a `SRUScanResultSet` object or ``None``
                if this operation is not supported by this search
                engine

        Raises:
            `SRUException`: if an fatal error occurred
        """

    # ----------------------------------------------------

    def init(
        self,
        config: SRUServerConfig,
        query_parser_registry_builder: SRUQueryParserRegistry.Builder,
        params: Dict[str, str],
    ) -> None:
        """Initialize the search engine.

        Args:
            config: the `SRUServerConfig` object for this search engine
            query_parser_registry_builder: the `SRUQueryParserRegistry.Builder`
                object to be used for this search engine. Use to register
                additional query parsers with the `SRUServer`
            params: additional parameters from the server

        Raises:
            SRUConfigException: an error occurred during initialization
                of the search engine
        """

    def destroy(self) -> None:
        """Destroy the search engine. Use this method for any cleanup
        the search engine needs to perform upon termination.
        """


# ---------------------------------------------------------------------------


class SRUServer:
    """SRU/CQL protocol implementation for the server-side (SRU/S).
    This class implements SRU/CQL version 1.1 and and 1.2.

    See also:
        SRU/CQL protocol 1.2: http://www.loc.gov/standards/sru/
    """

    def __init__(
        self,
        config: SRUServerConfig,
        query_parsers: SRUQueryParserRegistry,
        search_engine: SRUSearchEngine,
        authentication_info_provider: Optional[SRUAuthenticationInfoProvider] = None,
    ):
        if config is None:
            raise TypeError("config is None")
        if query_parsers is None:
            raise TypeError("query_parsers is None")
        if search_engine is None:
            raise TypeError("search_engine is None")

        self.config = config
        self.query_parsers = query_parsers
        self.search_engine = search_engine
        self.authentication_info_provider = authentication_info_provider

    # ----------------------------------------------------

    def handle_request(self, request: Request, response: Response):
        """Handle a SRU request."""

        req = SRURequestImpl(
            self.config,
            self.query_parsers,
            request,
            authentication_info_provider=self.authentication_info_provider,
        )
        try:
            # set response properties
            response.content_type = RESPONSE_CONTENT_TYPE
            response.content_encoding = RESPONSE_ENCODING
            response.status = 200  # type: ignore
            # TODO: buffer size? stream
            # self.config.response_buffer_size

            try:
                if req.check_parameters():
                    operation = req.get_operation()
                    if operation == SRUOperation.EXPLAIN:
                        self.explain(req, response)
                    elif operation == SRUOperation.SCAN:
                        self.scan(req, response)
                    elif operation == SRUOperation.SEARCH_RETRIEVE:
                        self.search(req, response)

                else:
                    # (some) parameters are malformed, send error
                    buf = io.StringIO()
                    out = self._create_XML_builder(
                        buf, SRURecordXmlEscaping.XML, False, req.get_indent_response()
                    )
                    ns = SRUNamespaces.get_namespaces(
                        req.get_version(), self.config.legacy_namespace_mode
                    )
                    self._write_fatal_error(out, ns, req, req.diagnostics)
                    response.set_data(buf.getvalue())
            except SAXException as ex:
                LOGGER.error("An error occurred while serializing response", ex)
                raise SRUException(
                    SRUDiagnostics.GENERAL_SYSTEM_ERROR,
                    message="An error occurred while serializing response.",
                ) from ex
            except Exception:
                # Well, can't really do anything useful here ...
                LOGGER.error("An unexpected exception occurred", exc_info=True)
        except SRUException as ex:
            # check if response.isCommitted does not exist for werkzeug
            if LOGGER.isEnabledFor(logging.INFO):
                message = ex.get_diagnostic().message
                if message:
                    LOGGER.info(
                        "Sending fatal diagnostic '%s' with message '%s'",
                        ex.get_diagnostic().uri,
                        message,
                    )
                else:
                    LOGGER.info(
                        "Sending fatal diagnostic '%s'", ex.get_diagnostic().uri
                    )
                LOGGER.debug("Fatal diagnostic was caused by this exception: %s", ex)

            # reset response buffer
            try:
                diagnostics = req.diagnostics
                if not diagnostics:
                    diagnostics = list()
                diagnostics.append(ex.get_diagnostic())

                buf = io.StringIO()
                out = self._create_XML_builder(
                    buf, SRURecordXmlEscaping.XML, False, req.get_indent_response()
                )
                ns = SRUNamespaces.get_namespaces(
                    req.get_version(), self.config.legacy_namespace_mode
                )
                self._write_fatal_error(out, ns, req, diagnostics)
                response.set_data(buf.getvalue())
            except Exception as ex:
                LOGGER.error("An exception occurred while in error state", ex)

    # TODO: temporary skip output buffering
    TEMP_OUTPUT_BUFFERING = False

    def explain(self, request: SRURequestImpl, response: Response):
        LOGGER.info("explain")

        # commence explain ...
        result = self.search_engine.explain(self.config, request, request)

        try:
            ns: SRUNamespaces = SRUNamespaces.get_namespaces(
                request.get_version(), self.config.legacy_namespace_mode
            )

            # send results
            buf = io.StringIO()
            out = self._create_XML_builder(
                buf,
                request.get_record_xml_escaping(),
                SRUServer.TEMP_OUTPUT_BUFFERING,
                request.get_indent_response(),
            )

            self._begin_response_with_request(out, ns, request)

            # write the explain record
            self._write_explain_record(out, ns, request)

            if self.config.echo_requests:
                self._write_echoed_explain_request(out, ns, request)

            # diagnostics
            self._write_diagnostics(out, ns, ns.response_NS, request.diagnostics)

            # extraResponseData
            if result:
                if result.has_extra_response_data:
                    with out.element("extraResponseData", ns.response_NS):
                        result.write_extra_response_data(out)

            self._end_response_with_request(out, ns, request)

            response.set_data(buf.getvalue())
        finally:
            if result:
                result.close()

    def scan(self, request: SRURequestImpl, response: Response):
        LOGGER.info("scan: scanClause = '%s'", request.get_scan_clause_raw())

        # commence scan ...
        result = self.search_engine.scan(self.config, request, request)
        if not result:
            raise SRUException(
                SRUDiagnostics.UNSUPPORTED_OPERATION,
                message="The 'scan' operation is not supported by this endpoint.",
            )

        try:
            ns: SRUNamespaces = SRUNamespaces.get_namespaces(
                request.get_version(), self.config.legacy_namespace_mode
            )

            # FIXME: re-check, if while scan response needs to be put
            # in scan namespace for SRU 2.0!

            # send results
            buf = io.StringIO()
            out = self._create_XML_builder(
                buf,
                request.get_record_xml_escaping(),
                SRUServer.TEMP_OUTPUT_BUFFERING,
                request.get_indent_response(),
            )

            self._begin_response_with_request(out, ns, request)

            try:
                # a scan result without a list of terms is a valid response;
                # make sure, to produce the correct output and omit in that
                # case the <terms> ...

                wrote_terms = False
                while result.next_term():
                    if not wrote_terms:
                        if ns.response_NS != ns.scan_NS:
                            out.startPrefixMapping(ns.scan_prefix, ns.scan_NS)
                            out.startElementNS((ns.scan_NS, "terms"))
                        wrote_terms = True

                    with out.element("term", ns.scan_NS):
                        with out.element("value", ns.scan_NS):
                            out.characters(result.get_value())

                        if result.get_number_of_records() > -1:
                            with out.element("numberOfRecords", ns.scan_NS):
                                out.characters(str(result.get_number_of_records()))

                        if result.get_display_term():
                            with out.element("displayTerm", ns.scan_NS):
                                out.characters(str(result.get_display_term()))

                        if result.get_WhereInList():
                            with out.element("whereInList", ns.scan_NS):
                                # NOTE: here it is not None
                                out.characters(result.get_WhereInList().lower())  # type: ignore

                        if result.has_extra_term_data():
                            with out.element("extraTermData", ns.scan_NS):
                                result.write_extra_term_data(out)

                if wrote_terms:
                    out.endElementNS((ns.scan_NS, "terms"))

            except StopIteration as ex:
                raise SRUException(
                    SRUDiagnostics.GENERAL_SYSTEM_ERROR,
                    message="An internal error occurred while serializing scan results.",
                ) from ex

            # echoedScanRequest
            if self.config.echo_requests:
                self._write_echoed_scan_request(
                    out, ns, request, request.get_scan_clause()
                )

            # diagnostics
            self._write_diagnostics(out, ns, ns.scan_NS, request.diagnostics)

            # extraResponseData
            if result.has_extra_response_data:
                with out.element("extraResponseData", ns.response_NS):
                    result.write_extra_response_data(out)

            self._end_response_with_request(out, ns, request)

            response.set_data(buf.getvalue())
        finally:
            if result:
                result.close()

    def search(self, request: SRURequestImpl, response: Response):
        LOGGER.info(
            "searchRetrieve: query = '%s', startRecord = %s, "
            "maximumRecords = %s, recordSchema = %s, resultSetTTL = %s",
            request.get_query_raw(),
            request.get_start_record(),
            request.get_maximum_records(),
            request.get_record_schema_identifier(),
            request.get_resultSet_TTL(),
        )

        # commence search ...
        result = self.search_engine.search(self.config, request, request)
        if not result:
            raise SRUException(
                SRUDiagnostics.GENERAL_SYSTEM_ERROR,
                message="SRUSearchEngine implementation returned invalid result (null).",
            )

        # check, of startRecord position is greater than total record set
        if (
            result.get_total_record_count() >= 0
            and request.get_start_record() > 1
            and request.get_start_record() > result.get_total_record_count()
        ):
            raise SRUException(SRUDiagnostics.FIRST_RECORD_POSITION_OUT_OF_RANGE)

        try:
            ns: SRUNamespaces = SRUNamespaces.get_namespaces(
                request.get_version(), self.config.legacy_namespace_mode
            )

            # send results
            buf = io.StringIO()
            out = self._create_XML_builder(
                buf,
                request.get_record_xml_escaping(),
                SRUServer.TEMP_OUTPUT_BUFFERING,
                request.get_indent_response(),
            )

            self._begin_response_with_request(out, ns, request)

            # numberOfRecords
            with out.element("numberOfRecords", ns.response_NS):
                out.characters(str(result.get_total_record_count()))

            # resultSetId
            if result.get_resultSet_id():
                with out.element("resultSetId", ns.response_NS):
                    out.characters(result.get_resultSet_id())

            # resultSetIdleTime (SRU 1.1 and SRU 1.2)
            if (
                not request.is_version(SRUVersion.VERSION_2_0)
                and result.get_resultSet_TTL() >= 0
            ):
                with out.element("resultSetIdleTime", ns.response_NS):
                    out.characters(str(result.get_resultSet_TTL()))

            position = (
                request.get_start_record() if request.get_start_record() > 0 else 1
            )

            if result.get_record_count() > 0:
                max_position_offset = (
                    (position + request.get_maximum_records() - 1)
                    if request.get_maximum_records() != -1
                    else -1
                )

                try:
                    out.startElementNS((ns.response_NS, "records"))

                    while result.next_record():
                        # Sanity check: do not return more then the maximum
                        # requested records. If the search engine
                        # implementation does not honor limit truncate the
                        # result set.
                        if max_position_offset != -1 and position > max_position_offset:
                            LOGGER.error(
                                "SRUSearchEngine implementation did not honor limit "
                                "for the amount of requsted records. Result set truncated!"
                            )
                            break

                        out.startElementNS((ns.response_NS, "record"))

                        # We need to output either the record or a surrogate
                        # diagnostic. In case of the latter, we need to output
                        # the appropriate record schema ...
                        diagnostic = result.get_surrogate_diagnostic()
                        with out.element("recordSchema", ns.response_NS):
                            if not diagnostic:
                                out.characters(result.get_record_schema_identifier())
                            else:
                                out.characters(SRU_DIAGNOSTIC_RECORD_SCHEMA)

                        # recordPacking (SRU 2.0). Only serialize, if it was in
                        # request.
                        # XXX: not sure, how to support 'unpacked' record
                        # packing anyways :/
                        if (
                            request.is_version(SRUVersion.VERSION_2_0)
                            and request.get_record_packing_raw()
                        ):
                            self._write_record_packing(
                                out, ns, request.get_record_packing()
                            )

                        # recordXMLEscaping (SRU 2.0) or
                        # recordPacking (SRU 1.1 and 1.2)
                        self._write_record_xml_escaping(out, ns, request)

                        # Output either record data or surrogate diagnostic ...
                        with out.element("recordData", ns.response_NS), out.record():
                            if diagnostic is None:
                                result.write_record(out)
                            else:
                                # write a surrogate diagnostic
                                self._write_diagnostic(out, ns, diagnostic, True)

                        # recordIdentifier is version 1.2+ only
                        if request.is_version_between(
                            SRUVersion.VERSION_1_2, SRUVersion.VERSION_2_0
                        ):
                            identifier = result.get_record_identifier()
                            if identifier:
                                with out.element("recordIdentifier", ns.response_NS):
                                    out.characters(identifier)

                        with out.element("recordPosition", ns.response_NS):
                            out.characters(str(position))

                        if result.has_extra_record_data:
                            with out.element("extraRecordData", ns.response_NS):
                                result.write_extra_record_data(out)

                        out.endElementNS((ns.response_NS, "record"))

                        position += 1

                    out.endElementNS((ns.response_NS, "records"))
                except StopIteration as ex:
                    raise SRUException(
                        SRUDiagnostics.GENERAL_SYSTEM_ERROR,
                        message="An internal error occurred while serializing search result set.",
                    ) from ex

            # nextRecordPosition
            if position <= result.get_total_record_count():
                with out.element("nextRecordPosition", ns.response_NS):
                    out.characters(str(position))

            # echoedSearchRetrieveRequest
            if self.config.echo_requests:
                # TODO: need to check, query should not be None
                self._write_echoed_searchRetrieve_request(
                    out, ns, request, request.get_query()  # type: ignore
                )

            # diagnostics
            self._write_diagnostics(out, ns, ns.response_NS, request.diagnostics)

            # extraResponseData
            if result.has_extra_response_data:
                with out.element("extraResponseData", ns.response_NS):
                    result.write_extra_response_data(out)

            # SRU 2.0 stuff ...
            if request.is_version(SRUVersion.VERSION_2_0):
                # resultSetTTL
                if result.get_resultSet_TTL() >= 0:
                    with out.element("resultSetTTL", ns.response_NS):
                        out.characters(str(result.get_resultSet_TTL()))

                # resultCountPrecision
                precision = result.get_result_count_precision()
                if precision:
                    with out.element("resultCountPrecision", ns.response_NS):
                        prefix = "info:srw/vocabulary/resultCountPrecision/1/"
                        out.characters(f"{prefix}{precision.lower()}")

                # facetedResults
                # NOTE: NOT YET SUPPORTED

                # searchResultAnalysis
                # NOTE: NOT YET SUPPORTED

            self._end_response_with_request(out, ns, request)

            response.set_data(buf.getvalue())
        finally:
            if result:
                result.close()

    # ----------------------------------------------------

    def _begin_response(
        self,
        out: SRUXMLStreamWriter,
        ns: SRUNamespaces,
        operation: SRUOperation,
        version: SRUVersion,
        stylesheet: Optional[str],
    ):
        out.startDocument()

        if stylesheet:
            out.processingInstruction(
                "xml-stylesheet", f'type="text/xsl" href="{stylesheet}"'
            )

        if operation == SRUOperation.EXPLAIN:
            out.startPrefixMapping(ns.response_prefix, ns.response_NS)
            out.startElementNS((ns.response_NS, "explainResponse"))
            self._write_version(out, ns.response_NS, version)
        elif operation == SRUOperation.SCAN:
            out.startPrefixMapping(ns.scan_prefix, ns.scan_NS)
            out.startElementNS((ns.scan_NS, "scanResponse"))
            self._write_version(out, ns.scan_NS, version)
        elif operation == SRUOperation.SEARCH_RETRIEVE:
            out.startPrefixMapping(ns.response_prefix, ns.response_NS)
            out.startElementNS((ns.response_NS, "searchRetrieveResponse"))
            self._write_version(out, ns.response_NS, version)

    def _begin_response_with_request(
        self, out: SRUXMLStreamWriter, ns: SRUNamespaces, request: SRURequest
    ):
        self._begin_response(
            out,
            ns,
            request.get_operation(),
            request.get_version(),
            request.get_stylesheet(),
        )

    def _end_response(
        self, out: SRUXMLStreamWriter, ns: SRUNamespaces, operation: SRUOperation
    ):
        if operation == SRUOperation.EXPLAIN:
            out.endElementNS((ns.response_NS, "explainResponse"))
        elif operation == SRUOperation.SCAN:
            out.endElementNS((ns.scan_NS, "scanResponse"))
        elif operation == SRUOperation.SEARCH_RETRIEVE:
            out.endElementNS((ns.response_NS, "searchRetrieveResponse"))

        out.endDocument()
        try:
            out.output_stream.flush()
            out.output_stream_raw.flush()

            # if we use buffers internally, then don't close them
            # otherwise we can't access the content anymore ...
            if not isinstance(out.output_stream, io.StringIO):
                out.output_stream.close()
            if not isinstance(out.output_stream_raw, io.StringIO):
                out.output_stream_raw.close()
        except Exception:
            pass

    def _end_response_with_request(
        self, out: SRUXMLStreamWriter, ns: SRUNamespaces, request: SRURequest
    ):
        self._end_response(out, ns, request.get_operation())

    # ----------------------------------------------------

    def _write_fatal_error(
        self,
        out: SRUXMLStreamWriter,
        ns: SRUNamespaces,
        request: SRURequestImpl,
        diagnostics: Optional[List[SRUDiagnostic]],
    ):
        # if operation is unknown, default to 'explain'
        operation = request.get_operation()
        if operation is None:
            operation = SRUOperation.EXPLAIN
        version = request.get_version()
        if version is None:
            version = self.config.default_version

        # write a response which conforms to the schema
        self._begin_response(out, ns, operation, version, None)
        if operation == SRUOperation.EXPLAIN:
            # 'explain' requires a complete explain record ...
            self._write_explain_record(out, ns, request)
            self._write_diagnostics(out, ns, ns.response_NS, diagnostics)
        elif operation == SRUOperation.SCAN:
            # 'scan' fortunately does not need any elements ...
            self._write_diagnostics(out, ns, ns.scan_NS, diagnostics)
        elif operation == SRUOperation.SEARCH_RETRIEVE:
            # 'searchRetrieve' needs numberOfRecords ..
            with out.element("numberOfRecords", ns.response_NS):
                out.characters("0")
            self._write_diagnostics(out, ns, ns.response_NS, diagnostics)

        self._end_response(out, ns, operation)

    def _write_diagnostics(
        self,
        out: SRUXMLStreamWriter,
        ns: SRUNamespaces,
        envelope_NS: str,
        diagnostics: Optional[List[SRUDiagnostic]],
    ):
        if not diagnostics:
            return

        out.startPrefixMapping(ns.diagnostic_prefix, ns.diagnostic_NS)
        with out.element("diagnostics", envelope_NS):
            for diagnostic in diagnostics:
                self._write_diagnostic(out, ns, diagnostic, False)

    def _write_diagnostic(
        self,
        out: SRUXMLStreamWriter,
        ns: SRUNamespaces,
        diagnostic: SRUDiagnostic,
        write_NS_decl: bool,
    ):
        if write_NS_decl:
            out.startPrefixMapping(ns.diagnostic_prefix, ns.diagnostic_NS)
        with out.element("diagnostic", ns.diagnostic_NS):
            with out.element("uri", ns.diagnostic_NS):
                out.characters(diagnostic.uri)
            if diagnostic.details:
                with out.element("details", ns.diagnostic_NS):
                    out.characters(diagnostic.details)
            if diagnostic.message:
                with out.element("message", ns.diagnostic_NS):
                    out.characters(diagnostic.message)

    # ----------------------------------------------------

    def _write_explain_record(
        self, out: SRUXMLStreamWriter, ns: SRUNamespaces, request: SRURequestImpl
    ):
        def _write_DatabaseInfo(info: Optional[DatabaseInfo]):
            if not info:
                return

            with out.element("databaseInfo", ns.explain_NS):
                self._write_LocalizedString(out, ns, "title", info.title)
                self._write_LocalizedString(out, ns, "description", info.description)

                self._write_LocalizedString(out, ns, "author", info.author)
                self._write_LocalizedString(out, ns, "extent", info.extent)
                self._write_LocalizedString(out, ns, "history", info.history)
                self._write_LocalizedString(out, ns, "langUsage", info.langUsage)
                self._write_LocalizedString(out, ns, "restrictions", info.restrictions)
                self._write_LocalizedString(out, ns, "subjects", info.subjects)
                self._write_LocalizedString(out, ns, "links", info.links)
                self._write_LocalizedString(
                    out, ns, "implementation", info.implementation
                )

        def _write_IndexInfo(info: Optional[IndexInfo]):
            if not info:
                return

            with out.element("indexInfo", ns.explain_NS):
                _write_IndexInfo_Sets(info.sets)
                _write_IndexInfo_Indexes(info.indexes)

        def _write_IndexInfo_Sets(sets: Optional[List[IndexInfo.Set]]):
            if not sets:
                return

            for set in sets:
                with out.element(
                    "set",
                    ns.explain_NS,
                    attrs={"identifier": set.identifier, "name": set.name},
                ):
                    self._write_LocalizedString(out, ns, "title", set.title)

        def _write_IndexInfo_Indexes(indexes: Optional[List[IndexInfo.Index]]):
            if not indexes:
                return

            for index in indexes:
                with out.element(
                    "index",
                    ns.explain_NS,
                    attrs={
                        "search": "true" if index.can_search else "false",
                        "scan": "true" if index.can_scan else "false",
                        "sort": "true" if index.can_sort else "false",
                    },
                ):
                    self._write_LocalizedString(out, ns, "title", index.title)

                    _write_IndexInfo_Index_Maps(index.maps)

        def _write_IndexInfo_Index_Maps(maps: Optional[List[IndexInfo.Index.Map]]):
            if not maps:
                return

            for map in maps:
                attrs: Dict[str, str] = dict()
                if map.primary:
                    attrs.update(primary="true")
                with out.element("map", ns.explain_NS, attrs=attrs):
                    with out.element(
                        "name",
                        ns.explain_NS,
                        attrs={"set": map.set},
                    ):
                        out.characters(map.name)

        def _write_SchemaInfos(infos: Optional[List[SchemaInfo]]):
            if not infos:
                return

            with out.element("schemaInfo", ns.explain_NS):
                for schema in infos:
                    attrs = {
                        "identifier": schema.identifier,
                        "name": schema.name,
                    }
                    # default is "false", so only add attribute if set to true
                    if schema.sort:
                        attrs.update({"sort": "true"})
                    # default is "true", so only add attribute if set to false
                    if not schema.retrieve:
                        attrs.update({"retrieve": "false"})

                    with out.element("schema", ns.explain_NS, attrs=attrs):
                        self._write_LocalizedString(out, ns, "title", schema.title)

        # ----------------------------

        with out.element("record", ns.response_NS):
            with out.element("recordSchema", ns.response_NS):
                out.characters(ns.explain_NS)

            # recordPacking (SRU 2.0)
            # Only serialize, if it was in request.
            # XXX: not sure, if this makes sense for explain
            if (
                request.is_version(SRUVersion.VERSION_2_0)
                and request.get_record_packing_raw()
            ):
                self._write_record_packing(out, ns, request.get_record_packing())

            # recordXMLEscaping (SRU 2.0) or recordPacking (SRU 1.1 and 1.2)
            self._write_record_xml_escaping(out, ns, request)

            with out.element("recordData", ns.response_NS), out.record():
                # explain ...
                out.startPrefixMapping(ns.explain_prefix, ns.explain_NS)
                with out.element("explain", ns.explain_NS):
                    # explain/serverInfo
                    with out.element(
                        "serverInfo",
                        ns.explain_NS,
                        attrs={
                            "protocol": "SRU",
                            "version": self.config.default_version.version_string,
                            "transport": self.config.transport,
                        },
                    ):
                        with out.element("host", ns.explain_NS):
                            out.characters(self.config.host)
                        with out.element("port", ns.explain_NS):
                            out.characters(str(self.config.port))
                        with out.element("database", ns.explain_NS):
                            out.characters(self.config.database)

                    # explain/databaseInfo
                    _write_DatabaseInfo(self.config.database_info)
                    # explain/indexInfo
                    _write_IndexInfo(self.config.index_info)
                    # explain/schemaInfo
                    _write_SchemaInfos(self.config.schema_info)

                    # explain/configInfo
                    with out.element("configInfo", ns.explain_NS):
                        # numberOfRecords (default)
                        with out.element(
                            "default", ns.explain_NS, attrs={"type": "numberOfRecords"}
                        ):
                            out.characters(str(self.config.number_of_records))

                        # maximumRecords (setting)
                        with out.element(
                            "setting", ns.explain_NS, attrs={"type": "maximumRecords"}
                        ):
                            out.characters(str(self.config.maximum_records))

    def _write_echoed_explain_request(
        self, out: SRUXMLStreamWriter, ns: SRUNamespaces, request: SRURequestImpl
    ):
        # echoedSearchRetrieveRequest ?
        with out.element("echoedExplainRequest", ns.response_NS):
            # echoedExplainRequest/version
            if request.get_version_raw() is not None:
                # NOTE: version is not None
                self._write_version(out, ns.response_NS, request.get_version_raw())  # type: ignore

            # echoedExplainRequest/recordXmlEscpaing / recordPacking
            if request.get_record_packing_raw():
                self._write_record_xml_escaping(out, ns, request)

            # echoedExplainRequest/stylesheet
            if request.stylesheet:
                with out.element("stylesheet", ns.response_NS):
                    out.characters(request.get_stylesheet())

    def _write_echoed_scan_request(
        self,
        out: SRUXMLStreamWriter,
        ns: SRUNamespaces,
        request: SRURequestImpl,
        query: Optional[cql.CQLQuery],
    ):
        # echoedScanRequest
        with out.element("echoedScanRequest", ns.response_NS):
            # echoedScanRequest/version
            if request.get_version_raw() is not None:
                # NOTE: version is not None
                self._write_version(out, ns.response_NS, request.get_version_raw())  # type: ignore

            # echoedScanRequest/scanClause
            with out.element("scanClause", ns.response_NS):
                out.characters(request.get_scan_clause_raw())

            # echoedScanRequest/xScanClause
            out.startPrefixMapping(None, ns.XCQL_NS)
            with out.element("xScanClause", ns.response_NS):
                # TODO: can this be None? it should not, need to test
                out.writeXCQL(query, False)  # type: ignore

            # echoedScanRequest/responsePosition
            if request.get_response_position() != -1:
                with out.element("responsePosition", ns.response_NS):
                    out.characters(str(request.get_response_position()))

            # echoedScanRequest/maximumTerms
            if request.get_maximum_terms() != -1:
                with out.element("maximumTerms", ns.response_NS):
                    out.characters(str(request.get_maximum_terms()))

            # echoedScanRequest/stylesheet
            if request.get_stylesheet():
                with out.element("stylesheet", ns.response_NS):
                    out.characters(request.get_stylesheet())

    def _write_echoed_searchRetrieve_request(
        self,
        out: SRUXMLStreamWriter,
        ns: SRUNamespaces,
        request: SRURequestImpl,
        query: SRUQuery[Any],
    ):
        # echoedSearchRetrieveRequest
        with out.element("echoedSearchRetrieveRequest", ns.response_NS):
            # echoedSearchRetrieveRequest/version
            if request.get_version_raw() is not None:
                # NOTE: version is not None
                self._write_version(out, ns.response_NS, request.get_version_raw())  # type: ignore

            # XXX: unclear, if <query> should only be echoed if queryType is CQL!?
            if SRUQueryType.CQL == query.query_type:
                # echoedSearchRetrieveRequest/query
                with out.element("query", ns.response_NS):
                    out.characters(query.raw_query)

                # echoedSearchRetrieveRequest/xQuery
                out.startPrefixMapping(None, ns.XCQL_NS)
                with out.element("xQuery", ns.response_NS):
                    out.writeXCQL(query.parsed_query, True)

            # echoedSearchRetrieveRequest/startRecord
            if request.get_start_record() > 0:
                with out.element("startRecord", ns.response_NS):
                    out.characters(str(request.get_start_record()))

            # echoedSearchRetrieveRequest/maximumRecords
            if request.get_maximum_records_raw() > 0:
                with out.element("maximumRecords", ns.response_NS):
                    out.characters(str(request.get_maximum_records_raw()))

            # (SRU 2.0) echoedSearchRetrieveRequest/recordPacking
            if (
                request.is_version(SRUVersion.VERSION_2_0)
                and request.get_record_packing_raw()
            ):
                with out.element("recordPacking", ns.response_NS):
                    out.characters(request.get_record_packing_raw())

            # echoedSearchRetrieveRequest/recordXmlEscaping / recordPacking
            if request.get_record_xml_escaping_raw():
                tag = (
                    "recordXMLEscaping"
                    if request.is_version(SRUVersion.VERSION_2_0)
                    else "recordPacking"
                )
                with out.element(tag, ns.response_NS):
                    out.characters(request.get_record_xml_escaping_raw())

            # echoedSearchRetrieveRequest/recordSchema
            if request.get_record_schema_identifier_raw():
                with out.element("recordSchema", ns.response_NS):
                    out.characters(request.get_record_schema_identifier_raw())

            # echoedSearchRetrieveRequest/recordXPath (1.1)
            if (
                request.is_version(SRUVersion.VERSION_1_1)
                and request.get_record_xpath()
            ):
                with out.element("recordXPath", ns.response_NS):
                    out.characters(request.get_record_xpath())

            # echoedSearchRetrieveRequest/resultSetTTL
            if request.get_resultSet_TTL() > 0:
                with out.element("resultSetTTL", ns.response_NS):
                    out.characters(str(request.get_resultSet_TTL()))

            # echoedSearchRetrieveRequest/sortKeys
            if request.is_version(SRUVersion.VERSION_1_1) and request.get_sortKeys():
                with out.element("sortKeys", ns.response_NS):
                    out.characters(request.get_sortKeys())

            # echoedSearchRetrieveRequest/xsortKeys

            # echoedSearchRetrieveRequest/stylesheet
            if request.get_stylesheet():
                with out.element("stylesheet", ns.response_NS):
                    out.characters(request.get_stylesheet())

            # echoedSearchRetrieveRequest/renderedBy
            if request.is_version(SRUVersion.VERSION_2_0) and request.get_renderBy():
                with out.element("renderedBy", ns.response_NS):
                    out.characters(request.get_renderBy().lower())  # type: ignore

            # echoedSearchRetrieveRequest/extraRequestParameter
            # FIXME: NOT YET IMPLEMENTED

            # echoedSearchRetrieveRequest/httpAccept
            # NOTE: broken in java version? uses renderedBy
            if (
                request.is_version(SRUVersion.VERSION_2_0)
                and request.get_http_accept_raw()
            ):
                with out.element("httpAccept", ns.response_NS):
                    out.characters(request.get_http_accept_raw())

            # echoedSearchRetrieveRequest/responseType
            if (
                request.is_version(SRUVersion.VERSION_2_0)
                and request.get_response_type()
            ):
                with out.element("responseType", ns.response_NS):
                    out.characters(request.get_response_type())

    # ----------------------------------------------------

    def _write_version(
        self, out: SRUXMLStreamWriter, envelope_NS: str, version: SRUVersion
    ):
        with out.element("version", envelope_NS):
            out.characters(version.version_string)

    def _write_record_xml_escaping(
        self, out: SRUXMLStreamWriter, ns: SRUNamespaces, request: SRURequest
    ):
        tag = (
            "recordXMLEscaping"
            if request.is_version(SRUVersion.VERSION_2_0)
            else "recordPacking"
        )
        with out.element(tag, ns.response_NS):
            out.characters(request.get_record_xml_escaping().lower())

    def _write_record_packing(
        self,
        out: SRUXMLStreamWriter,
        ns: SRUNamespaces,
        record_packing: SRURecordPacking,
    ):
        with out.element("recordPacking", ns.response_NS):
            out.characters(record_packing.lower())

    def _write_LocalizedString(
        self,
        out: SRUXMLStreamWriter,
        ns: SRUNamespaces,
        name: str,
        items: Optional[List[LocalizedString]],
    ):
        if not items:
            return
        for item in items:
            attrs: Dict[str, str] = dict()
            if item.lang:
                attrs.update(lang=item.lang)
            if item.primary:
                attrs.update(primary="true")
            with out.element(name, ns.explain_NS, attrs=attrs):
                out.characters(item.value)

    # ----------------------------------------------------

    def _create_XML_builder(
        self,
        output_stream: io.TextIOBase,
        record_packing: SRURecordXmlEscaping,
        skip_flush: bool,
        indent: int,
    ):
        try:
            if skip_flush:
                """
                Add a BufferedWriter(?) to delay flush() as long as possible.
                Doing so, enabled us to send an appropriate SRU diagnostic
                in case an error occurs during the serialization of the response.
                Of course, if an error occurs when the server response buffer
                already had been flushed, because it was to large, we cannot
                fail gracefully and we will produce ill-formed XML output.
                """
                # FIXME: do we have some...?
                # output_stream = io.BufferedWriter(
                #     output_stream, buffer_size=self.config.response_buffer_size
                # )
                # NOTE: might only make sense in async(io) use-case
                # otherwise always buffered in memory
                LOGGER.debug(
                    "Function for 'skip_flush' in '_create_XML_builder' not used."
                )

            return SRUXMLStreamWriter(
                output_stream, record_escaping=record_packing, indent=indent
            )
        except Exception as ex:
            raise SRUException(
                SRUDiagnostics.GENERAL_SYSTEM_ERROR,
                message="Error creating output stream.",
            ) from ex


# ---------------------------------------------------------------------------
