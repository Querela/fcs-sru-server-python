import importlib.resources
import io
import os
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

from lxml import etree

from ..constants import SRURecordPacking
from ..constants import SRURecordXmlEscaping
from ..constants import SRUVersion
from ..exception import SRUConfigException

# ---------------------------------------------------------------------------


class LegacyNamespaceMode(str, Enum):
    LOC = "loc"
    OASIS = "oasis"


@dataclass(frozen=True)
class LocalizedString:
    value: str
    lang: str
    primary: bool = False


# ---------------------------------------------------------------------------


DEFAULT_SRU_VERSION_MIN = SRUVersion.VERSION_1_1
DEFAULT_SRU_VERSION_MAX = SRUVersion.VERSION_1_2
DEFAULT_LEGACY_NAMESPACE_MODE = LegacyNamespaceMode.LOC

DEFAULT_NUMBER_OF_RECORDS = 100
DEFAULT_MAXIMUM_RECORDS = 250
DEFAULT_NUMBER_OF_TERMS = 250
DEFAULT_MAXIMUM_TERMS = 500
DEFAULT_RESPONSE_BUFFER_SIZE = 64 * 1024

CONFIG_FILE_NAMESPACE_PREFIX = "sru"
CONFIG_FILE_NAMESPACE_URI = "http://www.clarin.eu/sru-server/1.0/"
CONFIG_FILE_SCHEMA_PACKAGE = "clarin.sru.xml"
CONFIG_FILE_SCHEMA_URL = "sru-server-config.xsd"

# from: https://docs.oracle.com/javase/7/docs/api/javax/xml/XMLConstants.html
XML_NS_PREFIX = "xml"
XML_NS_URI = "http://www.w3.org/XML/1998/namespace"
NULL_NS_URI = ""
W3C_XML_SCHEMA_NS_URI = "http://www.w3.org/2001/XMLSchema"


# ---------------------------------------------------------------------------


