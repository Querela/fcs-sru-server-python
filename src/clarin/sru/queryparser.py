from abc import ABC
from abc import abstractmethod
from typing import Any
from typing import Dict
from typing import Generic
from typing import List
from typing import Optional
from typing import Type
from typing import TypeVar

import cql

from .constants import SRUDiagnostics
from .constants import SRUParam
from .constants import SRUQueryType
from .constants import SRUVersion
from .diagnostic import SRUDiagnosticList
from .exception import SRUConfigException

_T = TypeVar("_T")


# ---------------------------------------------------------------------------


class SRUQuery(ABC, Generic[_T]):
    """Holder class for a parsed query to be returned from a
    `SRUQueryParser`."""

    def __init__(self, raw_query: str, parsed_query: _T):
        super().__init__()
        if raw_query is None:
            raise TypeError("raw_query is None")
        if parsed_query is None:
            raise TypeError("parsed_query is None")
        self._raw_query = raw_query
        self._parsed_query = parsed_query

    @property
    @abstractmethod
    def query_type(self) -> str:
        """Get the short name for supported query, e.g. "cql"."""

    @property
    def raw_query(self) -> str:
        """Get the original query as a string."""
        return self._raw_query

    @property
    def parsed_query(self) -> _T:
        """Get the parsed query as an abstract syntax tree."""
        return self._parsed_query


# ---------------------------------------------------------------------------


class SRUQueryParser(ABC, Generic[_T]):
    """Interface for implementing pluggable query parsers.

    Parameterized by 'abstract syntax tree (object) for parsed queries.'
    """

    @property
    @abstractmethod
    def query_type(self) -> str:
        """Get the short name for supported query, e.g. "cql"."""

    @abstractmethod
    def supports_version(self, version: Optional[SRUVersion]) -> bool:
        """Check if query is supported by a specific version of SRU/CQL."""

    @property
    def query_type_definition(self) -> Optional[str]:
        """The URI for the for the query type's definition."""
        return None

    @property
    @abstractmethod
    def query_parameter_names(self) -> List[str]:
        """Get the list of query parameters."""

    @abstractmethod
    def parse_query(
        self,
        version: SRUVersion,
        parameters: Dict[str, str],
        diagnostics: SRUDiagnosticList,
    ) -> Optional[SRUQuery[_T]]:
        """Parse a query into an abstract syntax tree.

        Args:
            version: the SRU version the request was made
            parameters: the request parameters containing the query
            diagnostics: a `SRUDiagnosticList` for storing fatal and
                non-fatal diagnostics

        Returns:
            the parsed query or ``None`` if the query could not be parsed
        """


# ---------------------------------------------------------------------------


class SRUQueryParserRegistry:
    """A registry to keep track of registered `SRUQueryParser` to be
    used by the `SRUServer`.

    See also:
        `SRUQueryParser`
    """

    def __init__(self, parsers: List[SRUQueryParser[Any]]):
        if parsers is None:
            raise TypeError("parsers is None")
        if not parsers:
            raise ValueError("parsers is empty")
        self.parsers = list(parsers)

    @property
    def query_parsers(self) -> List[SRUQueryParser[Any]]:
        """Get a list of all registered query parsers.

        Returns:
            List[SRUQueryParser[Any]]: a list of registered query
                parsers
        """
        return self.parsers

    def find_query_parser(self, query_type: str) -> Optional[SRUQueryParser[Any]]:
        """Find a query parser by query type.

        Args:
            query_type: the query type to search for

        Returns:
            SRUQueryParser[Any]: the matching `SRUQueryParser`
                instance or ``None`` if no matching parser was found.
        """
        if query_type is None:
            raise TypeError("query_type is None")
        return SRUQueryParserRegistry._find_parser(self.parsers, query_type)

    @staticmethod
    def _find_parser(
        parsers: List[SRUQueryParser[Any]], query_type: str
    ) -> Optional[SRUQueryParser[Any]]:
        for parser in parsers:
            if query_type == parser.query_type:
                return parser
        return None

    # ----------------------------------------------------

    class Builder:
        """Builder for creating `SRUQueryParserRegistry` instances."""

        def __init__(self, register_defaults: bool = True):
            """[Constructor]

            Args:
                register_defaults: if ``True``,
                    register SRU/CQL standard query parsers
                    (queryType **cql** and **searchTerms**),
                    otherwise do nothing. Defaults to True.
            """
            self.parsers: List[SRUQueryParser[Any]] = list()
            if register_defaults:
                self.register_defaults()

        def register_defaults(self) -> "SRUQueryParserRegistry.Builder":
            """Registers registers SRU/CQL standard query parsers
            (queryType **cql** and **searchTerms**)."""
            if not SRUQueryParserRegistry._find_parser(self.parsers, SRUQueryType.CQL):
                try:
                    self.register(CQLQueryParser())
                except SRUConfigException:
                    pass

            if not SRUQueryParserRegistry._find_parser(
                self.parsers, SRUQueryType.SEARCH_TERMS
            ):
                try:
                    self.register(SearchTermsQueryParser())
                except SRUConfigException:
                    pass

            return self

        def register(
            self, parser: SRUQueryParser[Any]
        ) -> "SRUQueryParserRegistry.Builder":
            """Register a new query parser

            Args:
                parser (SRUQueryParser[Any]): the query parser
                    instance to be registered

            Raises:
                `SRUConfigException`: if a query parser for the same
                    query type was already registered
            """
            if parser is None:
                raise TypeError("parser is None")
            if parser.query_type is None:
                raise TypeError("parser.query_type is None")

            # duplicate-save add ...
            if not SRUQueryParserRegistry._find_parser(self.parsers, parser.query_type):
                self.parsers.append(parser)
            else:
                raise SRUConfigException(
                    f"query parser for query_type '{parser.query_type}' is already registered"
                )

            return self

        def build(self) -> "SRUQueryParserRegistry":
            """Create a configured `SRUQueryParserRegistry` instance
            from this builder.

            Returns:
                SRUQueryParserRegistry: a `SRUQueryParserRegistry`
                    instance
            """
            return SRUQueryParserRegistry(self.parsers)


