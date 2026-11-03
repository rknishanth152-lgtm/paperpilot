"""Turn GROBID TEI into PaperPilot's parser output (P3-T4).

`parse_tei` is a pure function of the TEI bytes: same input, same output, no
I/O. It implements docs/design/parser-output.md: metadata, passages from four
regions (abstract, body, caption, back), pages from coordinates, and the
provisional rules R1 (join split paragraphs) and R2 (skip paragraphs without
letters). Paper text is never put into error messages (NFR-PRI-002).
"""

import re
from dataclasses import dataclass, field
from xml.etree import ElementTree

NS = "{http://www.tei-c.org/ns/1.0}"
PARSER_NAME = "grobid"
_SENTENCE_END = (".", "?", "!", ":")
_LETTER = re.compile(r"[^\W\d_]")  # a letter in any script
_UNSAFE_XML = (b"<!DOCTYPE", b"<!ENTITY")  # GROBID never emits them


class ParseError(Exception):
    """The TEI cannot be used. `reason` is a stored failure_reason."""

    def __init__(self, reason: str, message: str) -> None:
        super().__init__(f"{reason}: {message}")
        self.reason = reason
        self.message = message


@dataclass(frozen=True)
class ParsedPassage:
    ordinal: int
    region: str  # "abstract" | "body" | "caption" | "back"
    back_type: str | None
    section_title: str | None
    section_number: str | None
    text: str
    page_start: int | None
    page_end: int | None


@dataclass(frozen=True)
class ParsedDocument:
    parser_name: str
    parser_version: str
    title: str | None
    authors: list[str]
    abstract: str | None
    doi: str | None
    page_count: int | None
    passages: list[ParsedPassage]
    skipped_paragraphs: int
    joined_paragraphs: int


@dataclass
class _Draft:
    region: str
    back_type: str | None
    section_title: str | None
    section_number: str | None
    text: str
    pages: list[int] = field(default_factory=list)


def parse_tei(raw: bytes) -> ParsedDocument:
    """Parse GROBID TEI. Raises ParseError (`malformed_tei`, `empty_parse`)."""
    root = _parse_xml(raw)
    header = root.find(f"{NS}teiHeader")
    version_element = root.find(f".//{NS}appInfo/{NS}application[@ident='GROBID']")
    version = version_element.get("version") if version_element is not None else None
    if header is None or not version:
        raise ParseError("malformed_tei", "TEI header or GROBID version is missing")

    builder = _Builder()
    abstract_paragraphs = builder.abstract(header)
    body = root.find(f"{NS}text/{NS}body")
    if body is not None:
        builder.container(body, region="body", back_type=None)
    back = root.find(f"{NS}text/{NS}back")
    if back is not None:
        for div in back.findall(f"{NS}div"):
            if div.get("type") != "references":
                builder.container(div, region="back", back_type=div.get("type"))

    if not any(draft.region == "body" for draft in builder.drafts):
        raise ParseError("empty_parse", "no body paragraphs with text were found")

    surfaces = root.findall(f"{NS}facsimile/{NS}surface")
    return ParsedDocument(
        parser_name=PARSER_NAME,
        parser_version=version,
        title=_text_or_none(header.find(f"{NS}fileDesc/{NS}titleStmt/{NS}title")),
        authors=_authors(header),
        abstract="\n\n".join(abstract_paragraphs) or None,
        doi=_text_or_none(
            header.find(
                f"{NS}fileDesc/{NS}sourceDesc/{NS}biblStruct/{NS}idno[@type='DOI']"
            )
        ),
        page_count=len(surfaces) or None,
        passages=[
            ParsedPassage(
                ordinal=ordinal,
                region=draft.region,
                back_type=draft.back_type,
                section_title=draft.section_title,
                section_number=draft.section_number,
                text=draft.text,
                page_start=min(draft.pages) if draft.pages else None,
                page_end=max(draft.pages) if draft.pages else None,
            )
            for ordinal, draft in enumerate(builder.drafts)
        ],
        skipped_paragraphs=builder.skipped,
        joined_paragraphs=builder.joined,
    )


