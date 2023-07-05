import logging
import re
from abc import ABCMeta
from abc import abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any
from typing import List
from typing import Optional
from typing import Type
from typing import TypeVar
from typing import Union

import cql
from werkzeug.wrappers import Request

from ..constants import PARAM_EXTENSION_PREFIX
from ..constants import SRUDiagnostics
from ..constants import SRUOperation
from ..constants import SRUParam
from ..constants import SRUParamValue
from ..constants import SRUQueryType
from ..constants import SRURecordPacking
from ..constants import SRURecordXmlEscaping
from ..constants import SRURenderBy
from ..constants import SRUVersion
from ..diagnostic import SRUDiagnostic
from ..diagnostic import SRUDiagnosticList
from ..exception import SRUException
from ..queryparser import CQLQueryParser
from ..queryparser import SRUQuery
from ..queryparser import SRUQueryParserRegistry
from .auth import SRUAuthenticationInfo
from .auth import SRUAuthenticationInfoProvider
from .config import SRUServerConfig

T = TypeVar("T")

LOGGER = logging.getLogger("__name__")

QUERY_TYPE_ALLOWED_CHARS = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]*")


# ---------------------------------------------------------------------------


class SRURequest(metaclass=ABCMeta):
    """Provides information about a SRU request."""

    @abstractmethod
    def get_operation(self) -> SRUOperation:
        """Get the ``operation`` parameter of this request. Available
        for **explain**, **searchRetrieve** and **scan** requests.
        """

    @abstractmethod
    def get_version(self) -> SRUVersion:
        """Get the **version** parameter of this request. Available
        for **explain**, **searchRetrieve** and **scan** requests.
        """

    def is_version(self, version: SRUVersion) -> bool:
        """Check if this request is of a specific version.

        Args:
            version: the version to check

        Returns:
            bool: ``True`` if this request is in the requested
                version, ``False`` otherwise
        """
        if version is None:
            raise Type("version is None")
        return self.get_version() == version

    def is_version_between(self, min: SRUVersion, max: SRUVersion) -> bool:
        """Check if version of this request is at least `min` and
        at most `max`.

        Args:
            min: the minimum version
            max: the maximum version

        Returns:
            bool: ``True`` if this request is in the requested
                version, ``False`` otherwise
        """
        if min is None:
            raise TypeError("min is None")
        if max is None:
            raise TypeError("max is None")
        if min.version_number > max.version_number:
            raise ValueError("min > max")
        version = self.get_version()
        return (
            version.version_number >= min.version_number
            and version.version_number <= max.version_number
        )

    @abstractmethod
    def get_record_xml_escaping(self) -> SRURecordXmlEscaping:
        """Get the **recordXmlEscpaing** (SRU 2.0) or **recordPacking**
        (SRU 1.1 and SRU 1.2) parameter of this request. Only
        available for **explain** and **searchRetrieve** requests.

        Returns:
            SRURecordXmlEscaping: the record XML escaping method
        """

    @abstractmethod
    def get_record_packing(self) -> SRURecordPacking:
        """Get the **recordPacking** (SRU 2.0) parameter of this
        request. Only available for **searchRetrieve** requests.

        Returns:
            SRURecordPacking: the record packing method
        """

    @abstractmethod
    def get_query(self) -> Optional[SRUQuery[Any]]:
        """Get the **query** parameter of this request. Only available
        for **searchRetrieve** requests.

        Returns:
            SRUQuery[Any]: an `SRUQuery` instance tailored for the
                used queryType or `None` if not a **searchRetrieve**
                request
        """

    # TODO: required; pythonic?
    # def get_query(self, type: Type[T]) -> Optional[SRUQuery[T]]:

    def get_query_type(self) -> Optional[str]:
        """Get the **queryType** parameter of this request. Only
        available for **searchRetrieve** requests.

        Returns:
            str: the queryType of the parsed query or `None` if not a
                **searchRetrieve** request
        """
        query = self.get_query()
        if query is None:
            return None
        return query.query_type

    def is_query_type(self, query_type: str) -> bool:
        """Check if the request was made with the given queryType.
        Only available for **searchRetrieve** requests.

        Args:
            query_type: the queryType to compare with

        Returns:
            bool: ``True`` if the queryType matches, ``False``
                otherwise
        """
        if query_type is None:
            return False
        return self.get_query_type() == query_type

    @abstractmethod
    def get_start_record(self) -> int:
        """Get the **startRecord** parameter of this request. Only
        available for **searchRetrieve** requests. If the client did
        not provide a value for the request, it is set to ``1``.

        Returns:
            int: the number of the start record
        """

    @abstractmethod
    def get_maximum_records(self) -> int:
        """Get the **maximumRecords** parameter of this request. Only
        available for **searchRetrieve** requests. If no value was
        supplied with the request, the server will automatically set
        a default value.

        Returns:
            int: the maximum number of records
        """

    @abstractmethod
    def get_record_schema_identifier(self) -> Optional[str]:
        """Get the record schema identifier derived from the
        **recordSchema** parameter of this request. Only available
        for **searchRetrieve** requests. If the request was send with
        the short record schema name, it will automatically expanded
        to the record schema identifier.

        Returns:
            str: the record schema identifier or `None` if no
                **recordSchema** parameter was supplied for this
                request
        """

    @abstractmethod
    def get_record_xpath(self) -> Optional[str]:
        """Get the **recordXPath** parameter of this request. Only
        available for **searchRetrieve** requests and version 1.1
        requests.

        Returns:
            str: the record XPath or `None` of no value was supplied
                for this request
        """

    @abstractmethod
    def get_resultSet_TTL(self) -> int:
        """Get the **resultSetTTL** parameter of this request. Only
        available for **searchRetrieve** requests.

        Returns:
            int: the result set TTL or ``-1`` if no value was
                supplied for this request
        """

    @abstractmethod
    def get_sortKeys(self) -> Optional[str]:
        """Get the **sortKeys** parameter of this request. Only
        available for **searchRetrieve** requests and version 1.1 requests.

        Returns:
            str: the record XPath or `None` of no value was supplied
                for this request
        """

    # TODO CQLQuery/CQLNode?
    @abstractmethod
    def get_scan_clause(self) -> Optional[cql.CQLQuery]:
        """Get the **scanClause** parameter of this request. Only
        available for **scan** requests.

        Returns:
            cql.CQLQuery: the parsed scan clause or `None` if not a
                **scan** request
        """

    @abstractmethod
    def get_response_position(self) -> int:
        """Get the **responsePosition** parameter of this request.
        Only available for **scan** requests. If the client did not
        provide a value for the request, it is set to ``1``.

        Returns:
            int: the response position
        """

    @abstractmethod
    def get_maximum_terms(self) -> int:
        """Get the **maximumTerms** parameter of this request.
        Available for any type of request.

        Returns:
            int: the maximum number of terms or ``-1`` if no value
                was supplied for this request
        """

    @abstractmethod
    def get_stylesheet(self) -> Optional[str]:
        """Get the **stylesheet** parameter of this request.
        Available for **explain**, **searchRetrieve** and **scan**
        requests.

        Returns:
            str: the stylesheet or `None` if no value was supplied
                for this request
        """

    @abstractmethod
    def get_renderBy(self) -> Optional[SRURenderBy]:
        """Get the **renderBy** parameter of this request.

        Returns:
            SRURenderBy: the renderBy parameter or `None` if no value
                was supplied for this request
        """

    @abstractmethod
    def get_response_type(self) -> Optional[str]:
        """(SRU 2.0) The request parameter **responseType**, paired
        with the Internet media type specified for the response (via
        either the httpAccept parameter or http accept header)
        determines the schema for the response.

        Returns:
            str: the value of the responeType request parameter or
                `None` if no value was supplied for this request
        """

    @abstractmethod
    def get_http_accept(self) -> Optional[str]:
        """(SRU 2.0) The request parameter **httpAccept** may be
        supplied to indicate the preferred format of the response.
        The value is an Internet media type.

        Returns:
            str: the value of the httpAccept request parameter or
                `None` if no value was supplied for
        """

    @abstractmethod
    def get_protocol_schema(self) -> str:
        """Get the protocol schema which was used of this request.
        Available for **explain**, **searchRetrieve** and **scan**
        requests.

        Returns:
            str: the protocol scheme
        """

    @abstractmethod
    def get_extra_request_data_names(self) -> List[str]:
        """Get the names of extra parameters of this request.
        Available for **explain**, **searchRetrieve** and **scan**
        requests.

        Returns:
            List[str]: a possibly empty list of parameter names
        """

    @abstractmethod
    def get_extra_request_data(self, name: str) -> Optional[str]:
        """Get the value of an extra parameter of this request.
        Available for **explain**, **searchRetrieve** and **scan**
        requests.

        Args:
            name: name of the extra parameter. Must be prefixed with
                ``x-``

        Returns:
            str: the value of the parameter of `None` of extra
                parameter with that name exists
        """


# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ParameterInfo:
    class Parameter(str, Enum):
        STYLESHEET = "stylesheet"
        RENDER_BY = "render_by"
        HTTP_ACCEPT = "http_accept"
        RESPONSE_TYPE = "response_type"
        START_RECORD = "start_record"
        MAXIMUM_RECORDS = "maximum_records"
        RECORD_XML_ESCAPING = "record_xml_escaping"
        RECORD_PACKING = "record_packing"
        RECORD_SCHEMA = "record_schema"
        RECORD_XPATH = "record_xpath"
        RESULT_SET_TTL = "result_set_ttl"
        SORT_KEYS = "sort_keys"
        SCAN_CLAUSE = "scan_clause"
        RESPONSE_POSITION = "response_position"
        MAXIMUM_TERMS = "maximum_terms"

    # ----------------------------------------------------# ----------------------------------------------------

    parameter: Parameter
    mandatory: bool
    min: SRUVersion
    max: SRUVersion

    def name(self, version: SRUVersion) -> Optional[str]:
        if self.parameter == ParameterInfo.Parameter.STYLESHEET:
            return SRUParam.STYLESHEET
        if self.parameter == ParameterInfo.Parameter.RENDER_BY:
            return SRUParam.RENDER_BY
        if self.parameter == ParameterInfo.Parameter.HTTP_ACCEPT:
            return SRUParam.HTTP_ACCEPT
        if self.parameter == ParameterInfo.Parameter.RESPONSE_TYPE:
            return SRUParam.RESPONSE_TYPE
        if self.parameter == ParameterInfo.Parameter.START_RECORD:
            return SRUParam.START_RECORD
        if self.parameter == ParameterInfo.Parameter.MAXIMUM_RECORDS:
            return SRUParam.MAXIMUM_RECORDS
        if self.parameter == ParameterInfo.Parameter.RECORD_SCHEMA:
            return SRUParam.RECORD_SCHEMA
        if self.parameter == ParameterInfo.Parameter.RECORD_XPATH:
            return SRUParam.RECORD_XPATH
        if self.parameter == ParameterInfo.Parameter.RESULT_SET_TTL:
            return SRUParam.RESULT_SET_TTL
        if self.parameter == ParameterInfo.Parameter.SORT_KEYS:
            return SRUParam.SORT_KEYS
        if self.parameter == ParameterInfo.Parameter.SCAN_CLAUSE:
            return SRUParam.SCAN_CLAUSE
        if self.parameter == ParameterInfo.Parameter.RESPONSE_POSITION:
            return SRUParam.RESPONSE_POSITION
        if self.parameter == ParameterInfo.Parameter.MAXIMUM_TERMS:
            return SRUParam.MAXIMUM_TERMS

        if self.parameter == ParameterInfo.Parameter.RECORD_XML_ESCAPING:
            """
            'recordPacking' was renamed to 'recordXMLEscaping' in SRU 2.0.
            For library API treat 'recordPacking' parameter as 'recordPacking'
            for SRU 1.1 and SRU 1.2.
            """
            if version == SRUVersion.VERSION_2_0:
                return SRUParam.RECORD_XML_ESCAPING
            else:
                return SRUParam.RECORD_PACKING
        if self.parameter == ParameterInfo.Parameter.RECORD_PACKING:
            """
            'recordPacking' only exists in SRU 2.0; the old variant is
            handled by the case for RECORD_XML_ESCAPING
            """
            if version == SRUVersion.VERSION_2_0:
                return SRUParam.RECORD_PACKING
            else:
                return None

        raise ValueError(f"unknown ParameterInfo.Parameter? {self.parameter}")

    def is_for_version(self, version: SRUVersion) -> bool:
        return (
            self.min.version_number <= version.version_number
            and self.max.version_number >= version.version_number
        )