# ---------------------------------------------------------------------------


class SearchTermsQuery(SRUQuery[List[str]]):
    @property
    def query_type(self) -> str:
        return SRUQueryType.SEARCH_TERMS.value


class SearchTermsQueryParser(SRUQueryParser[List[str]]):
    @property
    def query_type(self) -> str:
        return SRUQueryType.SEARCH_TERMS

    @property
    def query_parameter_names(self) -> List[str]:
        return [SRUParam.QUERY.value]

    def supports_version(self, version: Optional[SRUVersion]) -> bool:
        if not version:
            raise TypeError("Argument version is invalid/None.")
        # java: version.compareTo(SRUVersion.VERSION_2_0) >= 0
        return version < SRUVersion.VERSION_2_0

    def parse_query(
        self,
        version: SRUVersion,
        parameters: Dict[str, str],
        diagnostics: SRUDiagnosticList,
    ) -> Optional[SRUQuery[List[str]]]:
        raw_query = parameters.get(SRUParam.QUERY)
        if raw_query is None:
            diagnostics.add_diagnostic(
                SRUDiagnostics.GENERAL_SYSTEM_ERROR,
                message="no query passed to query parser",
            )
            return None

        terms = raw_query.split()
        return SearchTermsQuery(raw_query, terms)


# ---------------------------------------------------------------------------


class CQLQuery(SRUQuery[cql.CQLQuery]):
    @property
    def query_type(self) -> str:
        return SRUQueryType.CQL.value


class CQLQueryParser(SRUQueryParser[cql.CQLQuery]):
    """Default query parser to parse CQL."""

    @property
    def query_type(self) -> str:
        return SRUQueryType.CQL

    @property
    def query_parameter_names(self) -> List[str]:
        return [SRUParam.QUERY.value]

    def supports_version(self, version: Optional[SRUVersion]) -> bool:
        if not version:
            raise TypeError("Argument version is invalid/None.")
        # CQL is supported by all SRU versions ...
        return True

    def parse_query(
        self,
        version: SRUVersion,
        parameters: Dict[str, str],
        diagnostics: SRUDiagnosticList,
    ) -> Optional[SRUQuery[cql.CQLQuery]]:
        raw_query = parameters.get(SRUParam.QUERY)
        if raw_query is None:
            diagnostics.add_diagnostic(
                SRUDiagnostics.GENERAL_SYSTEM_ERROR,
                message="no query passed to query parser",
            )
            return None

        # XXX: maybe query length against limit and return
        # "Too many characters in query" error?

        try:
            parser_cls: Type[cql.CQLParser] = cql.CQLParser12
            if version == SRUVersion.VERSION_1_1:
                parser_cls = cql.CQLParser11
            elif version in (SRUVersion.VERSION_1_2, SRUVersion.VERSION_2_0):
                parser_cls = cql.CQLParser12

            parser = parser_cls()
            parser.build()

            parsed_query = parser.parse(raw_query)
            return CQLQuery(raw_query, parsed_query)
        except cql.parser.CQLParserError:
            diagnostics.add_diagnostic(
                SRUDiagnostics.QUERY_SYNTAX_ERROR, message="error parsing query"
            )
        except Exception:
            diagnostics.add_diagnostic(
                SRUDiagnostics.QUERY_SYNTAX_ERROR, message="error parsing query"
            )

        return None


# ---------------------------------------------------------------------------
