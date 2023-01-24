import io
import pathlib

import pytest
from lxml import etree

import clarin.sru.server.config

# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def server_config_content() -> bytes:
    return b"""
    <?xml version="1.0" encoding="UTF-8"?>
<endpoint-config xmlns="http://www.clarin.eu/sru-server/1.0/">
    <databaseInfo>
        <title xml:lang="en" primary="true">FCS 2.0 Endpoint</title>
        <title xml:lang="de">FCS 2.0 Endpunkt</title>
        <description xml:lang="en" primary="true">Search in some corpus.</description>
        <author xml:lang="en" primary="true">me</author>
    </databaseInfo>
    <indexInfo>
        <set name="fcs" identifier="http://clarin.eu/fcs/resource">
            <title xml:lang="en" primary="true">CLARIN Content Search</title>
        </set>
        <index search="true" scan="false" sort="false">
            <title xml:lang="en" primary="true">Words</title>
            <map primary="true">
                <name set="fcs">words</name>
            </map>
        </index>
    </indexInfo>
    <schemaInfo>
        <schema identifier="http://clarin.eu/fcs/resource" name="fcs" sort="false" retrieve="true">
            <title xml:lang="en" primary="true">CLARIN Content Search</title>
        </schema>
    </schemaInfo>
</endpoint-config>
    """.strip()


@pytest.fixture
def server_config_file(tmp_path: pathlib.Path, server_config_content: bytes) -> str:
    file = tmp_path / "sru-server-config.xml"
    file.write_bytes(server_config_content)
    return str(file)


@pytest.fixture
def server_config_doc(server_config_content) -> etree._ElementTree:
    buf = io.BytesIO(server_config_content)
    return clarin.sru.server.config.SRUServerConfig.load_config_file(buf)


# ---------------------------------------------------------------------------
