import io
from typing import Dict
from typing import Union

import pytest
from lxml import etree

import clarin.sru.server.config
from clarin.sru.server.config import SRUServerConfig
from clarin.sru.server.config import SRUServerConfigKey

ConfigParamDict = Dict[Union[SRUServerConfigKey, str], str]


# ---------------------------------------------------------------------------


@pytest.fixture(scope="function")
def config_params() -> ConfigParamDict:
    # minimal required params
    return {
        SRUServerConfigKey.SRU_TRANSPORT: "http",
        SRUServerConfigKey.SRU_HOST: "localhost",
        SRUServerConfigKey.SRU_PORT: "80",
        SRUServerConfigKey.SRU_DATABASE: "test",
    }


# ---------------------------------------------------------------------------


def test_load_config_file(server_config_content: bytes):
    buf = io.BytesIO(server_config_content)

    doc = SRUServerConfig.load_config_file(buf)
    assert doc is not None
    assert isinstance(doc, etree._ElementTree)


def test_build_infos(server_config_doc: etree._ElementTree):
    database_info = SRUServerConfig._build_DatabaseInfo(server_config_doc)
    assert isinstance(database_info, clarin.sru.server.config.DatabaseInfo)

    index_info = SRUServerConfig._build_IndexInfo(server_config_doc)
    assert isinstance(index_info, clarin.sru.server.config.IndexInfo)

    schema_infos = SRUServerConfig._build_SchemaInfo(server_config_doc)
    assert isinstance(schema_infos, list)
    assert all(
        isinstance(si, clarin.sru.server.config.SchemaInfo) for si in schema_infos
    )


def test_parse(server_config_content: bytes, config_params: ConfigParamDict):
    # "simulated" file stream
    buf = io.BytesIO(server_config_content)

    config = SRUServerConfig.parse(config_params, buf)
    assert isinstance(config, SRUServerConfig)


def test_parse_file(server_config_file: str, config_params: ConfigParamDict):
    config = SRUServerConfig.parse(config_params, server_config_file)
    assert isinstance(config, SRUServerConfig)


# ---------------------------------------------------------------------------
