"""Static HTML text extraction without fetching linked resources."""

from html.parser import HTMLParser
import re


class HtmlTextExtractor(HTMLParser):
    IGNORED = {"script", "style", "noscript", "svg", "template"}
    BLOCKS = {"p", "div", "section", "article", "header", "footer", "li", "ul", "ol",
              "h1", "h2", "h3", "h4", "h5", "h6", "br", "tr", "table", "blockquote", "pre"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.title_parts: list[str] = []
        self.ignored: list[str] = []
        self.in_title = False
        self.in_head = False

    def handle_starttag(self, tag, attrs):
        if self.ignored:
            if tag in self.IGNORED:
                self.ignored.append(tag)
            return
        if tag in self.IGNORED:
            self.ignored.append(tag)
        elif tag == "head":
            self.in_head = True
        elif tag == "title":
            self.in_title = True
        elif tag in self.BLOCKS:
            self.parts.append("\n")
        elif tag in {"td", "th"}:
            self.parts.append(" ")

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if self.ignored:
            if tag == self.ignored[-1]:
                self.ignored.pop()
            return
        if tag == "title":
            self.in_title = False
        elif tag == "head":
            self.in_head = False
        elif tag in self.BLOCKS:
            self.parts.append("\n")

    def handle_data(self, data):
        if self.ignored:
            return
        if self.in_title:
            self.title_parts.append(data)
        elif not self.in_head:
            self.parts.append(data)

    def result(self) -> tuple[str, str]:
        lines = [re.sub(r"\s+", " ", line).strip() for line in "".join(self.parts).splitlines()]
        return "\n".join(line for line in lines if line), re.sub(r"\s+", " ", "".join(self.title_parts)).strip()