class ParameterInfoSets(Enum):
    EXPLAIN = [
        ParameterInfo(
            ParameterInfo.Parameter.STYLESHEET,
            False,
            SRUVersion.VERSION_1_1,
            SRUVersion.VERSION_1_2,
        ),
        ParameterInfo(
            ParameterInfo.Parameter.RECORD_XML_ESCAPING,
            False,
            SRUVersion.VERSION_1_1,
            SRUVersion.VERSION_1_2,
        ),
    ]
    SCAN = [
        ParameterInfo(
            ParameterInfo.Parameter.STYLESHEET,
            False,
            SRUVersion.VERSION_1_1,
            SRUVersion.VERSION_2_0,
        ),
        ParameterInfo(
            ParameterInfo.Parameter.HTTP_ACCEPT,
            False,
            SRUVersion.VERSION_2_0,
            SRUVersion.VERSION_2_0,
        ),
        ParameterInfo(
            ParameterInfo.Parameter.SCAN_CLAUSE,
            True,
            SRUVersion.VERSION_1_1,
            SRUVersion.VERSION_2_0,
        ),
        ParameterInfo(
            ParameterInfo.Parameter.RESPONSE_POSITION,
            False,
            SRUVersion.VERSION_1_1,
            SRUVersion.VERSION_2_0,
        ),
        ParameterInfo(
            ParameterInfo.Parameter.MAXIMUM_TERMS,
            False,
            SRUVersion.VERSION_1_1,
            SRUVersion.VERSION_2_0,
        ),
    ]
    SEARCH_RETRIEVE = [
        ParameterInfo(
            ParameterInfo.Parameter.STYLESHEET,
            False,
            SRUVersion.VERSION_1_1,
            SRUVersion.VERSION_1_2,
        ),
        ParameterInfo(
            ParameterInfo.Parameter.HTTP_ACCEPT,
            False,
            SRUVersion.VERSION_2_0,
            SRUVersion.VERSION_2_0,
        ),
        ParameterInfo(
            ParameterInfo.Parameter.RENDER_BY,
            False,
            SRUVersion.VERSION_2_0,
            SRUVersion.VERSION_2_0,
        ),
        ParameterInfo(
            ParameterInfo.Parameter.RESPONSE_TYPE,
            False,
            SRUVersion.VERSION_2_0,
            SRUVersion.VERSION_2_0,
        ),
        ParameterInfo(
            ParameterInfo.Parameter.START_RECORD,
            False,
            SRUVersion.VERSION_1_1,
            SRUVersion.VERSION_2_0,
        ),
        ParameterInfo(
            ParameterInfo.Parameter.MAXIMUM_RECORDS,
            False,
            SRUVersion.VERSION_1_1,
            SRUVersion.VERSION_2_0,
        ),
        ParameterInfo(
            ParameterInfo.Parameter.RECORD_XML_ESCAPING,
            False,
            SRUVersion.VERSION_1_1,
            SRUVersion.VERSION_2_0,
        ),
        ParameterInfo(
            ParameterInfo.Parameter.RECORD_PACKING,
            False,
            SRUVersion.VERSION_2_0,
            SRUVersion.VERSION_2_0,
        ),
        ParameterInfo(
            ParameterInfo.Parameter.RECORD_SCHEMA,
            False,
            SRUVersion.VERSION_1_1,
            SRUVersion.VERSION_2_0,
        ),
        ParameterInfo(
            ParameterInfo.Parameter.RESULT_SET_TTL,
            False,
            SRUVersion.VERSION_1_1,
            SRUVersion.VERSION_2_0,
        ),
        ParameterInfo(
            ParameterInfo.Parameter.RECORD_XPATH,
            False,
            SRUVersion.VERSION_1_1,
            SRUVersion.VERSION_1_2,
        ),
        ParameterInfo(
            ParameterInfo.Parameter.SORT_KEYS,
            False,
            SRUVersion.VERSION_1_1,
            SRUVersion.VERSION_2_0,
        ),
    ]

    @classmethod
    def for_operation(
        cls, operation: Optional[SRUOperation]
    ) -> Optional[List[ParameterInfo]]:
        if not operation:
            return None
        if operation == SRUOperation.EXPLAIN:
            return cls.EXPLAIN.value
        if operation == SRUOperation.SCAN:
            return cls.SCAN.value
        if operation == SRUOperation.SEARCH_RETRIEVE:
            return cls.SEARCH_RETRIEVE.value
        # actually cannot happen
        return None


