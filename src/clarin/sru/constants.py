from enum import Enum
from typing import Optional

# ---------------------------------------------------------------------------


class SRUOperation(str, Enum):
    """SRU operation"""

    def __str__(self) -> str:
        return self.value

    #: A ``explain`` operation
    EXPLAIN = "explain"
    """A ``explain`` operation"""

    SEARCH_RETRIEVE = "searchRetrieve"
    """A ``searchRetrieve`` operation"""

    SCAN = "scan"
    """A ``scan`` operation"""


class SRUQueryType(str, Enum):
    def __str__(self) -> str:
        return self.value

    CQL = "cql"
    """shorthand queryType identifier for CQL"""

    SEARCH_TERMS = "searchTerms"


class SRURecordPacking(str, Enum):
    """SRU 2.0 record packing."""

    def __str__(self) -> str:
        return self.value

    PACKED = "packed"
    """The client requests that the server should supply records strictly
    according to the requested schema."""

    UNPACKED = "unpacked"
    """The server is free to allow the location of application data to vary
    within the record."""


class SRURecordXmlEscaping(str, Enum):
    """SRU Record XML escaping (or record packing in SRU 1.2)."""

    def __str__(self) -> str:
        return self.value

    XML = "xml"
    """XML record packing"""

    STRING = "string"
    """String record packing"""


class SRURenderBy(str, Enum):
    """SRU Record XML escaping."""

    def __str__(self) -> str:
        return self.value

    CLIENT = "client"
    """The client requests that the server simply return this URL in
    the response, in the href attribute of the xml-stylesheet
    processing instruction before the response xml."""

    SERVER = "server"
    """The client requests that the server format the response
    according to the specified stylesheet, assuming the default SRU
    response schema as input to the stylesheet."""


class SRUResultCountPrecision(str, Enum):
    """(SRU 2.0) Indicate the accuracy of the result count reported
    by total number of records that matched the query."""

    def __str__(self) -> str:
        return self.value

    EXACT = "exact"
    """The server guarantees that the reported number of records is accurate."""

    UNKNOWN = "unknown"
    """The server has no idea what the result count is, and does not want to
    venture an estimate."""

    ESTIMATE = "estimate"
    """The server does not know the result set count, but offers an estimate."""

    MAXIMUM = "maximum"
    """The value supplied is an estimate of the maximum possible count that the
    result set will attain."""

    MINIMUM = "minimum"
    """The server does not know the result count but guarantees that it is at
    least this large."""

    CURRENT = "current"
    """The value supplied is an estimate of the count at the time the response
    was sent, however the result set may continue to grow."""


# ---------------------------------------------------------------------------


class SRUVersion(str, Enum):
    """SRU version"""

    def __new__(cls, major: int, minor: int):
        obj = str.__new__(cls, f"{major}.{minor}")
        obj._value_ = f"{major}.{minor}"
        obj.major = major
        obj.minor = minor
        return obj

    major: int
    minor: int

    @property
    def version_number(self) -> int:
        return (self.major << 16) | self.minor

    @property
    def version_string(self) -> str:
        return self.value

    def __str__(self) -> str:
        return self.value

    VERSION_1_1 = (1, 1)
    VERSION_1_2 = (1, 2)
    VERSION_2_0 = (2, 0)


# ---------------------------------------------------------------------------
# Diagnostics

SRU_DIAGNOSTIC_RECORD_SCHEMA = "info:srw/schema/1/diagnostics-v1.1"
SRU_DIAGNOSTIC_URI_PREFIX = "info:srw/diagnostic/1/"


