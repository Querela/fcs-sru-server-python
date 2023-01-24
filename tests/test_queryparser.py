from typing import Optional

import cql
import pytest

from clarin.sru.constants import SRUParam
from clarin.sru.constants import SRUVersion
from clarin.sru.diagnostic import SRUDiagnosticList
from clarin.sru.queryparser import CQLQueryParser
from clarin.sru.queryparser import SearchTermsQuery
from clarin.sru.queryparser import SearchTermsQueryParser
from clarin.sru.queryparser import SRUQueryParser
from clarin.sru.queryparser import SRUQueryParserRegistry

# ---------------------------------------------------------------------------


def test_registry():
    with pytest.raises(TypeError):
        SRUQueryParserRegistry()

    with pytest.raises(TypeError):
        SRUQueryParserRegistry(None)

    with pytest.raises(ValueError):
        SRUQueryParserRegistry([])

    # NOTE: no type check; usually type hints (mypy etc) should check this?
    reg = SRUQueryParserRegistry(["parser1", "parser2"])
    assert ["parser1", "parser2"] == reg.parsers
    assert ["parser1", "parser2"] == reg.query_parsers

    # ----------------------------------------------------

    reg = SRUQueryParserRegistry.Builder(True).build()
    assert isinstance(
        reg.find_query_parser(SearchTermsQueryParser().query_type),
        SearchTermsQueryParser,
    )

    with pytest.raises(TypeError):
        reg.find_query_parser(None)


def test_registry_builder():
    bi = SRUQueryParserRegistry.Builder(False)
    assert not bi.parsers
    with pytest.raises(ValueError, match="parsers is empty"):
        bi.build()

    bi = SRUQueryParserRegistry.Builder(True)
    assert len(bi.parsers) == 2
    assert all(isinstance(p, SRUQueryParser) for p in bi.parsers)
    assert any(isinstance(p, SearchTermsQueryParser) for p in bi.parsers)
    assert any(isinstance(p, CQLQueryParser) for p in bi.parsers)
    reg = bi.build()
    assert len(reg.parsers) == 2
    assert len(reg.query_parsers) == 2
    assert all(isinstance(p, SRUQueryParser) for p in reg.parsers)
    assert any(isinstance(p, SearchTermsQueryParser) for p in reg.parsers)
    assert any(isinstance(p, CQLQueryParser) for p in reg.parsers)

    bi = SRUQueryParserRegistry.Builder(True)
    # only registers them once
    # NOTE: that subclassed queryparsers will also can not be registered
    bi.register_defaults()
    bi.register_defaults()
    bi.register_defaults()
    assert len(bi.parsers) == 2
    assert len(reg.query_parsers) == 2
    assert all(isinstance(p, SRUQueryParser) for p in bi.parsers)
    assert any(isinstance(p, SearchTermsQueryParser) for p in bi.parsers)
    assert any(isinstance(p, CQLQueryParser) for p in bi.parsers)

    bi = SRUQueryParserRegistry.Builder(False)
    bi.register_defaults()
    assert len(bi.parsers) == 2
    assert len(reg.query_parsers) == 2
    assert all(isinstance(p, SRUQueryParser) for p in bi.parsers)
    assert any(isinstance(p, SearchTermsQueryParser) for p in bi.parsers)
    assert any(isinstance(p, CQLQueryParser) for p in bi.parsers)


# ---------------------------------------------------------------------------


class MyTestDiagsList(SRUDiagnosticList):
    def __init__(self) -> None:
        self.diags = list()

    def add_diagnostic(
        self, uri: str, details: Optional[str] = None, message: Optional[str] = None
    ) -> None:
        self.diags.append((uri, details, message))


def test_SRUQuery():
    from clarin.sru.queryparser import CQLQuery
    from clarin.sru.queryparser import SRUQuery

    class TestSRUQuery(SRUQuery[str]):
        @property
        def query_type(self) -> str:
            return "test"

    with pytest.raises(TypeError):
        TestSRUQuery(None, None)
    with pytest.raises(TypeError):
        TestSRUQuery("abc", None)

    assert TestSRUQuery("abc", "def")

    with pytest.raises(TypeError):
        SearchTermsQuery(None, None)
    with pytest.raises(TypeError):
        SearchTermsQuery("abc", None)
    assert SearchTermsQuery("abc", "def")

    with pytest.raises(TypeError):
        CQLQuery(None, None)
    with pytest.raises(TypeError):
        CQLQuery("abc", None)
    # parameters not type checked
    assert CQLQuery("abc", "def")


def test_SearchTermsQueryParser():
    parser = SearchTermsQueryParser()
    assert not parser.supports_version(SRUVersion.VERSION_2_0)
    assert parser.supports_version(SRUVersion.VERSION_1_2)
    assert parser.query_type_definition is None

    diags = MyTestDiagsList()
    query = parser.parse_query(SRUVersion.VERSION_1_2, dict(), diags)
    assert diags.diags[0][2] == "no query passed to query parser"
    assert query is None

    diags = MyTestDiagsList()
    query = parser.parse_query(
        SRUVersion.VERSION_1_2, {SRUParam.QUERY: "test query"}, diags
    )
    assert not diags.diags
    assert query.raw_query == "test query"
    assert query.parsed_query == ["test", "query"]


def test_CQLQueryParser():
    parser = CQLQueryParser()
    assert parser.supports_version(SRUVersion.VERSION_1_1)
    assert parser.supports_version(SRUVersion.VERSION_2_0)
    assert parser.query_type_definition is None

    diags = MyTestDiagsList()
    query = parser.parse_query(SRUVersion.VERSION_2_0, dict(), diags)
    assert diags.diags[0][2] == "no query passed to query parser"
    assert query is None

    diags = MyTestDiagsList()
    query = parser.parse_query(
        SRUVersion.VERSION_2_0, {SRUParam.QUERY: "test query"}, diags
    )
    assert diags.diags[0][2] == "error parsing query"
    assert query is None

    diags = MyTestDiagsList()
    query = parser.parse_query(SRUVersion.VERSION_2_0, {SRUParam.QUERY: 1}, diags)
    assert diags.diags[0][2] == "error parsing query"
    assert query is None

    diags = MyTestDiagsList()
    query = parser.parse_query(
        SRUVersion.VERSION_2_0, {SRUParam.QUERY: '"test query"'}, diags
    )
    assert not diags.diags
    assert query.raw_query == '"test query"'
    assert isinstance(query.parsed_query.root, cql.parser.CQLSearchClause)
    assert query.parsed_query.root.term == "test query"


# ---------------------------------------------------------------------------