# ---------------------------------------------------------------------------

DEFAULT_START_RECORD = 1
DEFAULT_RESPONSE_POSITION = 1


class SRURequestImpl(SRUDiagnosticList, SRURequest):
    def __init__(
        self,
        config: SRUServerConfig,
        query_parsers: SRUQueryParserRegistry,
        request: Request,
        authentication_info_provider: Optional[SRUAuthenticationInfoProvider] = None,
    ):
        self.config = config
        self.query_parsers = query_parsers
        self.authentication_info_provider = authentication_info_provider
        self.authentication_info: Optional[SRUAuthenticationInfo] = None

        self.request = request

        self.diagnostics: List[SRUDiagnostic] = list()

        # NOTE: set default to EXPLAIN
        # (usually correctly set when parameters validated but operations
        # expect some value to be set, not None allowed)
        # FIXME: default value version None handling?
        self.operation: SRUOperation = SRUOperation.EXPLAIN
        self.version: Optional[SRUVersion] = None

        self.response_type: Optional[str] = None
        self.http_accept: Optional[str] = None

        self.record_xml_escaping: Optional[SRURecordXmlEscaping] = None
        self.record_packing: Optional[SRURecordPacking] = None
        self.renderBy: Optional[SRURenderBy] = None
        self.stylesheet: Optional[str] = None

        self.query: Optional[SRUQuery[Any]] = None

        self.start_record = DEFAULT_START_RECORD
        self.maximum_records = -1
        self.response_position = DEFAULT_RESPONSE_POSITION
        self.maximum_terms = -1
        self.record_schema_identifier: Optional[str] = None
        self.record_xpath: Optional[str] = None
        self.resultSet_TTL = -1
        self.sortKeys: Optional[str] = None
        self.scan_clause: Optional[cql.CQLQuery] = None

    # ----------------------------------------------------

    def get_request(self) -> Request:
        return self.request

    def get_operation(self) -> SRUOperation:
        return self.operation

    def get_version(self) -> SRUVersion:
        if self.version is not None:
            return self.version
        return self.config.default_version

    def get_authentication(self) -> Optional[SRUAuthenticationInfo]:
        return self.authentication_info

    def get_authentication_subject(self) -> Optional[str]:
        if not self.authentication_info:
            return None
        return self.authentication_info.subject

    # ----------------------------------------------------

    def get_query(self) -> Optional[SRUQuery[Any]]:
        return self.query

    def get_record_xml_escaping(self) -> SRURecordXmlEscaping:
        if self.record_xml_escaping is not None:
            return self.record_xml_escaping
        return self.config.default_record_xml_escaping

    def get_record_packing(self) -> SRURecordPacking:
        if self.record_packing is not None:
            return self.record_packing
        return self.config.default_record_packing

    def get_start_record(self) -> int:
        return self.start_record

    def get_maximum_records(self) -> int:
        if self.config.allow_override_maximum_records and self.get_extra_request_data(
            SRUParam.X_UNLIMITED_RESULTSET
        ):
            return -1
        if self.maximum_records == -1:
            return self.config.number_of_records
        if self.maximum_records > self.config.maximum_records:
            return self.config.maximum_records
        return self.maximum_records

    def get_record_schema_identifier(self) -> Optional[str]:
        return self.record_schema_identifier

    def get_record_xpath(self) -> Optional[str]:
        return self.record_xpath

    def get_resultSet_TTL(self) -> int:
        return self.resultSet_TTL

    def get_sortKeys(self) -> Optional[str]:
        return self.sortKeys

    def get_scan_clause(self) -> Optional[cql.CQLQuery]:
        return self.scan_clause

    def get_response_position(self) -> int:
        return self.response_position

    def get_maximum_terms(self) -> int:
        if self.config.allow_override_maximum_terms and self.get_extra_request_data(
            SRUParam.X_UNLIMITED_TERMLIST
        ):
            return -1
        if self.maximum_terms == -1:
            return self.config.number_of_terms
        if self.maximum_records > self.config.maximum_terms:
            return self.config.maximum_terms
        return self.maximum_terms

    def get_stylesheet(self) -> Optional[str]:
        return self.stylesheet

    def get_renderBy(self) -> Optional[SRURenderBy]:
        return self.renderBy

    def get_response_type(self) -> Optional[str]:
        return self.response_type

    # ----------------------------------------------------

    # raw/parameter grabby stuff

    def get_version_raw(self) -> Optional[SRUVersion]:
        return self.version

    def get_record_xml_escaping_raw(self) -> Optional[str]:
        if self.is_version(SRUVersion.VERSION_2_0):
            return self.get_parameter(SRUParam.RECORD_XML_ESCAPING, True, False)
        else:
            return self.get_parameter(SRUParam.RECORD_PACKING, True, False)

    def get_record_packing_raw(self) -> Optional[str]:
        if self.is_version(SRUVersion.VERSION_2_0):
            return self.get_parameter(SRUParam.RECORD_PACKING, True, False)
        else:
            return None

    def get_record_schema_identifier_raw(self) -> Optional[str]:
        return self.get_parameter(SRUParam.RECORD_SCHEMA, True, False)

    def get_query_raw(self) -> Optional[str]:
        return self.get_parameter(SRUParam.QUERY, True, False)

    def get_maximum_records_raw(self) -> int:
        return self.maximum_records

    def get_scan_clause_raw(self) -> Optional[str]:
        return self.get_parameter(SRUParam.SCAN_CLAUSE, True, False)

    def get_http_accept_raw(self) -> Optional[str]:
        return self.get_parameter(SRUParam.HTTP_ACCEPT, True, False)

    # FIXME: access request

    def get_indent_response(self) -> int:
        if self.config.allow_override_indent_response:
            value_str = self.get_extra_request_data(SRUParam.X_INDENT_RESPONSE)
            if value_str:
                try:
                    value = int(value_str)
                    if value > -2 and value < 9:
                        return value
                except Exception:
                    pass

        return self.config.indent_response

    def get_http_accept(self) -> Optional[str]:
        if self.http_accept is not None:
            return self.http_accept
        return self.request.headers.get("ACCEPT")

    def get_protocol_schema(self) -> str:
        return "https://" if self.request.is_secure else "http://"

    # ----------------------------------------------------

    def add_diagnostic(
        self, uri: str, details: Optional[str] = None, message: Optional[str] = None
    ) -> None:
        self.add_diagnostic_obj(SRUDiagnostic(uri, details, message))

    def add_diagnostic_obj(self, diagnostic: SRUDiagnostic):
        if self.diagnostics is None:
            self.diagnostics = list()
        self.diagnostics.append(diagnostic)

    # ----------------------------------------------------

    def _parse_number_parameter(self, param: str, value: str, min: int) -> int:
        result = -1

        if value:
            try:
                result = int(value)
                if result < min:
                    self.add_diagnostic(
                        SRUDiagnostics.UNSUPPORTED_PARAMETER_VALUE,
                        param,
                        f"Value is less than {min}.",
                    )
            except Exception:
                self.add_diagnostic(
                    SRUDiagnostics.UNSUPPORTED_PARAMETER_VALUE,
                    param,
                    "Invalid number format.",
                )

        return result

    def _parse_scan_query_parameter(
        self, param: str, value: str
    ) -> Optional[cql.CQLQuery]:
        # NOTE: this should only be called in `check_parameters_rest`
        # when version is not None anymore
        sru_query = CQLQueryParser().parse_query(
            self.version, {SRUParam.QUERY: value}, self  # type: ignore
        )
        if sru_query is None:
            return None
        return sru_query.parsed_query

    def _parse_and_check_version_parameter(
        self, operation: SRUOperation
    ) -> Optional[SRUVersion]:
        version_str = self.get_parameter(SRUParam.VERSION, True, True)
        if version_str:
            if version_str == SRUVersion.VERSION_1_1:
                return SRUVersion.VERSION_1_1
            if version_str == SRUVersion.VERSION_1_2:
                return SRUVersion.VERSION_1_2
            self.add_diagnostic(
                SRUDiagnostics.UNSUPPORTED_VERSION,
                SRUVersion.VERSION_1_2,
                f"Version '{version_str}' is not supported",
            )
            return None

        # except for "explain" operation, complain if "version" parameter
        # was not supplied.
        if operation != SRUOperation.EXPLAIN:
            self.add_diagnostic(
                SRUDiagnostics.MANDATORY_PARAMETER_NOT_SUPPLIED,
                str(SRUParam.VERSION),
                f"Mandatory parameter '{SRUParam.VERSION!s}' was not supplied.",
            )

        # this is an explain operation, assume default version
        return self.config.default_version

    # ----------------------------------------------------

    def check_parameters(self) -> bool:
        """Validate incoming request parameters

        Returns:
            bool: ``True`` if successful, ``False``  if something
                went wrong
        """
        if not self.check_parameters_version_operation():
            return False

        self._check_parameters_rest()
        self._check_parameters_auth()

        # diagnostics is None -> consider as success
        # FIXME: this should be done nicer!
        return not self.diagnostics

    def check_parameters_version_operation(self) -> bool:
        """Validate incoming request parameters **version** and
        **operation**.

        Returns:
            bool: ``True`` if successful, ``False``  if something
                went wrong
        """

        # generally assume, we will also allow processing of SRU 1.1 or 1.2
        process_SRU_old = True

        # Heuristic to detect SRU version and operation ...
        if self.config.max_version >= SRUVersion.VERSION_2_0:
            if not self.get_parameter(SRUParam.VERSION, False, False):
                # Ok, we're committed to SRU 2.0 now, so don't allow processing
                # of SRU 1.1 and 1.2 ...
                process_SRU_old = False

                LOGGER.debug(
                    "handling request as SRU 2.0, because no '%s' parameter was found in the request",
                    SRUParam.VERSION,
                )
                if self.get_parameter(
                    SRUParam.QUERY, False, False
                ) or self.get_parameter(SRUParam.QUERY_TYPE, False, False):
                    LOGGER.debug(
                        "found parameter '%s' or '%s' therefore assuming '%s' operation",
                        SRUParam.QUERY,
                        SRUParam.QUERY_TYPE,
                        SRUOperation.SEARCH_RETRIEVE,
                    )
                    operation = SRUOperation.SEARCH_RETRIEVE
                elif self.get_parameter(SRUParam.SCAN_CLAUSE, False, False):
                    LOGGER.debug(
                        "found parameter '%s' therefore assuming '%s' operation",
                        SRUParam.SCAN_CLAUSE,
                        SRUOperation.SCAN,
                    )
                    operation = SRUOperation.SCAN
                else:
                    LOGGER.debug(
                        "no special parameter found therefore assuming '%s' operation",
                        SRUOperation.EXPLAIN,
                    )
                    operation = SRUOperation.EXPLAIN

                # record version ...
                version: Optional[SRUVersion] = SRUVersion.VERSION_2_0

                # do pedantic check for 'operation' parameter
                operation_str = self.get_parameter(SRUParam.OPERATION, False, False)
                if operation_str:
                    # XXX: if operation is searchRetrive and the 'operation'
                    # parameter is also searchRetrieve, should the server just
                    # ignore it?
                    if (
                        operation != SRUOperation.SEARCH_RETRIEVE
                        and operation_str == SRUOperation.SEARCH_RETRIEVE
                    ):
                        self.add_diagnostic(
                            SRUDiagnostics.UNSUPPORTED_PARAMETER,
                            SRUParam.OPERATION,
                            message=f"Parameter '{SRUParam.OPERATION}' is not valid for SRU version 2.0",
                        )

            else:
                LOGGER.debug(
                    "handling request as legacy SRU, because found parameter '%s' in request",
                    SRUParam.VERSION,
                )

        if process_SRU_old:
            # parse mandatory operation parameter
            operation_str = self.get_parameter(SRUParam.OPERATION, False, False)
            if operation_str:
                if not operation_str.isspace():
                    if operation_str == SRUOperation.EXPLAIN:
                        operation = SRUOperation.EXPLAIN
                    elif operation_str == SRUOperation.SCAN:
                        operation = SRUOperation.SCAN
                    elif operation_str == SRUOperation.SEARCH_RETRIEVE:
                        operation = SRUOperation.SEARCH_RETRIEVE
                    else:
                        self.add_diagnostic(
                            SRUDiagnostics.UNSUPPORTED_OPERATION,
                            message=f"Operation '{operation_str}' is not supported",
                        )
                else:
                    self.add_diagnostic(
                        SRUDiagnostics.UNSUPPORTED_OPERATION,
                        message=f"An empty parameter '{SRUParam.OPERATION}' is not supported.",
                    )

                # parse and check version
                version = self._parse_and_check_version_parameter(operation)
            else:
                # absent parameter should be interpreted as "explain"
                operation = SRUOperation.EXPLAIN
                # parse and check version
                version = self._parse_and_check_version_parameter(operation)

        # sanity check
        if version and operation:
            LOGGER.debug(
                "min = %s, min? = %s, max = %s, max? = %s, version = %s",
                self.config.min_version,
                version == self.config.min_version,
                self.config.max_version,
                version == self.config.max_version,
                version,
            )
            if (
                version >= self.config.min_version
                and version <= self.config.max_version
            ):
                self.version = version
                self.operation = operation

                return True

            else:
                self.add_diagnostic(
                    SRUDiagnostics.UNSUPPORTED_VERSION,
                    self.config.max_version,
                    message=f"Version '{version}' is not supported by this endpoint.",
                )

        LOGGER.debug("bailed")
        return False

    def _check_parameters_rest(self) -> bool:
        """Validate incoming request parameters.

        Returns:
            bool: ``True`` if successful, ``False``  if something
                went wrong
        """
        if self.diagnostics:
            # this should only happen if repeatedly called
            # which is not done usually
            return False

        # check mandatory/optional parameters for operation
        parameters = ParameterInfoSets.for_operation(self.operation)
        if not parameters:
            self.add_diagnostic(
                SRUDiagnostics.GENERAL_SYSTEM_ERROR,
                message="internal error (invalid operation)",
            )
            return False

        # keep list of all submitted parameters (except "operation" and
        # "version"), so we can later warn if an unsupported parameter
        # was sent (= not all parameters were consumed).
        parameter_names = self.get_parameter_names()

        # check parameters ...
        for parameter in parameters:
            name = parameter.name(self.version)  # type: ignore
            if not name:
                # this parameter is not supported in the SRU version that
                # was used for the request
                continue

            value = self.get_parameter(name, True, True)
            if value is None:
                if parameter.mandatory:
                    self.add_diagnostic(
                        SRUDiagnostics.MANDATORY_PARAMETER_NOT_SUPPLIED,
                        name,
                        message=f"Mandatory parameter '{name}' was not supplied.",
                    )
                continue

            # remove supported parameter from list
            if name in parameter_names:
                parameter_names.remove(name)

            # if parameter is not supported in this version, skip it
            # and create add an diagnostic.
            # NOTE: version is not None
            if not parameter.is_for_version(self.version):  # type: ignore
                self.add_diagnostic(
                    SRUDiagnostics.UNSUPPORTED_PARAMETER,
                    name,
                    message=f"Version {self.version} does not support parameter '{name}'.",
                )
                continue

            # validate and parse parameters ...
            if parameter.parameter == ParameterInfo.Parameter.RECORD_XML_ESCAPING:
                if value == SRUParamValue.RECORD_XML_ESCAPING_XML:
                    self.record_xml_escaping = SRURecordXmlEscaping.XML
                elif value == SRUParamValue.RECORD_XML_ESCAPING_STRING:
                    self.record_xml_escaping = SRURecordXmlEscaping.STRING
                else:
                    self.add_diagnostic(
                        SRUDiagnostics.UNSUPPORTED_XML_ESCAPING_VALUE,
                        message=f"Record XML escaping '{value}' is not supported.",
                    )

            elif parameter.parameter == ParameterInfo.Parameter.RECORD_PACKING:
                if value == SRUParamValue.RECORD_PACKING_PACKED:
                    self.record_packing = SRURecordPacking.PACKED
                elif value == SRUParamValue.RECORD_PACKING_UNPACKED:
                    self.record_packing = SRURecordPacking.UNPACKED
                else:
                    self.add_diagnostic(
                        SRUDiagnostics.UNSUPPORTED_PARAMETER_VALUE,
                        message=f"Record packing '{value}' is not supported.",
                    )

            elif parameter.parameter == ParameterInfo.Parameter.RENDER_BY:
                if value == SRUParamValue.RENDER_BY_CLIENT:
                    self.renderBy = SRURenderBy.CLIENT
                elif value == SRUParamValue.RENDER_BY_SERVER:
                    self.renderBy = SRURenderBy.SERVER
                else:
                    self.add_diagnostic(
                        SRUDiagnostics.UNSUPPORTED_PARAMETER_VALUE,
                        message=f"Value '{value}' for parameter '{name}' is not supported.",
                    )

            elif parameter.parameter == ParameterInfo.Parameter.RECORD_SCHEMA:
                # The parameter recordSchema may contain either schema
                # identifier or the short name. If available, set to
                # appropriate schema identifier in the request object.
                schema_info = self.config.find_schema_info(value)
                if schema_info:
                    self.record_schema_identifier = schema_info.identifier
                else:
                    # SRU servers are supposed to raise a non-surrogate
                    # (fatal) diagnostic in case the record schema is not
                    # known to the server.
                    self.add_diagnostic(
                        SRUDiagnostics.UNKNOWN_SCHEMA_FOR_RETRIEVAL,
                        value,
                        message=f"Record schema '{value}' is not supported for retrieval.",
                    )

            elif parameter.parameter == ParameterInfo.Parameter.START_RECORD:
                self.start_record = self._parse_number_parameter(name, value, 1)
            elif parameter.parameter == ParameterInfo.Parameter.RESPONSE_POSITION:
                self.response_position = self._parse_number_parameter(name, value, 0)
            elif parameter.parameter == ParameterInfo.Parameter.MAXIMUM_RECORDS:
                self.maximum_records = self._parse_number_parameter(name, value, 0)
            elif parameter.parameter == ParameterInfo.Parameter.MAXIMUM_TERMS:
                self.maximum_terms = self._parse_number_parameter(name, value, 0)
            elif parameter.parameter == ParameterInfo.Parameter.RESULT_SET_TTL:
                self.resultSet_TTL = self._parse_number_parameter(name, value, 0)

            elif parameter.parameter == ParameterInfo.Parameter.SCAN_CLAUSE:
                self.scan_clause = self._parse_scan_query_parameter(name, value)

            elif parameter.parameter == ParameterInfo.Parameter.RECORD_XPATH:
                self.record_xpath = value
            elif parameter.parameter == ParameterInfo.Parameter.SORT_KEYS:
                self.sortKeys = value
            elif parameter.parameter == ParameterInfo.Parameter.STYLESHEET:
                self.stylesheet = value

            elif parameter.parameter == ParameterInfo.Parameter.RESPONSE_TYPE:
                # FIXME: check parameter validity?!
                self.response_type = value
            elif parameter.parameter == ParameterInfo.Parameter.HTTP_ACCEPT:
                # FIXME: check parameter validity?!
                self.http_accept = value

        # handle query and queryType
        if self.operation == SRUOperation.SEARCH_RETRIEVE:
            # determine queryType
            query_type: Optional[str] = None
            if self.version == SRUVersion.VERSION_2_0:
                if SRUParam.QUERY_TYPE in parameter_names:
                    parameter_names.remove(SRUParam.QUERY_TYPE)
                value = self.get_parameter(SRUParam.QUERY_TYPE, True, True)
                if value is None:
                    query_type = SRUQueryType.CQL.value
                else:
                    has_bad_chars = QUERY_TYPE_ALLOWED_CHARS.fullmatch(value) is None
                    if has_bad_chars:
                        self.add_diagnostic(
                            SRUDiagnostics.UNSUPPORTED_PARAMETER_VALUE,
                            SRUParam.QUERY_TYPE,
                            message="Value contains illegal characters.",
                        )
                    else:
                        query_type = value
            else:
                # SRU 1.1 and SRU 1.2 only support CQL
                query_type = SRUQueryType.CQL.value

            if query_type:
                LOGGER.debug("looking for query parser for query type '%s'", query_type)
                query_parser = self.query_parsers.find_query_parser(query_type)
                if query_parser:
                    if query_parser.supports_version(self.version):
                        # gather query parameters
                        # (as required by QueryParser implementation)
                        query_parameters = dict()
                        missing_parameters = list()
                        for name in query_parser.query_parameter_names:
                            if name in parameter_names:
                                parameter_names.remove(name)
                            value = self.get_parameter(name, True, False)
                            if value is not None:
                                query_parameters[name] = value
                            else:
                                missing_parameters.append(name)

                        if not missing_parameters:
                            LOGGER.debug(
                                "parsing query with parser for type '%s' and parameters %s",
                                query_parser.query_type,
                                query_parameters,
                            )
                            # NOTE: version is not None
                            self.query = query_parser.parse_query(
                                self.version, query_parameters, self  # type: ignore
                            )
                            if not self.query:
                                LOGGER.debug("query parser failed to parse query")
                                self.add_diagnostic(
                                    SRUDiagnostics.QUERY_SYNTAX_ERROR,
                                    message="Query could not be parsed.",
                                )
                        else:
                            LOGGER.debug(
                                "parameters %s missing, cannot parse query",
                                missing_parameters,
                            )
                            for name in missing_parameters:
                                self.add_diagnostic(
                                    SRUDiagnostics.MANDATORY_PARAMETER_NOT_SUPPLIED,
                                    name,
                                    message=(
                                        f"Mandatory parameter '{name}' is missing or empty. "
                                        f"Required to perform query of query type '{query_type}'."
                                    ),
                                )

                    else:
                        LOGGER.debug(
                            "query parser for query type '%s' is not supported by SRU version %s",
                            query_type,
                            self.version,
                        )
                        self.add_diagnostic(
                            SRUDiagnostics.CANNOT_PROCESS_QUERY_REASON_UNKNOWN,
                            message=(
                                f"Query parser for query type '{query_type}' is not"
                                f" supported by SRU version '{self.version}'."
                            ),
                        )

                else:
                    LOGGER.debug("no parser for query type '%s' found", query_type)
                    self.add_diagnostic(
                        SRUDiagnostics.CANNOT_PROCESS_QUERY_REASON_UNKNOWN,
                        message=f"Cannot find query parser for query type '{query_type}'.",
                    )

            else:
                LOGGER.debug("cannot determine query type")
                self.add_diagnostic(
                    SRUDiagnostics.CANNOT_PROCESS_QUERY_REASON_UNKNOWN,
                    message="Cannot determine query type.",
                )

        # check if any parameters where not consumed and
        # add appropriate warnings
        if parameter_names:
            for name in parameter_names:
                # skip extraRequestData (aka extensions)
                if not name.startswith(PARAM_EXTENSION_PREFIX):
                    self.add_diagnostic(
                        SRUDiagnostics.UNSUPPORTED_PARAMETER,
                        name,
                        message=f"Parameter '{name}' is not supported for this operation.",
                    )

        # diagnostics is None -> consider as success
        # FIXME: this should be done nicer!
        return not self.diagnostics

    def _check_parameters_auth(self) -> None:
        # extract authentication information from,
        # if an authentication provider is set
        if self.authentication_info_provider:
            try:
                self.authentication_info = (
                    self.authentication_info_provider.get_AuthenticationInfo(
                        self.request
                    )
                )
            except SRUException as ex:
                self.add_diagnostic_obj(ex.get_diagnostic())

    # ----------------------------------------------------

    def get_parameter_names(self) -> List[str]:
        parameters = list(self.request.args.keys())
        parameters = [
            p for p in parameters if p not in (SRUParam.OPERATION, SRUParam.VERSION)
        ]
        return parameters

    def get_parameter(
        self, name: Union[SRUParam, str], nullify: bool, diagnostic_if_empty: bool
    ) -> Optional[str]:
        value = self.request.args.get(name)
        if value is not None:
            value = value.strip()
            if nullify and not value:
                value = None
                if diagnostic_if_empty:
                    self.add_diagnostic(
                        SRUDiagnostics.UNSUPPORTED_PARAMETER_VALUE,
                        name,
                        message=f"An empty parameter '{name}' is not supported.",
                    )
        return value

    def get_extra_request_data_names(self) -> List[str]:
        parameters = list(self.request.args.keys())
        parameters = [p for p in parameters if p.startswith(PARAM_EXTENSION_PREFIX)]
        return parameters

    def get_extra_request_data(self, name: str) -> Optional[str]:
        if name is None:
            raise TypeError("name is None")
        if not name.startswith(PARAM_EXTENSION_PREFIX):
            raise ValueError(f"name must start with '{PARAM_EXTENSION_PREFIX}'")
        return self.request.args.get(name)


# ---------------------------------------------------------------------------