class SRUDiagnostics(str, Enum):
    """Constants for SRU diagnostics

    See also:
        * SRU Diagnostics: http://www.loc.gov/standards/sru/diagnostics/
        * SRU Diagnostics List: http://www.loc.gov/standards/sru/diagnostics/diagnosticsList.html
    """

    def __new__(cls, nr: int, category: str, description: str):
        obj = str.__new__(cls, f"{SRU_DIAGNOSTIC_URI_PREFIX}{nr}")
        obj._value_ = f"{SRU_DIAGNOSTIC_URI_PREFIX}{nr}"
        obj.nr = nr
        obj.category = category
        obj.description = description
        obj.__doc__ = description
        return obj

    nr: int
    category: str
    description: str

    # fmt: off

    # general diagnostics
    GENERAL_SYSTEM_ERROR = (1, "general", "General system error")
    SYSTEM_TEMPORARILY_UNAVAILABLE = (2, "general", "System temporarily unavailable")
    AUTHENTICATION_ERROR = (3, "general", "Authentication error")
    UNSUPPORTED_OPERATION = (4, "general", "Unsupported operation")
    UNSUPPORTED_VERSION = (5, "general", "Unsupported version")
    UNSUPPORTED_PARAMETER_VALUE = (6, "general", "Unsupported parameter value")
    MANDATORY_PARAMETER_NOT_SUPPLIED = (7, "general", "Mandatory parameter not supplied")
    UNSUPPORTED_PARAMETER = (8, "general", "Unsupported Parameter")
    DATABASE_DOES_NOT_EXIST = (235, "general", "Database does not exist")

    # diagnostics relating to CQL
    QUERY_SYNTAX_ERROR = (10, "cql", "Query syntax erro")
    TOO_MANY_CHARACTERS_IN_QUERY = (12, "cql", "Too many characters in query")
    INVALID_OR_UNSUPPORTED_USE_OF_PARENTHESES = (13, "cql", "Invalid or unsupported use of parentheses")
    INVALID_OR_UNSUPPORTED_USE_OF_QUOTES = (14, "cql", "Invalid or unsupported use of quotes")
    UNSUPPORTED_CONTEXT_SET = (15, "cql", "Unsupported context set")
    UNSUPPORTED_INDEX = (16, "cql", "Unsupported index")
    UNSUPPORTED_COMBINATION_OF_INDEXES = (18, "cql", "Unsupported combination of indexes")
    UNSUPPORTED_RELATION = (19, "cql", "Unsupported relation")
    UNSUPPORTED_RELATION_MODIFIER = (20, "cql", "Unsupported relation modifier")
    UNSUPPORTED_COMBINATION_OF_RELATION_MODIFERS = (21, "cql", "Unsupported combination of relation modifers")
    UNSUPPORTED_COMBINATION_OF_RELATION_AND_INDEX = (22, "cql", "Unsupported combination of relation and index")
    TOO_MANY_CHARACTERS_IN_TERM = (23, "cql", "Too many characters in term")
    UNSUPPORTED_COMBINATION_OF_RELATION_AND_TERM = (24, "cql", "Unsupported combination of relation and term")
    NON_SPECIAL_CHARACTER_ESCAPED_IN_TERM = (26, "cql", "Non special character escaped in term")
    EMPTY_TERM_UNSUPPORTED = (27, "cql", "Empty term unsupported")
    MASKING_CHARACTER_NOT_SUPPORTED = (28, "cql", "Masking character not supported")
    MASKED_WORDS_TOO_SHORT = (29, "cql", "Masked words too short")
    TOO_MANY_MASKING_CHARACTERS_IN_TERM = (30, "cql", "Too many masking characters in term")
    ANCHORING_CHARACTER_NOT_SUPPORTED = (31, "cql", "Anchoring character not supported")
    ANCHORING_CHARACTER_IN_UNSUPPORTED_POSITION = (32, "cql", "Anchoring character in unsupported position")
    COMBINATION_OF_PROXIMITY_ADJACENCY_AND_MASKING_CHARACTERS_NOT_SUPPORTED = (33, "cql", "Combination of proximity/adjacency and masking characters not supported")
    COMBINATION_OF_PROXIMITY_ADJACENCY_AND_ANCHORING_CHARACTERS_NOT_SUPPORTED = (34, "cql", "Combination of proximity/adjacency and anchoring characters not supported")
    TERM_CONTAINS_ONLY_STOPWORDS = (35, "cql", "Term contains only stopwords")
    TERM_IN_INVALID_FORMAT_FOR_INDEX_OR_RELATION = (36, "cql", "Term in invalid format for index or relation")
    UNSUPPORTED_BOOLEAN_OPERATOR = (37, "cql", "Unsupported boolean operator")
    TOO_MANY_BOOLEAN_OPERATORS_IN_QUERY = (38, "cql", "Too many boolean operators in query")
    PROXIMITY_NOT_SUPPORTED = (39, "cql", "Proximity not supporte")
    UNSUPPORTED_PROXIMITY_RELATION = (40, "cql", "Unsupported proximity relation")
    UNSUPPORTED_PROXIMITY_DISTANCE = (41, "cql", "Unsupported proximity distance")
    UNSUPPORTED_PROXIMITY_UNIT = (42, "cql", "Unsupported proximity unit")
    UNSUPPORTED_PROXIMITY_ORDERING = (43, "cql", "Unsupported proximity ordering")
    UNSUPPORTED_COMBINATION_OF_PROXIMITY_MODIFIERS = (44, "cql", "Unsupported combination of proximity modifiers")
    UNSUPPORTED_BOOLEAN_MODIFIER = (46, "cql", "Unsupported boolean modifier")
    CANNOT_PROCESS_QUERY_REASON_UNKNOWN = (47, "cql", "Cannot process query; reason unknown")
    QUERY_FEATURE_UNSUPPORTED = (48, "cql", "Query feature unsupported")
    MASKING_CHARACTER_IN_UNSUPPORTED_POSITION = (49, "cql", "Masking character in unsupported position")

    # diagnostics relating to result sets
    RESULT_SETS_NOT_SUPPORTED = (50, "result sets", "Result sets not supported")
    RESULT_SET_DOES_NOT_EXIST = (51, "result sets", "Result set does not exist")
    RESULT_SET_TEMPORARILY_UNAVAILABLE = (52, "result sets", "Result set temporarily unavailable")
    RESULT_SETS_ONLY_SUPPORTED_FOR_RETRIEVAL = (53, "result sets", "Result sets only supported for retrieval")
    COMBINATION_OF_RESULT_SETS_WITH_SEARCH_TERMS_NOT_SUPPORTED = (55, "result sets", "Combination of result sets with search terms not supported")
    RESULT_SET_CREATED_WITH_UNPREDICTABLE_PARTIAL_RESULTS_AVAILABLE = (58, "result sets", "Result set created with unpredictable partial results available")
    RESULT_SET_CREATED_WITH_VALID_PARTIAL_RESULTS_AVAILABLE = (59, "result sets", "Result set created with valid partial results available")
    RESULT_SET_NOT_CREATED_TOO_MANY_MATCHING_RECORDS = (60, "result sets", "Result set not created: too many matching records")

    # diagnostics relating to records
    FIRST_RECORD_POSITION_OUT_OF_RANGE = (61, "records", "First record position out of range")
    RECORD_TEMPORARILY_UNAVAILABLE = (64, "records", "Record temporarily unavailable")
    RECORD_DOES_NOT_EXIST = (65, "records", "Record does not exist")
    UNKNOWN_SCHEMA_FOR_RETRIEVAL = (66, "records", "Unknown schema for retrieval")
    RECORD_NOT_AVAILABLE_IN_THIS_SCHEMA = (67, "records", "Record not available in this schema")
    NOT_AUTHORISED_TO_SEND_RECORD = (68, "records", "Not authorised to send record")
    NOT_AUTHORISED_TO_SEND_RECORD_IN_THIS_SCHEMA = (69, "records", "Not authorised to send record in this schema")
    RECORD_TOO_LARGE_TO_SEND = (70, "records", "Record too large to send")
    UNSUPPORTED_XML_ESCAPING_VALUE = (71, "records", "Unsupported record packing")
    XPATH_RETRIEVAL_UNSUPPORTED = (72, "records", "XPath retrieval unsupported")
    XPATH_EXPRESSION_CONTAINS_UNSUPPORTED_FEATURE = (73, "records", "XPath expression contains unsupported feature")
    UNABLE_TO_EVALUATE_XPATH_EXPRESSION = (74, "records", "Unable to evaluate XPath expression")

    # diagnostics relating to sorting
    SORT_NOT_SUPPORTED = (80, "sorting", "Sort not supported")
    UNSUPPORTED_SORT_SEQUENCE = (82, "sorting", "Unsupported sort sequence")
    TOO_MANY_RECORDS_TO_SORT = (83, "sorting", "Too many records to sort")
    TOO_MANY_SORT_KEYS_TO_SORT = (84, "sorting", "Too many sort keys to sort")
    CANNOT_SORT_INCOMPATIBLE_RECORD_FORMATS = (86, "sorting", "Cannot sort: incompatible record format")
    UNSUPPORTED_SCHEMA_FOR_SORT = (87, "sorting", "Unsupported schema for sort")
    UNSUPPORTED_PATH_FOR_SORT = (88, "sorting", "Unsupported path for sort")
    PATH_UNSUPPORTED_FOR_SCHEMA = (89, "sorting", "Path unsupported for schema")
    UNSUPPORTED_DIRECTION = (90, "sorting", "Unsupported direction")
    UNSUPPORTED_CASE = (91, "sorting", "Unsupported case")
    UNSUPPORTED_MISSING_VALUE_ACTION = (92, "sorting", "Unsupported missing value action")
    SORT_ENDED_DUE_TO_MISSING_VALUE = (93, "sorting", "Sort ended due to missing value ")
    SORT_SPEC_INCLUDED_BOTH_IN_QUERY_AND_PROTOCOL_QUERY_PREVAILS = (94, "sorting", "Sort spec included both in query and protocol: query prevails")
    SORT_SPEC_INCLUDED_BOTH_IN_QUERY_AND_PROTOCOL_PROTOCOL_PREVAILS = (95, "sorting", "Sort spec included both in query and protocol: protocol prevails")
    SORT_SPEC_INCLUDED_BOTH_IN_QUERY_AND_PROTOCOL_ERROR = (96, "sorting", "Sort spec included both in query and protocol: error")

    # diagnostics relating to stylesheets
    STYLESHEETS_NOT_SUPPORTED = (110, "stylesheets", "Stylesheets not supported")
    UNSUPPORTED_STYLESHEET = (111, "stylesheets", "Unsupported stylesheet")

    # diagnostics relating to scan
    RESPONSE_POSITION_OUT_OF_RANGE = (120, "scan", "Response position out of range")
    TOO_MANY_TERMS_REQUESTED = (121, "scan", "Too many terms requested")

    # fmt: on

    @classmethod
    def get_by_uri(cls, uri: str) -> Optional["SRUDiagnostics"]:
        if not uri:
            return None
        for _, member in cls.__members__.items():
            if member.value == uri:
                return member
        return None


