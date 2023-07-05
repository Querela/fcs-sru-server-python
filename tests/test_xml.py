import io
from xml.sax.saxutils import XMLGenerator

import cql
import pytest
from lxml import etree

from clarin.sru.constants import SRURecordXmlEscaping
from clarin.sru.xml.writer import SRUXMLStreamWriter

# ---------------------------------------------------------------------------


def test_streamwriter():
    buf = io.StringIO()

    writer = SRUXMLStreamWriter(buf, SRURecordXmlEscaping.STRING, indent=2)
    # writer = XMLGenerator(buf, "utf-8")

    writer.startDocument()
    writer.startElement("root", dict())
    writer.startElement("ele1", dict())
    writer.endElement("ele1")
    writer.endElement("root")
    writer.endDocument()

    content = buf.getvalue()

    assert (
        content
        == """<?xml version="1.0" encoding="utf-8"?>\n<root>\n  <ele1></ele1>\n</root>"""
    )


def test_streamwriter_xcql():
    buf = io.StringIO()

    writer = SRUXMLStreamWriter(buf, SRURecordXmlEscaping.STRING, indent=2)

    query = cql.parse("stuff")
    query.setServerDefaults()

    writer.startDocument()
    writer.startElement("root", dict())
    writer.startElement("ele1", dict())
    writer.endElement("ele1")
    writer.startElement("xQuery", dict())
    writer.writeXCQL(query, False)
    writer.endElement("xQuery")
    writer.endElement("root")
    writer.endDocument()

    content = buf.getvalue()

    assert (
        content
        == """<?xml version="1.0" encoding="utf-8"?>\n<root>\n  <ele1></ele1>\n"""
        """  <xQuery>\n    <index>cql.serverChoice</index>\n    <relation>\n"""
        """      <value>=</value>\n    </relation>\n    <term>stuff</term>\n"""
        """  </xQuery>\n</root>"""
    )


def test_streamwriter_ns():
    buf = io.StringIO()

    writer = SRUXMLStreamWriter(buf, SRURecordXmlEscaping.STRING, indent=2)
    # writer = XMLGenerator(buf, "utf-8")

    writer.startDocument()
    writer.startElement("root", dict())
    writer.startPrefixMapping("abc", "http://a.bc")
    writer.startElementNS(("http://a.bc", "ele1"), "ele1", dict())
    # writer.startElement("test", dict())
    # writer.endElement("test")
    # writer.startElementNS(("http://a.bc", "test"), None, dict())
    # writer.endElementNS(("http://a.bc", "test"), "test")
    writer.endElementNS(("http://a.bc", "ele1"), "ele1")
    writer.endElement("root")
    writer.endPrefixMapping("abc")
    writer.endDocument()

    content = buf.getvalue()

    assert (
        content == """<?xml version="1.0" encoding="utf-8"?>\n<root>\n"""
        """  <abc:ele1 xmlns:abc="http://a.bc"></abc:ele1>\n</root>"""
    )


def test_streamwriter_xcql_ns():
    buf = io.StringIO()

    writer = SRUXMLStreamWriter(buf, SRURecordXmlEscaping.STRING, indent=2)

    query = cql.parse("stuff")
    query.setServerDefaults()

    writer.startDocument()
    writer.startPrefixMapping("abc", "http://a.bc")
    writer.startElement("root", dict())
    writer.startElement("ele1", dict())
    writer.endElement("ele1")
    writer.startElementNS(("http://a.bc", "xQuery"), "xQuery", dict())
    writer.writeXCQL(query, False)
    writer.endElementNS(("http://a.bc", "xQuery"), "xQuery")
    writer.endElement("root")
    writer.endPrefixMapping("abc")
    writer.endDocument()

    content = buf.getvalue()

    assert (
        content
        == """<?xml version="1.0" encoding="utf-8"?>\n<root>\n  <ele1></ele1>\n"""
        """  <abc:xQuery xmlns:abc="http://a.bc">\n    <index>cql.serverChoice"""
        """</index>\n    <relation>\n      <value>=</value>\n    </relation>\n"""
        """    <term>stuff</term>\n  </abc:xQuery>\n</root>"""
    )


def test_record_packing():
    buf = io.StringIO()
    writer = SRUXMLStreamWriter(buf, SRURecordXmlEscaping.XML, indent=2)

    writer.startElement("root", dict())
    writer.startRecord()
    writer.startElement("test", dict())
    writer.endElement("test")
    writer.endRecord()
    writer.endElement("root")

    content = buf.getvalue()
    assert content == """<root>\n  <test></test>\n</root>"""

    buf = io.StringIO()
    writer = SRUXMLStreamWriter(buf, SRURecordXmlEscaping.STRING, indent=2)

    writer.startElement("root", dict())
    writer.startRecord()
    writer.startElement("test", dict())
    writer.endElement("test")
    writer.endRecord()
    writer.endElement("root")

    content = buf.getvalue()
    assert content == """<root>&lt;test&gt;&lt;/test&gt;</root>"""


def test_default_ns():
    buf = io.StringIO()
    writer = SRUXMLStreamWriter(buf, SRURecordXmlEscaping.XML, indent=2)

    writer.startPrefixMapping(None, "http://default.ns")
    writer.startPrefixMapping("ns", "http://name.space")
    with writer.element("root", "http://name.space"):
        with writer.element("test"):
            writer.characters("content")

    content = buf.getvalue()
    assert (
        content
        == """<ns:root xmlns="http://default.ns" xmlns:ns="http://name.space">\n  <test>content</test>\n</ns:root>"""
    )


# ---------------------------------------------------------------------------


@pytest.mark.skip("manual testing")
def test_buffered_io():
    fp = io.StringIO()
    buf = io.BufferedWriter(fp, buffer_size=16)

    buf.write("abc")

    assert fp.getvalue() == ""
    buf.flush()
    assert fp.getvalue() == "abc"


@pytest.mark.skip("manual testing")
def test_lxml_xmlfile():
    fp = io.BytesIO()
    buf = io.BufferedWriter(fp, buffer_size=1024)

    with etree.xmlfile(buf, encoding="utf-8", close=False, buffered=True) as xf:
        # xf.write_declaration(standalone=True)
        with xf.element("root"):
            with xf.element("elements"):
                for i in range(10):
                    with xf.element("element", {"nr": str(i)}):
                        pass

        xf.flush()

    assert fp.getvalue() == b""

    buf.flush()

    content = fp.getvalue()

    assert content.startswith(b"<root><")

    import lxml.sax

    class MyHandler(lxml.sax.ElementTreeContentHandler):
        def __init__(self, makeelement=None):
            super().__init__(makeelement)
            self.indentlevel = 0
            self.saw_content = False

        def startElementNS(self, ns_name, qname, attributes=None):
            print(ns_name, qname, attributes)
            if qname != "root":
                self.indentlevel += 1
                self.characters("\n" + (self.indentlevel * "  "))
            return super().startElementNS(ns_name, qname, attributes)

        def endElementNS(self, ns_name, qname):
            if not self.saw_content:
                self.characters("\n" + (self.indentlevel * "  "))
                self.indentlevel -= 1
            return super().endElementNS(ns_name, qname)

    handler = MyHandler()

    lxml.sax.saxify(etree.parse(io.BytesIO(content)), handler)

    tree = handler.etree
    content2 = etree.tostring(tree.getroot())
    print(content2.decode())

    assert content == content2

    assert content2 is None


# ---------------------------------------------------------------------------