class SRUServerConfigKey(str, Enum):
    SRU_SUPPORTED_VERSION_MIN = "eu.clarin.sru.server.sruSupportedVersionMin"
    """Parameter constant for setting the minimum supported SRU
    version for this SRU server. Must be smaller or equal to
    `SRU_SUPPORTED_VERSION_MAX`.

    Valid values: "``1.1``", "``1.2``" or " ``2.0``" (without
    quotation marks)
    """

    SRU_SUPPORTED_VERSION_MAX = "eu.clarin.sru.server.sruSupportedVersionMax"
    """Parameter constant for setting the maximum supported SRU
    version for this SRU server. Must be larger or equal to
    `SRU_SUPPORTED_VERSION_MIN`.

    Valid values: "``1.1``", "``1.2``" or "``2.0``" (without
    quotation marks)
    """

    SRU_SUPPORTED_VERSION_DEFAULT = "eu.clarin.sru.server.sruSupportedVersionDefault"
    """Parameter constant for setting the default SRU version for
    this SRU server, e.g. for an **Explain** request without explicit
    version.

    Must not me less than `SRU_SUPPORTED_VERSION_MIN` or larger than
    `SRU_SUPPORTED_VERSION_MAX`. Defaults to `SRU_SUPPORTED_VERSION_MAX`.

    Valid values: "``1.1``", "``1.2``" or "``2.0``" (without
    quotation marks)
    """

    SRU_LEGACY_NAMESPACE_MODE = "eu.clarin.sru.server.legacyNamespaceMode"
    """Parameter constant for setting the namespace URIs for SRU 1.1
    and SRU 1.2.

    Valid values: "``loc``" for Library Of Congress URI or "``oasis``"
    for OASIS URIs (without quotation marks).
    """

    SRU_TRANSPORT = "eu.clarin.sru.server.transport"
    """Parameter constant for configuring the transports for this SRU
    server.

    Valid values: "``http``", "``https``" or "``http https``"
    (without quotation marks)

    Used as part of the **Explain** response.
    """

    SRU_HOST = "eu.clarin.sru.server.host"
    """Parameter constant for configuring the host of this SRU server.

    Valid values: any fully qualified hostname,
    e.g. ``sru.example.org``.

    Used as part of the **Explain** response.
    """

    SRU_PORT = "eu.clarin.sru.server.port"
    """Parameter constant for configuring the port number of this SRU
    server.

    Valid values: number between 1 and 65535 (typically 80 or 8080)

    Used as part of the **Explain** response.
    """

    SRU_DATABASE = "eu.clarin.sru.server.database"
    """Parameter constant for configuring the database of this SRU
    server. This is usually the path component of the SRU servers URI.

    Valid values: typically the path component if the SRU server URI.

    Used as part of the **Explain** response.
    """

    SRU_NUMBER_OF_RECORDS = "eu.clarin.sru.server.numberOfRecords"
    """Parameter constant for configuring the **default** number of
    records the SRU server will provide in the response to a
    **searchRetrieve** request if the client does not provide this
    value.

    Valid values: a integer greater than 0 (default value is 100)
    """

    SRU_MAXIMUM_RECORDS = "eu.clarin.sru.server.maximumRecords"
    """Parameter constant for configuring the **maximum** number of
    records the SRU server will support in the response to a
    **searchRetrieve** request. If a client requests more records,
    the number will be limited to this value.

    Valid values: a integer greater than 0 (default value is 250)
    """

    SRU_NUMBER_OF_TERMS = "eu.clarin.sru.server.numberOfTerms"
    """Parameter constant for configuring the **default** number of
    terms the SRU server will provide in the response to a **scan**
    request if the client does not provide this value.

    Valid values: a integer greater than 0 (default value is 250)
    """

    SRU_MAXIMUM_TERMS = "eu.clarin.sru.server.maximumTerms"
    """Parameter constant for configuring the **maximum** number of
    terms the SRU server will support in the response to a **scan**
    request. If a client requests more records, the number will be
    limited to this value.

    Valid values: a integer greater than 0 (default value is 500)
    """

    SRU_ECHO_REQUESTS = "eu.clarin.sru.server.echoRequests"
    """Parameter constant for configuring, if the SRU server will
    echo the request.

    Valid values: ``true`` or ``false``
    """

    SRU_INDENT_RESPONSE = "eu.clarin.sru.server.indentResponse"
    """Parameter constant for configuring, if the SRU server
    pretty-print the XML response. Setting this parameter can be
    useful for manual debugging of the XML response, however it is
    **not recommended** for production setups.

    Valid values: any integer greater or equal to ``-1`` (default)
    and less or equal to ``8``
    """

    SRU_ALLOW_OVERRIDE_MAXIMUM_RECORDS = (
        "eu.clarin.sru.server.allowOverrideMaximumRecords"
    )
    """Parameter constant for configuring, if the SRU server will
    allow the client to override the maximum number of records the
    server supports. This parameter is solely intended for debugging
    and setting it to ``true`` is **strongly** discouraged for
    production setups.

    Valid values: ``true`` or ``false`` (default)
    """

    SRU_ALLOW_OVERRIDE_MAXIMUM_TERMS = "eu.clarin.sru.server.allowOverrideMaximumTerms"
    """Parameter constant for configuring, if the SRU server will
    allow the client to override the maximum number of terms the
    server supports. This parameter is solely intended for debugging
    and setting it to ``true`` it is **strongly** discouraged for
    production setups.

    Valid values: ``true`` or ``false`` (default)
    """

    SRU_ALLOW_OVERRIDE_INDENT_RESPONSE = (
        "eu.clarin.sru.server.allowOverrideIndentResponse"
    )
    """Parameter constant for configuring, if the SRU server will
    allow the client to override the pretty-printing setting of the
    server. This parameter is solely intended for debugging and
    setting it to ``true`` it is **strongly** discouraged for
    production setups.

    Valid values: ``true`` or ``false`` (default)
    """

    # TODO: docstring; needed?
    SRU_RESPONSE_BUFFER_SIZE = "eu.clarin.sru.server.responseBufferSize"
    """Parameter constant for configuring the size of response buffer.
    The Servlet will buffer up to this amount of data before sending
    a response to the client. This value specifies the size of the
    buffer in bytes.

    Valid values: any positive integer (default 65536)
    """


# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DatabaseInfo:
    title: Optional[List[LocalizedString]] = None
    description: Optional[List[LocalizedString]] = None
    author: Optional[List[LocalizedString]] = None
    extent: Optional[List[LocalizedString]] = None
    history: Optional[List[LocalizedString]] = None
    langUsage: Optional[List[LocalizedString]] = None
    restrictions: Optional[List[LocalizedString]] = None
    subjects: Optional[List[LocalizedString]] = None
    links: Optional[List[LocalizedString]] = None
    implementation: Optional[List[LocalizedString]] = None


@dataclass(frozen=True)
class SchemaInfo:
    identifier: str
    name: str
    location: str
    sort: bool
    retrieve: bool
    title: Optional[List[LocalizedString]] = None


@dataclass(frozen=True)
class IndexInfo:
    @dataclass(frozen=True)
    class Set:
        identifier: str
        name: str
        title: Optional[List[LocalizedString]] = None

    @dataclass(frozen=True)
    class Index:
        @dataclass(frozen=True)
        class Map:
            primary: bool
            set: str
            name: str

        can_search: bool
        can_scan: bool
        can_sort: bool
        maps: Optional[List[Map]] = None
        title: Optional[List[LocalizedString]] = None

    sets: Optional[List[Set]] = None
    indexes: Optional[List[Index]] = None


# ---------------------------------------------------------------------------