# ---------------------------------------------------------------------------


RESPONSE_ENCODING = "utf-8"
RESPONSE_CONTENT_TYPE = "application/xml"

PARAM_EXTENSION_PREFIX = "x-"


class SRUParam(str, Enum):
    def __str__(self) -> str:
        return self.value

    # general / explain related parameter names
    OPERATION = "operation"
    VERSION = "version"
    STYLESHEET = "stylesheet"
    RENDER_BY = "renderedBy"
    HTTP_ACCEPT = "httpAccept"
    RESPONSE_TYPE = "responseType"

    # searchRetrieve related parameter names
    QUERY = "query"
    QUERY_TYPE = "queryType"
    START_RECORD = "startRecord"
    MAXIMUM_RECORDS = "maximumRecords"
    RECORD_XML_ESCAPING = "recordXMLEscaping"
    RECORD_PACKING = "recordPacking"
    RECORD_SCHEMA = "recordSchema"
    RECORD_XPATH = "recordXPath"
    RESULT_SET_TTL = "resultSetTTL"
    SORT_KEYS = "sortKeys"

    # scan related parameter names
    SCAN_CLAUSE = "scanClause"
    RESPONSE_POSITION = "responsePosition"
    MAXIMUM_TERMS = "maximumTerms"

    X_UNLIMITED_RESULTSET = "x-unlimited-resultset"
    X_UNLIMITED_TERMLIST = "x-unlimited-termlist"
    X_INDENT_RESPONSE = "x-indent-response"


class SRUParamValue(str, Enum):
    def __str__(self) -> str:
        return self.value

    # operations
    OP_EXPLAIN = "explain"
    OP_SCAN = "scan"
    OP_SEARCH_RETRIEVE = "searchRetrieve"
    VERSION_1_1 = "1.1"
    VERSION_1_2 = "1.2"

    # various parameter values
    RECORD_XML_ESCAPING_XML = "xml"
    RECORD_XML_ESCAPING_STRING = "string"
    RECORD_PACKING_PACKED = "packed"
    RECORD_PACKING_UNPACKED = "unpacked"
    RENDER_BY_CLIENT = "client"
    RENDER_BY_SERVER = "server"


# ---------------------------------------------------------------------------
