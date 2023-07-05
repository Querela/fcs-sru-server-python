import io
import xml.etree.ElementTree as ET
import xml.sax.saxutils
from collections import deque
from contextlib import contextmanager
from enum import Enum
from enum import auto
from typing import Deque
from typing import Union
from xml.sax import SAXException
from xml.sax.handler import ContentHandler
from xml.sax.saxutils import XMLGenerator

import cql
from lxml import etree
from lxml.sax import saxify

from ..constants import RESPONSE_ENCODING
from ..constants import SRURecordXmlEscaping

# ---------------------------------------------------------------------------


class SRUXMLStreamWriter(ContentHandler):
    class IndentingState(Enum):
        SEEN_NOTHING = auto()
        SEEN_ELEMENT = auto()
        SEEN_DATA = auto()

    def __init__(
        self,
        output_stream: io.TextIOBase,
        record_escaping: SRURecordXmlEscaping,
        indent: int = -1,
        encoding: str = RESPONSE_ENCODING,
        short_empty_elements: bool = False,
    ) -> None:
        super().__init__()
        self.record_escaping = record_escaping
        self.writing_record = False
        # TODO: SRURecordXmlEscaping.STRING
        # https://www.loc.gov/standards/sru/sru-1-1.html#packing
        # if self.writing_record and self.record_escaping == SRURecordXmlEscaping.STRING:
        #     content = escape(content)

        self.depth = 0
        self.indent = indent
        self.indent_state = SRUXMLStreamWriter.IndentingState.SEEN_NOTHING
        self.indent_state_stack: Deque[SRUXMLStreamWriter.IndentingState] = deque()

        self.output_stream = self.output_stream_raw = output_stream

        if self.record_escaping == SRURecordXmlEscaping.STRING:
            # output_stream.__class__ ?
            class SRURecordXmlEscapingStream(io.TextIOBase):
                def __init__(self, writer) -> None:
                    super().__init__()
                    self.writer = writer

                def write(self, __s: str) -> int:
                    if self.writer.writing_record:
                        __s = xml.sax.saxutils.escape(__s)
                    return self.writer.output_stream.write(__s)

                def flush(self) -> None:
                    return self.writer.output_stream.flush()

            # FIXME: is that stable, even required?
            # self.output_stream = xml.sax.saxutils._gettextwriter(
            #     self.output_stream, encoding
            # )
            xml_output_stream: Union[
                SRURecordXmlEscapingStream, io.TextIOBase
            ] = SRURecordXmlEscapingStream(self)

        else:
            xml_output_stream = self.output_stream

        self.xmlwriter = XMLGenerator(
            xml_output_stream,
            encoding=encoding,
            short_empty_elements=short_empty_elements,
        )

    # ----------------------------------------------------

    def _should_do_indent_stuff(self):
        if not self.writing_record:
            return True
        if self.record_escaping != SRURecordXmlEscaping.STRING:
            return True
        return False

    def onStartElement(self):
        if self._should_do_indent_stuff():
            self.indent_state_stack.append(
                SRUXMLStreamWriter.IndentingState.SEEN_ELEMENT
            )
            self.indent_state = SRUXMLStreamWriter.IndentingState.SEEN_NOTHING
            if self.depth > 0:
                self.xmlwriter.characters("\n")
            self.doIndent()
            self.depth += 1

    def onEndElement(self):
        if self._should_do_indent_stuff():
            self.depth -= 1
            if self.indent_state == SRUXMLStreamWriter.IndentingState.SEEN_ELEMENT:
                self.xmlwriter.characters("\n")
                self.doIndent()
            self.indent_state = self.indent_state_stack.pop()

    def onEmptyElement(self):
        if self._should_do_indent_stuff:
            self.indent_state = SRUXMLStreamWriter.IndentingState.SEEN_ELEMENT
            if self.depth > 0:
                self.xmlwriter.characters("\n")
            self.doIndent()

    def doIndent(self):
        if self.depth > 0:
            self.xmlwriter.characters(" " * self.depth * self.indent)

    # ----------------------------------------------------

    def startRecord(self):
        if self.writing_record:
            raise ValueError("was already writing record")
        self.xmlwriter._flush()  # or call on my stream variable?
        # force writer to close/finish any pending start or end elements
        self.xmlwriter._finish_pending_start_element()
        self.writing_record = True

    def endRecord(self):
        if not self.writing_record:
            raise ValueError("was not writing record")
        # force writer to close/finish any pending start or end elements
        self.xmlwriter._finish_pending_start_element()
        self.xmlwriter._flush()  # or call on my stream variable?
        self.writing_record = False

    # ----------------------------------------------------
    # ContentHandler methods

    def setDocumentLocator(self, locator):
        self.xmlwriter.setDocumentLocator(locator)

    def startPrefixMapping(self, prefix, uri):
        self.xmlwriter.startPrefixMapping(prefix, uri)

    def endPrefixMapping(self, prefix):
        self.xmlwriter.endPrefixMapping(prefix)

    def processingInstruction(self, target, data):
        self.xmlwriter.processingInstruction(target, data)

    def startDocument(self):
        self.xmlwriter.startDocument()
        # if self.indent > 0:
        #     self.xmlwriter.characters("\n")

    def endDocument(self):
        self.xmlwriter.endDocument()

    def startElement(self, name, attrs=None):
        if self.indent > 0:
            self.onStartElement()
        if attrs is None:
            attrs = dict()
        self.xmlwriter.startElement(name, attrs)

    def endElement(self, name):
        if self.indent > 0:
            self.onEndElement()
        self.xmlwriter.endElement(name)

    def startElementNS(self, name, qname=None, attrs=None):
        if self.indent > 0:
            self.onStartElement()
        if attrs is None:
            attrs = dict()
        else:
            # small helper to set None-namespace for attributes
            # that did not supply them
            if not all(isinstance(key, tuple) for key in attrs.keys()):
                attrs_copy = dict()
                for key, value in attrs.items():
                    if not isinstance(key, tuple):
                        key = (None, key)
                    attrs_copy[key] = value
                attrs = attrs_copy
        self.xmlwriter.startElementNS(name, qname, attrs)

    def endElementNS(self, name, qname=None):
        if self.indent > 0:
            self.onEndElement()
        self.xmlwriter.endElementNS(name, qname)

    def characters(self, content):
        if self.indent > 0:
            self.indent_state = SRUXMLStreamWriter.IndentingState.SEEN_DATA
        self.xmlwriter.characters(content)

    def ignorableWhitespace(self, whitespace):
        self.xmlwriter.ignorableWhitespace(whitespace)

    def skippedEntity(self, name):
        self.xmlwriter.skippedEntity(name)

    # ----------------------------------------------------

    def writeXCQL(self, query: cql.CQLQuery, search_retrieve_mode: bool):
        # HACK: Parsing the XCQL to serialize is wasting resources.
        # Alternative would be to serialize to XCQL from CQLNode, but
        # I'm not yet enthusiastic on writing the serializer myself.

        class XCQLHandler(ContentHandler):
            def __init__(self, writer):
                super().__init__()
                self.writer = writer

            def startElementNS(self, name, qname, attrs):
                if not search_retrieve_mode and qname == "searchClause":
                    return
                self.writer.startElementNS(name, qname, attrs)

            def endElementNS(self, name, qname):
                if not search_retrieve_mode and qname == "searchClause":
                    return
                self.writer.endElementNS(name, qname)

            def characters(self, content):
                if not content or content.isspace():
                    return
                self.writer.characters(content)

        try:
            # tree = query.toXCQL()
            # content = query.toXCQLString()
            tree = query.root.toXCQL()
            content = ET.tostring(tree)
            tree = etree.fromstring(content)
            handler = XCQLHandler(self)
            saxify(tree, handler)
        except Exception as ex:
            raise SAXException("serializing xcql failed") from ex

    # ----------------------------------------------------

    @contextmanager
    def prefix(self, prefix, uri):
        self.startPrefixMapping(self, prefix, uri)
        yield
        self.endPrefixMapping(prefix)

    @contextmanager
    def element(self, name, namespace=None, attrs=None):
        self.startElementNS((namespace, name), attrs=attrs)
        yield
        self.endElementNS((namespace, name))

    def elementcontent(self, name, content=None, namespace=None, attrs=None):
        self.startElementNS((namespace, name), attrs=attrs)
        self.characters(content)
        self.endElementNS((namespace, name))

    @contextmanager
    def record(self):
        self.startRecord()
        yield
        self.endRecord()


