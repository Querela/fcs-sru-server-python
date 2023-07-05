from abc import ABC
from abc import ABCMeta
from abc import abstractmethod
from enum import Enum
from typing import Optional

from ..constants import SRUResultCountPrecision
from ..diagnostic import SRUDiagnostic
from ..diagnostic import SRUDiagnosticList
from ..xml.writer import SRUXMLStreamWriter

# ---------------------------------------------------------------------------


class SRUAbstractResult(metaclass=ABCMeta):
    """Base class for SRU responses."""

    def __init__(self, diagnostics: SRUDiagnosticList) -> None:
        if diagnostics is None:
            raise TypeError("Implementation error: diagnostics must not be None!")
        self.diagnostics = diagnostics

    def add_diagnostic(
        self, uri: str, details: Optional[str] = None, message: Optional[str] = None
    ) -> None:
        """Add a non surrogate diagnostic to the response.

        Args:
            uri: the diagnostic's identifying URI
            details: supplementary information available, often
                in a format specified by the diagnostic or ``None``
            message: human readable message to display to the
                end user or ``None``
        """
        self.diagnostics.add_diagnostic(uri, details, message)

    @property
    def has_extra_response_data(self) -> bool:
        """Check, if extra response data should be serialized for
        this request. Default implementation is provided for convince
        and always returns ``False``.

        Returns:
            bool: ``True`` if extra response data should be serialized
        """
        return False

    def write_extra_response_data(self, writer: SRUXMLStreamWriter) -> None:
        """Serialize extra response data for this request. A no-op
        default implementation is provided for convince.

        Args:
            writer: Writer to serialize extra response data
        """

    def close(self) -> None:
        """Release this result and free any associated resources.

        This method **must not** throw any exceptions.

        Calling the method `close` on a result object that
        is already closed is a no-op.
        """


# ---------------------------------------------------------------------------


class SRUExplainResult(ABC, SRUAbstractResult):
    """A result set of an ``explain`` operation. A database
    implementation may use it implement extensions to the SRU
    protocol, i.e. providing extraResponseData.

    This class needs to be implemented for the target data source.

    See also:
        SRU Explain Operation: http://www.loc.gov/standards/sru/explain/
    """


# ---------------------------------------------------------------------------


class SRUScanResultSet(ABC, SRUAbstractResult):
    """A result set of a ``scan`` operation. It is used to iterate
    over the term set and provides a method to serialize the terms.

    A `SRUScanResultSet` object maintains a cursor pointing to its
    current term. Initially the cursor is positioned before the first
    term. The `next` method moves the cursor to the next term, and
    because it returns ``False`` when there are no more terms in the
    `SRUScanResultSet` object, it can be used in a `while` loop to
    iterate through the term set.

    This class needs to be implemented for the target search engine.

    See also:
        SRU Scan Operation: http://www.loc.gov/standards/sru/companionSpecs/scan.html
    """

    class WhereInList(str, Enum):
        """A flag to indicate the position of the term within the
        complete term list."""

        FIRST = "first"
        """The first term (**first**)"""

        LAST = "last"
        """The last term (**last**)"""

        ONLY = "only"
        """The only term (**only**)"""

        INNER = "inner"
        """Any other term (**inner**)"""

    @abstractmethod
    def next_term(self) -> bool:
        """Moves the cursor forward one term from its current
        position. A result set cursor is initially positioned before
        the first record; the first call to the method `next` makes
        the first term the current term; the second call makes the
        second term the current term, and so on.

        When a call to the `next` method returns ``False``, the
        cursor is positioned after the last term.

        Returns:
            bool: ``True`` if the new current term is valid;
                ``False`` if there are no more terms

        Raises:
            `SRUException`: if an error occurred while fetching the
                next term
        """

    @abstractmethod
    def get_value(self) -> str:
        """Get the current term exactly as it appears in the index.

        Returns:
            str: current term
        """

    @abstractmethod
    def get_number_of_records(self) -> int:
        """Get the number of records for the current term which would
        be matched if the index in the request's `scanClause` was
        searched with the term in the `value` field.

        Returns:
            int: a non-negative number of records or ``-1``, if the
                number is unknown.
        """

    @abstractmethod
    def get_display_term(self) -> Optional[str]:
        """Get the string for the current term to display to the end
        user in place of the term itself.

        Returns:
            str: display string or ``None``
        """

    @abstractmethod
    def get_WhereInList(self) -> Optional[WhereInList]:
        """Get the flag to indicate the position of the term within
        the complete term list.

        Returns:
            `WhereInList`: position within term list or ``None``
        """

    def has_extra_term_data(self) -> bool:
        """Check, if extra term data should be serialized for the
        current term. A default implementation is provided for
        convince and always returns ``False``.

        Returns:
            bool: ``True`` if the term has extra term data

        Raises:
            `StopIteration`: term set is already advanced past all
                past terms

        See also:
            `write_extra_term_data`
        """
        return False

    @abstractmethod
    def write_extra_term_data(self, writer: SRUXMLStreamWriter):
        """Serialize extra term data for the current term. A no-op
        default implementation is provided for convince.

        Args:
            writer: Writer to serialize extra term data for current
                term

        Raises:
            `StopIteration`: term set already advanced past all terms
        """