@dataclass
class SRUServerConfig:
    """SRU server configuration.

    The XML configuration file must validate against the
    ``sru-server-config.xsd`` W3C schema bundled with the package and
    need to have the ``http://www.clarin.eu/sru-server/1.0/`` XML
    namespace.
    """

    min_version: SRUVersion
    max_version: SRUVersion
    default_version: SRUVersion
    legacy_namespace_mode: LegacyNamespaceMode
    transport: str
    host: str
    port: int
    database: str
    number_of_records: int
    maximum_records: int
    number_of_terms: int
    maximum_terms: int
    echo_requests: bool
    indent_response: int
    response_buffer_size: int
    allow_override_maximum_records: bool
    allow_override_maximum_terms: bool
    allow_override_indent_response: bool
    base_url: str = field(init=False)
    database_info: DatabaseInfo
    index_info: IndexInfo
    schema_info: Optional[List[SchemaInfo]] = None

    def __post_init__(self):
        self.base_url = f"{self.host}{':' + str(self.port) if self.port != 80 else ''}/{self.database}"
        if not self.schema_info:
            self.schema_info = None

    @property
    def default_record_xml_escaping(self) -> SRURecordXmlEscaping:
        return SRURecordXmlEscaping.XML

    @property
    def default_record_packing(self) -> SRURecordPacking:
        return SRURecordPacking.PACKED

    def get_record_schema_identifier(self, record_schema_name: str) -> Optional[str]:
        if record_schema_name is not None:
            if self.schema_info:
                for schema in self.schema_info:
                    if schema.name == record_schema_name:
                        return schema.identifier
        return None

    def get_record_schema_name(self, schema_identifier: str) -> Optional[str]:
        if schema_identifier is not None:
            if self.schema_info:
                for schema in self.schema_info:
                    if schema.identifier == schema_identifier:
                        return schema.name
        return None

    def find_schema_info(self, value: str) -> Optional[SchemaInfo]:
        if value is not None:
            if self.schema_info:
                for schema in self.schema_info:
                    if schema.identifier == value or schema.name == value:
                        return schema
        return None

    @staticmethod
    def find_set_by_name(
        sets: List[IndexInfo.Set], name: str
    ) -> Optional[IndexInfo.Set]:
        for set in sets:
            if set.name == name:
                return set
        return None

    @staticmethod
    def fromparams(
        params: Dict[str, str],
        database_info: DatabaseInfo,
        index_info: Optional[IndexInfo] = None,
        schema_info: Optional[List[SchemaInfo]] = None,
    ) -> "SRUServerConfig":
        """Creates an SRU configuration object with default values
        and overrides from **params**.

        Args:
            params: additional settings
            database_info: optinal `DatabaseInfo`
            index_info: optinal `IndexInfo`
            schema_info: optional list `SchemaInfo`

        Returns:
            SRUServerConfig: a initialized `SRUEndpointConfig` instance

        Raises:
            `TypeError`: if **params** is None
            `SRUConfigException`: if an error occurred
        """
        if params is None:
            raise TypeError("params is None")

        # NOTE: maybe some more validation? but everything could possibly be empty
        if database_info is None:
            database_info = DatabaseInfo()
        if index_info is None:
            index_info = IndexInfo()

        try:
            # fetch parameters more parameters (usually passed from
            # environment)

            min_version = SRUServerConfig.parse_version(
                params,
                SRUServerConfigKey.SRU_SUPPORTED_VERSION_MIN,
                False,
                DEFAULT_SRU_VERSION_MIN,
            )
            max_version = SRUServerConfig.parse_version(
                params,
                SRUServerConfigKey.SRU_SUPPORTED_VERSION_MAX,
                False,
                DEFAULT_SRU_VERSION_MAX,
            )
            if max_version.version_number < min_version.version_number:
                raise SRUConfigException(
                    f"parameter value '{SRUServerConfigKey.SRU_SUPPORTED_VERSION_MAX}'"
                    f" ({max_version.version_string}) must be equal or larger than value"
                    f"of parameter '{SRUServerConfigKey.SRU_SUPPORTED_VERSION_MIN}'"
                    f" ({min_version.version_string})"
                )

            default_version = SRUServerConfig.parse_version(
                params,
                SRUServerConfigKey.SRU_SUPPORTED_VERSION_DEFAULT,
                False,
                max_version,
            )
            if (
                default_version.version_number < min_version.version_number
                or default_version.version_number > max_version.version_number
            ):
                raise SRUConfigException(
                    f"parameter value '{SRUServerConfigKey.SRU_SUPPORTED_VERSION_DEFAULT}'"
                    f" ({default_version.version_string}) must be between value of parameter"
                    f" '{SRUServerConfigKey.SRU_SUPPORTED_VERSION_MIN}'"
                    f" ({min_version.version_string}) and"
                    f" '{SRUServerConfigKey.SRU_SUPPORTED_VERSION_MAX}'"
                    f" ({max_version.version_string})"
                )

            legacy_namespace_mode = DEFAULT_LEGACY_NAMESPACE_MODE
            mode = params.get(SRUServerConfigKey.SRU_LEGACY_NAMESPACE_MODE)
            if mode is not None and isinstance(mode, str) and not mode.strip():
                if LegacyNamespaceMode.LOC.value == mode:
                    legacy_namespace_mode = LegacyNamespaceMode.LOC
                elif LegacyNamespaceMode.OASIS.value == mode:
                    legacy_namespace_mode = LegacyNamespaceMode.OASIS
                else:
                    raise SRUConfigException(
                        f"invalid value for parameter {SRUServerConfigKey.SRU_LEGACY_NAMESPACE_MODE}: {mode}"
                    )

            transport = params.get(SRUServerConfigKey.SRU_TRANSPORT)
            if (
                transport is None
                or not isinstance(transport, str)
                or not transport.strip()
            ):
                raise SRUConfigException(
                    f"parameter {SRUServerConfigKey.SRU_TRANSPORT} is mandatory"
                )
            transport_parts = transport.strip().lower().split()
            for tr in transport_parts:
                if tr not in ("http", "https"):
                    raise SRUConfigException(f"unsupported transport {tr}")
            transport = " ".join(transport_parts)

            host = params.get(SRUServerConfigKey.SRU_HOST)
            if host is None or not isinstance(host, str) or not host.strip():
                raise SRUConfigException(
                    f"parameter {SRUServerConfigKey.SRU_HOST} is mandatory"
                )

            port = SRUServerConfig.parse_int(
                params, SRUServerConfigKey.SRU_PORT, True, -1, 1, 65535
            )

            database = params.get(SRUServerConfigKey.SRU_DATABASE)
            if (
                database is None
                or not isinstance(database, str)
                or not database.strip()
            ):
                raise SRUConfigException(
                    f"parameter {SRUServerConfigKey.SRU_DATABASE} is mandatory"
                )
            database = database.lstrip("/")

            number_of_records = SRUServerConfig.parse_int(
                params,
                SRUServerConfigKey.SRU_NUMBER_OF_RECORDS,
                False,
                DEFAULT_NUMBER_OF_RECORDS,
                1,
                -1,
            )

            maximum_records = SRUServerConfig.parse_int(
                params,
                SRUServerConfigKey.SRU_MAXIMUM_RECORDS,
                False,
                DEFAULT_MAXIMUM_RECORDS,
                number_of_records,
                -1,
            )

            number_of_terms = SRUServerConfig.parse_int(
                params,
                SRUServerConfigKey.SRU_NUMBER_OF_TERMS,
                False,
                DEFAULT_NUMBER_OF_TERMS,
                0,
                -1,
            )

            maximum_terms = SRUServerConfig.parse_int(
                params,
                SRUServerConfigKey.SRU_MAXIMUM_TERMS,
                False,
                DEFAULT_MAXIMUM_TERMS,
                number_of_terms,
                -1,
            )

            echo_requests = SRUServerConfig.parse_bool(
                params, SRUServerConfigKey.SRU_ECHO_REQUESTS, False, True
            )

            indent_response = SRUServerConfig.parse_int(
                params, SRUServerConfigKey.SRU_INDENT_RESPONSE, False, -1, -1, 8
            )

            allow_override_maximum_records = SRUServerConfig.parse_bool(
                params,
                SRUServerConfigKey.SRU_ALLOW_OVERRIDE_MAXIMUM_RECORDS,
                False,
                False,
            )

            allow_override_maximum_terms = SRUServerConfig.parse_bool(
                params,
                SRUServerConfigKey.SRU_ALLOW_OVERRIDE_MAXIMUM_TERMS,
                False,
                False,
            )

            allow_override_indent_response = SRUServerConfig.parse_bool(
                params,
                SRUServerConfigKey.SRU_ALLOW_OVERRIDE_INDENT_RESPONSE,
                False,
                False,
            )

            response_buffer_size = SRUServerConfig.parse_int(
                params,
                SRUServerConfigKey.SRU_RESPONSE_BUFFER_SIZE,
                False,
                DEFAULT_RESPONSE_BUFFER_SIZE,
                0,
                -1,
            )

            return SRUServerConfig(
                min_version=min_version,
                max_version=max_version,
                default_version=default_version,
                legacy_namespace_mode=legacy_namespace_mode,
                transport=transport,
                host=host,
                port=port,
                database=database,
                number_of_records=number_of_records,
                maximum_records=maximum_records,
                number_of_terms=number_of_terms,
                maximum_terms=maximum_terms,
                echo_requests=echo_requests,
                indent_response=indent_response,
                response_buffer_size=response_buffer_size,
                allow_override_maximum_records=allow_override_maximum_records,
                allow_override_maximum_terms=allow_override_maximum_terms,
                allow_override_indent_response=allow_override_indent_response,
                database_info=database_info,
                index_info=index_info,
                schema_info=schema_info,
            )
        except Exception as ex:
            raise SRUConfigException("error building configuration object") from ex

    @staticmethod
    def parse(
        params: Dict[str, str], config_file: Union[io.BytesIO, os.PathLike, str]
    ) -> "SRUServerConfig":
        """Parse a SRU server XML configuration file and create an
        configuration object from it.

        Args:
            params: additional settings
            config_file: an ``URL`` pointing to the XML configuration
                file

        Returns:
            SRUServerConfig: a initialized `SRUEndpointConfig` instance

        Raises:
            `TypeError`: if **params** or **configFile** is None
            `SRUConfigException`: if an error occurred
        """
        if params is None:
            raise TypeError("params is None")
        if config_file is None:
            raise TypeError("config_file is None")

        try:
            doc = SRUServerConfig.load_config_file(config_file)

            database_info = SRUServerConfig._build_DatabaseInfo(doc)
            index_info = SRUServerConfig._build_IndexInfo(doc)
            schema_info = SRUServerConfig._build_SchemaInfo(doc)
        except Exception as ex:
            raise SRUConfigException("error reading configuration file") from ex

        return SRUServerConfig.fromparams(
            params,
            database_info=database_info,
            index_info=index_info,
            schema_info=schema_info,
        )

    @staticmethod
    def load_config_file(
        config_file: Union[io.BytesIO, os.PathLike, str]
    ) -> etree._ElementTree:
        # load validation schema
        if not importlib.resources.is_resource(
            CONFIG_FILE_SCHEMA_PACKAGE, CONFIG_FILE_SCHEMA_URL
        ):
            raise SRUConfigException(
                f"cannot open {CONFIG_FILE_SCHEMA_URL} in {CONFIG_FILE_SCHEMA_PACKAGE}"
            )

        with importlib.resources.open_text(
            CONFIG_FILE_SCHEMA_PACKAGE,
            CONFIG_FILE_SCHEMA_URL,
            encoding="utf-8",
            errors="strict",
        ) as fp:
            config_schema_doc = etree.parse(fp)

        config_schema = etree.XMLSchema(config_schema_doc)

        parser = etree.XMLParser(ns_clean=False, remove_comments=True)

        # load config xml
        config_doc: etree._ElementTree = etree.parse(config_file, parser)
        docinfo: etree.DocInfo = config_doc.docinfo
        docinfo.public_id = CONFIG_FILE_NAMESPACE_URI
        docinfo.system_url = CONFIG_FILE_NAMESPACE_URI

        # validate
        config_schema.assertValid(config_doc)

        return config_doc

    @staticmethod
    def parse_version(
        params: Dict[str, str], name: str, mandatory: bool, default: SRUVersion
    ) -> SRUVersion:
        value = params.get(name)
        if value is None or not isinstance(value, str) or not value.strip():
            if mandatory:
                raise SRUConfigException(f"parameter '{name}' is mandatory")
            else:
                return default

        if "1.1" == value:
            return SRUVersion.VERSION_1_1
        if "1.2" == value:
            return SRUVersion.VERSION_1_2
        if "2.0" == value:
            return SRUVersion.VERSION_2_0

        raise SRUConfigException(f"invalid value for parameter '{name}': value")

    @staticmethod
    def parse_int(
        params: Dict[str, str],
        name: str,
        mandatory: bool,
        default: int,
        min: int,
        max: int,
    ) -> int:
        value = params.get(name)
        if value is None or not isinstance(value, str) or not value.strip().isdigit():
            if mandatory:
                raise SRUConfigException(f"parameter '{name}' is mandatory")
            else:
                return default
        try:
            num = int(value)

            # sanity checks
            if min != -1 and max != -1:
                if num < min or num > max:
                    raise SRUConfigException(
                        f"parameter '{name}' must be between {min} and {max}: {num}"
                    )
            else:
                if min != -1 and num < min:
                    raise SRUConfigException(
                        f"parameter '{name}' must be larger than {min}: {num}"
                    )
                if max != -1 and num > max:
                    raise SRUConfigException(
                        f"parameter '{name}' must be smaller than {max}: {num}"
                    )

            return num
        except ValueError as ex:
            import sys

            raise SRUConfigException(
                f"parameter '{name}' must be nummerical and less than {sys.maxsize}: {value}"
            ) from ex

    @staticmethod
    def parse_bool(
        params: Dict[str, str], name: str, mandatory: bool, default: bool
    ) -> bool:
        value = params.get(name)
        if (
            value is None
            or not isinstance(value, str)
            or value.strip().lower() not in ("true", "false")
        ):
            if mandatory:
                raise SRUConfigException(f"parameter '{name}' is mandatory")
            else:
                return default
        return value.strip().lower() == "true"

    @staticmethod
    def _build_DatabaseInfo(doc: etree._ElementTree) -> DatabaseInfo:
        title = SRUServerConfig._build_list(doc, "//sru:databaseInfo/sru:title")
        description = SRUServerConfig._build_list(
            doc, "//sru:databaseInfo/sru:description"
        )
        author = SRUServerConfig._build_list(doc, "//sru:databaseInfo/sru:author")
        extent = SRUServerConfig._build_list(doc, "//sru:databaseInfo/sru:extent")
        history = SRUServerConfig._build_list(doc, "//sru:databaseInfo/sru:history")
        langUsage = SRUServerConfig._build_list(doc, "//sru:databaseInfo/sru:langUsage")
        restrictions = SRUServerConfig._build_list(
            doc, "//sru:databaseInfo/sru:restrictions"
        )
        subjects = SRUServerConfig._build_list(doc, "//sru:databaseInfo/sru:subjects")
        links = SRUServerConfig._build_list(doc, "//sru:databaseInfo/sru:links")
        implementation = SRUServerConfig._build_list(
            doc, "//sru:databaseInfo/sru:implementation"
        )

        return DatabaseInfo(
            title=title,
            description=description,
            author=author,
            extent=extent,
            history=history,
            langUsage=langUsage,
            restrictions=restrictions,
            subjects=subjects,
            links=links,
            implementation=implementation,
        )

    @staticmethod
    def _build_IndexInfo(doc: etree._ElementTree) -> IndexInfo:
        sets: Optional[List[IndexInfo.Set]] = None
        indexes: Optional[List[IndexInfo.Index]] = None

        nodes = doc.xpath(
            "//sru:indexInfo/sru:set",
            namespaces={CONFIG_FILE_NAMESPACE_PREFIX: CONFIG_FILE_NAMESPACE_URI},
        )
        if nodes:
            sets = list()
            for node in nodes:
                identifier = node.get("identifier")
                name = node.get("name")
                if not identifier or not identifier.strip():
                    raise SRUConfigException(
                        "attribute 'identifier' may on element '/indexInfo/set' may not be empty"
                    )
                if not name or not name.strip():
                    raise SRUConfigException(
                        "attribute 'name' may on element '/indexInfo/set' may not be empty"
                    )
                title = SRUServerConfig._from_node_list(
                    node.findall("title", namespaces=node.nsmap)
                )

                sets.append(
                    IndexInfo.Set(identifier=identifier, name=name, title=title)
                )

        nodes = doc.xpath(
            "//sru:indexInfo/sru:index",
            namespaces={CONFIG_FILE_NAMESPACE_PREFIX: CONFIG_FILE_NAMESPACE_URI},
        )
        if nodes:
            indexes = list()
            for node in nodes:
                title = SRUServerConfig._from_node_list(
                    node.findall("title", namespaces=node.nsmap)
                )
                can_search = SRUServerConfig._get_bool_attrib(node, "search", False)
                can_scan = SRUServerConfig._get_bool_attrib(node, "scan", False)
                can_sort = SRUServerConfig._get_bool_attrib(node, "sort", False)

                maps: Optional[List[IndexInfo.Index.Map]] = None
                nodes_map = node.findall("map", namespaces=node.nsmap)
                if nodes_map:
                    maps = list()
                    found_primary = False
                    for node_map in nodes_map:
                        primary = SRUServerConfig._get_bool_attrib(
                            node_map, "primary", False
                        )
                        if primary:
                            if found_primary:
                                raise SRUConfigException(
                                    "only one map may be 'primary' in index"
                                )
                            found_primary = True

                        node_name = node_map.find("name", namespaces=node_map.nsmap)
                        if node_name is not None:
                            map_set = node_name.get("set")
                            map_name = node_name.text
                            if not map_set or not map_set.strip():
                                raise SRUConfigException(
                                    "attribute 'set' on element '/indexInfo/index/map/name' may not be empty"
                                )
                            if map_name is None or not map_name.strip():
                                raise SRUConfigException(
                                    "element '/indexInfo/index/map/name' may not be empty"
                                )

                            # clarin/java code would allow setting None to both set/name
                            # (if there was no schema validation)
                            # so we can assume that when we find a map entry, a name entry
                            # exists with the correct attribute
                            # so we skip adding the map on identation lower --> mypy checks ...
                            maps.append(
                                IndexInfo.Index.Map(
                                    primary=primary, set=map_set, name=map_name
                                )
                            )

                indexes.append(
                    IndexInfo.Index(
                        title=title,
                        can_search=can_search,
                        can_scan=can_scan,
                        can_sort=can_sort,
                        maps=maps,
                    )
                )

            # sanity check (/index/map/name/@set exists in any set/@name)
            if sets:
                for index in indexes:
                    if not index.maps:
                        continue
                    for map in index.maps:
                        if not SRUServerConfig.find_set_by_name(sets, map.set):
                            raise SRUConfigException(
                                f"/index/map/name refers to nonexitsing set ({map.set})"
                            )

        return IndexInfo(sets, indexes)

    @staticmethod
    def _build_SchemaInfo(doc: etree._ElementTree) -> Optional[List[SchemaInfo]]:
        nodes = doc.xpath(
            "//sru:schemaInfo/sru:schema",
            namespaces={CONFIG_FILE_NAMESPACE_PREFIX: CONFIG_FILE_NAMESPACE_URI},
        )
        if not nodes:
            return None

        schemaInfos: List[SchemaInfo] = list()
        for node in nodes:
            identifier = node.get("identifier")
            name = node.get("name")
            location = node.get("location")
            if location is not None and not location.strip():
                location = None
            sort = SRUServerConfig._get_bool_attrib(node, "sort", False)
            retrieve = SRUServerConfig._get_bool_attrib(node, "retrieve", False)
            title = SRUServerConfig._from_node_list(
                node.findall("title", namespaces=node.nsmap)
            )

            schemaInfos.append(
                SchemaInfo(
                    identifier=identifier,
                    name=name,
                    location=location,
                    sort=sort,
                    retrieve=retrieve,
                    title=title,
                )
            )

        return schemaInfos

    @staticmethod
    def _build_list(
        doc: etree._ElementTree, xpath: str
    ) -> Optional[List[LocalizedString]]:
        return SRUServerConfig._from_node_list(
            doc.xpath(
                xpath,
                namespaces={CONFIG_FILE_NAMESPACE_PREFIX: CONFIG_FILE_NAMESPACE_URI},
            )
        )

    @staticmethod
    def _from_node_list(nodes: List[etree._Element]) -> Optional[List[LocalizedString]]:
        if nodes is None or not len(nodes):
            return None

        strings = list()
        found_primary = False
        for node in nodes:
            primary = SRUServerConfig._get_bool_attrib(node, "primary", False)
            if primary:
                if found_primary:
                    raise SRUConfigException(
                        "list may only contain one element as primary"
                    )
                found_primary = True

            strings.append(
                LocalizedString(
                    value=node.text,
                    lang=node.get(etree.QName(XML_NS_URI, "lang")),
                    primary=primary,
                )
            )

        return strings

    @staticmethod
    def _get_bool_attrib(node: etree._Element, local_name: str, default: bool) -> bool:
        value = node.get(local_name)
        if (
            value is None
            or not value.strip()
            or value.strip().lower() not in ("true", "false")
        ):
            return default
        return value.strip().lower() == "true"


# ---------------------------------------------------------------------------