# ---------------------------------------------------------------------------


def copy_XML_into_writer(writer: ContentHandler, xml: Union[bytes, str]):
    class XMLCopyHandler(ContentHandler):
        def __init__(self, writer):
            super().__init__()
            self.writer = writer

        def startPrefixMapping(self, prefix, uri):
            self.writer.startPrefixMapping(prefix, uri)

        def endPrefixMapping(self, prefix):
            self.writer.endPrefixMapping(prefix)

        def startElementNS(self, name, qname, attrs):
            self.writer.startElementNS(name, qname, attrs)

        def endElementNS(self, name, qname):
            self.writer.endElementNS(name, qname)

        def characters(self, content):
            # if not content or content.isspace():
            #     return
            self.writer.characters(content)

    try:
        tree = etree.fromstring(xml)
        handler = XMLCopyHandler(writer)
        saxify(tree, handler)
    except Exception as ex:
        raise SAXException("serializing xml failed") from ex


class XMLStreamWriterHelper(ContentHandler):
    def __init__(self, xmlwriter: ContentHandler) -> None:
        super().__init__()
        self.xmlwriter = xmlwriter

        # unwrap to avoid uneccessary call chains
        if (
            isinstance(self.xmlwriter, XMLStreamWriterHelper)
            and self.xmlwriter.__class__ == XMLStreamWriterHelper
        ):
            self.xmlwriter = self.xmlwriter.xmlwriter

    # ----------------------------------------------------
    # ContentHandler methods

    def setDocumentLocator(self, locator):
        self.xmlwriter.setDocumentLocator(locator)

    def startPrefixMapping(self, prefix, uri):
        self.xmlwriter.startPrefixMapping(prefix, uri)

    def endPrefixMapping(self, prefix):
        self.xmlwriter.endPrefixMapping(prefix)

    def processingInstruction(self, target, data):
        self.xmlwriter.processingInstruction(target, data)

    def startDocument(self):
        self.xmlwriter.startDocument()

    def endDocument(self):
        self.xmlwriter.endDocument()

    def startElement(self, name, attrs=None):
        if attrs is None:
            attrs = dict()
        self.xmlwriter.startElement(name, attrs)

    def endElement(self, name):
        self.xmlwriter.endElement(name)

    def startElementNS(self, name, qname=None, attrs=None):
        if attrs is None:
            attrs = dict()
        else:
            # small helper to set None-namespace for attributes
            # that did not supply them
            if not all(isinstance(key, tuple) for key in attrs.keys()):
                attrs_copy = dict()
                for key, value in attrs.items():
                    if not isinstance(key, tuple):
                        key = (None, key)
                    attrs_copy[key] = value
                attrs = attrs_copy
        self.xmlwriter.startElementNS(name, qname, attrs)

    def endElementNS(self, name, qname=None):
        self.xmlwriter.endElementNS(name, qname)

    def characters(self, content):
        self.xmlwriter.characters(content)

    def ignorableWhitespace(self, whitespace):
        self.xmlwriter.ignorableWhitespace(whitespace)

    def skippedEntity(self, name):
        self.xmlwriter.skippedEntity(name)

    # ----------------------------------------------------

    def writeXML(self, xml: Union[bytes, str]):
        copy_XML_into_writer(self, xml)

    def writeXMLdocument(self, xmldoc: ET.Element):
        try:
            content = ET.tostring(xmldoc)
            self.writeXML(content)
        except SAXException:
            raise
        except Exception as ex:
            raise SAXException("serializing xmldoc failed") from ex

    # ----------------------------------------------------
    # contextmanagers + SRUXMLStreamWriter methods

    @contextmanager
    def prefix(self, prefix, uri):
        self.startPrefixMapping(self, prefix, uri)
        yield
        self.endPrefixMapping(prefix)

    @contextmanager
    def element(self, name, namespace=None, attrs=None):
        self.startElementNS((namespace, name), attrs=attrs)
        yield
        self.endElementNS((namespace, name))

    def elementcontent(self, name, content=None, namespace=None, attrs=None):
        self.startElementNS((namespace, name), attrs=attrs)
        self.characters(content)
        self.endElementNS((namespace, name))

    def startRecord(self):
        if isinstance(self.xmlwriter, SRUXMLStreamWriter):
            self.xmlwriter.startRecord()

    def endRecord(self):
        if isinstance(self.xmlwriter, SRUXMLStreamWriter):
            self.xmlwriter.endRecord()

    @contextmanager
    def record(self):
        self.startRecord()
        yield
        self.endRecord()


# ---------------------------------------------------------------------------