# ---------------------------------------------------------------------------


class SRUSearchResultSet(ABC, SRUAbstractResult):
    """A result set of a ``searchRetrieve`` operation. It it used to
    iterate over the result set and provides a method to serialize
    the record in the requested format.

    A `SRUSearchResultSet` object maintains a cursor pointing to its
    current record. Initially the cursor is positioned before the
    first record. The `next` method moves the cursor to the next
    record, and because it returns ``False`` when there are no more
    records in the `SRUSearchResultSet` object, it can be used in a
    `while` loop to iterate through the result set.

    This class needs to be implemented for the target search engine.

    See also:
        * SRU Search Retrieve Operation: http://www.loc.gov/standards/sru/
        * SRU 1.1 SR: http://www.loc.gov/standards/sru/sru-1-1.html
        * SRU 1.2 SR: http://www.loc.gov/standards/sru/sru-1-2.html
        * SRU 2.0 SR: http://www.loc.gov/standards/sru/sru-2-0.html
        * Differences SRU 2.0 to SRU 1.2: http://www.loc.gov/standards/sru/differences.html
    """

    @abstractmethod
    def get_total_record_count(self) -> int:
        """The number of records matched by the query. If the query
        fails this must be ``0``. If the search engine cannot
        determine the total number of matched by a query, it must
        return ``-1``.

        Returns:
            int: the total number of results or ``0`` if the query
                failed or ``-1`` if the search engine cannot
                determine the total number of results
        """

    @abstractmethod
    def get_record_count(self) -> int:
        """The number of records matched by the query but at most as
        the number of records requested to be returned
        (``maximumRecords`` parameter). If the query fails this must
        be ``0``.

        Returns:
            int: the number of results or ``0`` if the query failed
        """

    def get_resultSet_id(self) -> Optional[str]:
        """The result set id of this result. The default
        implementation returns ``None``.

        Returns:
            str: the result set id or ``None`` if not applicable for
                this result
        """
        return None

    def get_resultSet_TTL(self) -> int:
        """The result set time to live. In SRU 2.0 it will be
        serialized as ``<resultSetTTL>`` element; in SRU 1.2 as
        ``<resultSetIdleTime>`` element.The default implementation
        returns ``-1``.

        Returns:
            int: the result set time to live or ``-1`` if not
                applicable for this result
        """
        return -1

    def get_result_count_precision(self) -> Optional[SRUResultCountPrecision]:
        """(SRU 2.0) Indicate the accuracy of the result count
        reported by total number of records that matched the query.
        Default implementation returns ``None``.

        Returns:
            Optional[SRUResultCountPrecision]: the result count
                precision or ``None`` if not applicable for this
                result

        See also:
            `SRUResultCountPrecision`
        """
        return None

    @abstractmethod
    def get_record_schema_identifier(self) -> str:
        """The record schema identifier in which the records are
        returned (``recordSchema`` parameter).

        Returns:
            str: the record schema identifier
        """

    @abstractmethod
    def next_record(self) -> bool:
        """Moves the cursor forward one record from its current
        position. A `SRUSearchResultSet` cursor is initially
        positioned before the first record; the first call to the
        method `next` makes the first record the current record; the
        second call makes the second record the current record, and
        so on.

        When a call to the `next` method returns ``False``, the
        cursor is positioned after the last record.

        Returns:
            bool: ``True`` if the new current record is valid;
                ``False`` if there are no more records

        Raises:
            `SRUException`: if an error occurred while fetching the
                next record
        """

    @abstractmethod
    def get_record_identifier(self) -> Optional[str]:
        """An identifier for the current record by which it can
        unambiguously be retrieved in a subsequent operation.

        Returns:
            str: identifier for the record or ``None`` of none is
                available

        Raises:
            `StopIteration`: result set is past all records
        """

    def get_surrogate_diagnostic(self) -> Optional[SRUDiagnostic]:
        """Get surrogate diagnostic for current record. If this
        method returns a diagnostic, the `write_record method will
        not be called. The default implementation returns ``None``.

        Returns:
            Optional[SRUDiagnostic]: a surrogate diagnostic or
                ``None``
        """
        return None

    @abstractmethod
    def write_record(self, writer: SRUXMLStreamWriter) -> None:
        """Serialize the current record in the requested format.

        Args:
            writer: Writer to serialize current record

        Raises:
            `StopIteration`: result set is past all records
        """

    @property
    def has_extra_record_data(self) -> bool:
        """Check, if extra record data should be serialized for the
        current record. The default implementation returns ``False``.

        Returns:
            bool: ``True`` if the record has extra record data

        Raises:
            `StopIteration`: result set is past all records

        See also:
            `write_extra_record_data`
        """
        return False

    def write_extra_record_data(self, writer: SRUXMLStreamWriter) -> None:
        """Serialize extra record data for the current record. A
        no-op default implementation is provided for convince.

        Args:
            writer: Writer to serialize extra record data for current
                record

        Raises:
            `StopIteration`: result set past already advanced past
                all records
        """
        pass


# ---------------------------------------------------------------------------