class _Builder:
    """Collects passages in document order, applying R1 and R2."""

    def __init__(self) -> None:
        self.drafts: list[_Draft] = []
        self.skipped = 0
        self.joined = 0

    def abstract(self, header: ElementTree.Element) -> list[str]:
        abstract = header.find(f"{NS}profileDesc/{NS}abstract")
        if abstract is None:
            return []
        texts = []
        for group in abstract.findall(f"{NS}div") or [abstract]:
            title = _text_or_none(group.find(f"{NS}head"))
            for paragraph in group.findall(f".//{NS}p"):
                draft = self._paragraph(paragraph, "abstract", None, title, None)
                if draft is not None:
                    self.drafts.append(draft)
                    texts.append(draft.text)
        return texts

    def container(
        self, element: ElementTree.Element, *, region: str, back_type: str | None
    ) -> None:
        """Walk a body or back container: sections (div) and figures in order."""
        for child in element:
            if child.tag == f"{NS}div":
                self._section(child, region=region, back_type=back_type)
            elif child.tag == f"{NS}figure":
                self._caption(child)

    def _section(
        self, div: ElementTree.Element, *, region: str, back_type: str | None
    ) -> None:
        head = div.find(f"{NS}head")
        title = _text_or_none(head)
        number = head.get("n") if head is not None else None
        previous: _Draft | None = None  # R1 only joins directly adjacent paragraphs
        for child in div:
            if child.tag == f"{NS}p":
                draft = self._paragraph(child, region, back_type, title, number)
                if draft is None:
                    continue
                if previous is not None and _continues(previous.text, draft.text):
                    previous.text = f"{previous.text} {draft.text}"
                    previous.pages.extend(draft.pages)
                    self.joined += 1
                    continue
                self.drafts.append(draft)
                previous = draft
            elif child.tag == f"{NS}figure":
                self._caption(child)
                previous = None
            elif child.tag == f"{NS}div":
                self._section(child, region=region, back_type=back_type)
                previous = None

    def _paragraph(
        self,
        element: ElementTree.Element,
        region: str,
        back_type: str | None,
        title: str | None,
        number: str | None,
    ) -> _Draft | None:
        text = _text(element)
        if not _LETTER.search(text):
            self.skipped += 1  # R2
            return None
        return _Draft(region, back_type, title, number or None, text, _pages(element))

    def _caption(self, figure: ElementTree.Element) -> None:
        text = _text(figure.find(f"{NS}figDesc"))
        if not text:
            return
        label = _text(figure.find(f"{NS}head")).rstrip(" .:") or _text(
            figure.find(f"{NS}label")
        )
        self.drafts.append(
            _Draft("caption", None, label or None, None, text, _pages(figure))
        )


def _parse_xml(raw: bytes) -> ElementTree.Element:
    if any(marker in raw for marker in _UNSAFE_XML):
        raise ParseError(
            "malformed_tei", "TEI contains a document type or entity declaration"
        )
    try:
        root = ElementTree.fromstring(raw)
    except ElementTree.ParseError:
        raise ParseError("malformed_tei", "TEI is not well-formed XML") from None
    if root.tag != f"{NS}TEI":
        raise ParseError("malformed_tei", "root element is not a TEI document")
    return root


def _continues(previous: str, text: str) -> bool:
    """R1: a lowercase start continuing an unfinished directly preceding paragraph."""
    return text[0].islower() and not previous.endswith(_SENTENCE_END)


def _text(element: ElementTree.Element | None) -> str:
    if element is None:
        return ""
    return " ".join("".join(element.itertext()).split())


def _text_or_none(element: ElementTree.Element | None) -> str | None:
    return _text(element) or None


def _pages(element: ElementTree.Element) -> list[int]:
    coords = element.get("coords")
    if not coords:
        return []
    return [int(box.split(",", 1)[0]) for box in coords.split(";") if box]


def _authors(header: ElementTree.Element) -> list[str]:
    path = f"{NS}fileDesc/{NS}sourceDesc/{NS}biblStruct/{NS}analytic/{NS}author/{NS}persName"
    names = []
    for person in header.findall(path):
        parts = [
            _text(part)
            for part in person
            if part.tag in (f"{NS}forename", f"{NS}surname")
        ]
        name = " ".join(part for part in parts if part)
        if name:
            names.append(name)
    return names
