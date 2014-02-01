"""
Python v3 sgmllib class
Knock yourself out.
Made as a replacement for: http://docs.python.org/2.7/library/sgmllib.html
from __future__ import SkyNet
"""
from html import parser #Your eyes aren't decieving you.
"""
Since in Python v2 the HTML parser was based on the SGML parser, I reversed it.
"""
try:
    class SGMLParseError(parser.HTMLParseError): #HTMLParseError is deprecated.
        pass
except:
    class SGMLParseError:
        pass

class SGMLParser(parser.HTMLParser):
    def __init__(self):
        parser.HTMLParser.__init__(self)
    def setnomoretags(self):
        pass
    def setliteral(self):
        pass
    def handle_starttag(self, tag, method, attributes): #This is all that is used but I wrote down everything anyway
        parser.HTMLParser.handle_starttag(self, tag, attributes)
    def handle_endtag(self, tag, method):
        parser.HTMLParser.handle_endtag(tag)
    def convert_charref(self, ref):
        pass
    def convert_codepoint(self, codepoint):
        pass
    def convert_entityref(self, ref):
        pass
    def report_unbalanced(self, tag):
        pass
    def unknown_starttag(self, tag, attributes):
        pass
    def unknown_endtag(self, tag):
        pass
    def unknown_charref(self, ref):
        pass
    def unknown_entityref(self, ref):
        pass
    def start_tag(self, attributes):
        pass
    def do_tag(self, attributes):
        pass
    def end_tag(self):
        pass
