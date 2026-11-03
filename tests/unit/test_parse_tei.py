"""Tests for parse_tei (P3-T4, docs/design/parser-output.md).

Fixtures are small synthetic TEI documents shaped like GROBID 0.9.1 output
(docs/experiments/grobid-feasibility.md §5.1); no paper content is used.
"""

import pytest

from app.services.ingestion.tei import ParsedDocument, ParseError, parse_tei

NS = "http://www.tei-c.org/ns/1.0"


def tei(
    *,
    header: str = "",
    abstract: str = "",
    body: str = "",
    back: str = "",
    pages: int = 2,
    version: str = "0.9.1",
) -> bytes:
    surfaces = "".join(
        f'<surface n="{n}" ulx="0" uly="0" lrx="612" lry="792"/>'
        for n in range(1, pages + 1)
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="{NS}">
  <teiHeader>
    <fileDesc>
      <titleStmt><title level="a" type="main">A Synthetic Paper</title></titleStmt>
      <sourceDesc><biblStruct><analytic>
        <author><persName><forename type="first">Ada</forename><forename type="middle">B</forename><surname>Example</surname></persName></author>
        <author><persName><forename type="first">Ben</forename><surname>Sample</surname></persName></author>
      </analytic>{header}</biblStruct></sourceDesc>
    </fileDesc>
    <encodingDesc><appInfo><application version="{version}" ident="GROBID"/></appInfo></encodingDesc>
    <profileDesc><abstract>{abstract}</abstract></profileDesc>
  </teiHeader>
  <facsimile>{surfaces}</facsimile>
  <text><body>{body}</body><back>{back}</back></text>
</TEI>""".encode()


def p(text: str, coords: str | None = "1,10,10,100,10") -> str:
    attr = f' coords="{coords}"' if coords else ""
    return f"<p{attr}>{text}</p>"


def section(title: str, *paragraphs: str, n: str | None = None) -> str:
    number = f' n="{n}"' if n else ""
    return f"<div><head{number}>{title}</head>{''.join(paragraphs)}</div>"


BODY = section("Introduction", p("A synthetic sentence."), n="1")


def parse(**kwargs: object) -> ParsedDocument:
    return parse_tei(tei(**kwargs))  # type: ignore[arg-type]


def regions(doc: ParsedDocument) -> list[str]:
    return [passage.region for passage in doc.passages]


# --- metadata -----------------------------------------------------------------------


def test_metadata() -> None:
    doc = parse(header='<idno type="DOI">10.1/ABC</idno>', body=BODY, pages=3)

    assert doc.parser_name == "grobid"
    assert doc.parser_version == "0.9.1"
    assert doc.title == "A Synthetic Paper"
    assert doc.authors == ["Ada B Example", "Ben Sample"]
    assert doc.doi == "10.1/ABC"
    assert doc.page_count == 3


def test_missing_metadata_is_none_not_empty() -> None:
    raw = tei(body=BODY).replace(b"A Synthetic Paper", b"   ")

    doc = parse_tei(raw)

    assert doc.title is None
    assert doc.doi is None
    assert doc.abstract is None


def test_abstract_metadata_joins_abstract_paragraphs() -> None:
    doc = parse(abstract=f"<div>{p('First part.')}{p('Second part.')}</div>", body=BODY)

    assert doc.abstract == "First part.\n\nSecond part."


# --- regions and order ------------------------------------------------------------------


def test_regions_follow_document_order() -> None:
    doc = parse(
        abstract=f"<div><head>Abstract</head>{p('Summary.')}</div>",
        body=BODY
        + '<figure type="table" coords="2,1,1,1,1"><head>Table 2 .</head><label>2</label>'
        + "<figDesc>Accuracy by method.</figDesc><table><row><cell>0.9</cell></row></table></figure>",
        back='<div type="availability"><div><head>Data availability</head>'
        + p("All data are included.", "2,5,5,5,5")
        + "</div></div>",
    )

    assert regions(doc) == ["abstract", "body", "caption", "back"]
    assert [x.ordinal for x in doc.passages] == [0, 1, 2, 3]


def test_abstract_passage_takes_its_heading() -> None:
    doc = parse(abstract=f"<div><head>Abstract</head>{p('Summary.')}</div>", body=BODY)

    assert doc.passages[0].section_title == "Abstract"


def test_body_section_title_and_number() -> None:
    doc = parse(body=BODY)

    body = doc.passages[0]
    assert (body.section_title, body.section_number, body.text) == (
        "Introduction",
        "1",
        "A synthetic sentence.",
    )


def test_caption_uses_figure_label_pages_and_skips_table_cells() -> None:
    doc = parse(
        body=BODY
        + '<figure type="table" coords="2,1,1,1,1;3,1,1,1,1"><head>Table 2 .</head>'
        + "<figDesc>Accuracy by method.</figDesc><table><row><cell>CELLTEXT</cell></row></table></figure>"
    )

    caption = doc.passages[1]
    assert caption.region == "caption"
    assert caption.section_title == "Table 2"
    assert caption.text == "Accuracy by method."
    assert (caption.page_start, caption.page_end) == (2, 3)
    assert all("CELLTEXT" not in x.text for x in doc.passages)


def test_empty_caption_is_not_a_passage() -> None:
    doc = parse(
        body=BODY
        + '<figure coords="1,1,1,1,1"><head>Figure 1 .</head><figDesc> </figDesc></figure>'
    )

    assert regions(doc) == ["body"]


def test_back_matter_keeps_type_and_excludes_references() -> None:
    doc = parse(
        body=BODY,
        back='<div type="annex"><div><head>A Appendix</head>'
        + p("Extra results.")
        + "</div></div>"
        '<div type="references"><listBibl><biblStruct><note type="raw_reference">Ref one.</note>'
        "</biblStruct></listBibl></div>",
    )

    back = [x for x in doc.passages if x.region == "back"]
    assert len(back) == 1
    assert (back[0].back_type, back[0].section_title) == ("annex", "A Appendix")
    assert all("Ref one" not in x.text for x in doc.passages)


def test_reference_section_text_is_never_a_passage() -> None:
    """Even if GROBID wrote paragraphs inside the references section."""
    doc = parse(
        body=BODY,
        back='<div type="references"><div><head>References</head>'
        + p("Reference-like paragraph.")
        + "</div></div>",
    )

    assert regions(doc) == ["body"]


def test_figure_inside_back_matter_becomes_a_caption() -> None:
    doc = parse(
        body=BODY,
        back='<div type="annex"><div><head>B</head>' + p("Text.") + "</div>"
        '<figure type="table" coords="3,1,1,1,1"><head>Table 8 .</head><figDesc>Appendix table.</figDesc></figure></div>',
    )

    assert regions(doc) == ["body", "back", "caption"]
    assert doc.passages[2].back_type is None


def test_body_notes_are_not_passages() -> None:
    doc = parse(body=BODY + '<note place="foot">PLoS ONE | www.plosone.org</note>')

    assert all("plosone" not in x.text for x in doc.passages)


# --- text and pages --------------------------------------------------------------------


def test_text_includes_inline_citations_with_whitespace_collapsed() -> None:
    doc = parse(
        body=section("S", p('Shown  before\n   <ref type="bibr">[9][10]</ref>   here.'))
    )

    assert doc.passages[0].text == "Shown before [9][10] here."


def test_pages_come_from_first_and_last_box() -> None:
    doc = parse(body=section("S", p("Spans pages.", "4,1,1,1,1;4,1,2,1,1;5,1,1,1,1")))

    assert (doc.passages[0].page_start, doc.passages[0].page_end) == (4, 5)


def test_missing_coordinates_give_unknown_pages() -> None:
    doc = parse(body=section("S", p("No coordinates.", None)))

    assert (doc.passages[0].page_start, doc.passages[0].page_end) == (None, None)


def test_page_count_is_none_without_facsimile() -> None:
    assert parse(body=BODY, pages=0).page_count is None


# --- R1: join split paragraphs -------------------------------------------------------------


def test_r1_joins_adjacent_split_paragraph_in_same_section() -> None:
    doc = parse(
        body=section(
            "S",
            p("The first half is obliged to target smaller", "2,1,1,1,1"),
            p("effect sizes. The rest follows.", "3,1,1,1,1"),
        )
    )

    assert len(doc.passages) == 1
    assert doc.passages[0].text == (
        "The first half is obliged to target smaller effect sizes. The rest follows."
    )
    assert (doc.passages[0].page_start, doc.passages[0].page_end) == (2, 3)
    assert doc.joined_paragraphs == 1


@pytest.mark.parametrize(
    ("first", "second"),
    [
        ("A complete sentence.", "lowercase start after a full stop."),
        ("Ends with a question?", "lowercase start."),
        ("Ends with a colon:", "lowercase start."),
        ("Unfinished", "Capital start continues."),
    ],
)
def test_r1_does_not_join_otherwise(first: str, second: str) -> None:
    doc = parse(body=section("S", p(first), p(second)))

    assert len(doc.passages) == 2
    assert doc.joined_paragraphs == 0


def test_r1_never_joins_across_a_figure() -> None:
    """A figure between two paragraphs means they are not directly adjacent."""
    doc = parse(
        body=(
            "<div><head>S</head>"
            + p("Unfinished")
            + '<figure coords="1,1,1,1,1"><head>Figure 1 .</head><figDesc>A chart.</figDesc></figure>'
            + p("lowercase start.")
            + "</div>"
        )
    )

    assert [x.region for x in doc.passages] == ["body", "caption", "body"]
    assert doc.joined_paragraphs == 0


def test_r1_never_joins_across_sections() -> None:
    doc = parse(
        body=section("One", p("Unfinished")) + section("Two", p("lowercase start."))
    )

    assert len(doc.passages) == 2


def test_r1_does_not_join_abstract_paragraphs() -> None:
    doc = parse(
        abstract=f"<div>{p('Unfinished')}{p('lowercase start.')}</div>", body=BODY
    )

    assert regions(doc).count("abstract") == 2


# --- R2: skip paragraphs with no letters ---------------------------------------------------


def test_r2_skips_paragraphs_without_letters_and_counts_them() -> None:
    doc = parse(body=section("S", p("Real text."), p("..."), p("12"), p("   ")))

    assert [x.text for x in doc.passages] == ["Real text."]
    assert doc.skipped_paragraphs == 3


def test_letters_in_any_script_count() -> None:
    doc = parse(body=section("S", p("Été 2024."), p("αβγ")))

    assert len(doc.passages) == 2


# --- outcomes ---------------------------------------------------------------------------------


def test_document_without_body_passages_is_an_empty_parse() -> None:
    with pytest.raises(ParseError) as error:
        parse(abstract=f"<div>{p('Only an abstract.')}</div>", body="")

    assert error.value.reason == "empty_parse"


def test_body_with_only_junk_is_an_empty_parse() -> None:
    with pytest.raises(ParseError) as error:
        parse(body=section("S", p("...")))

    assert error.value.reason == "empty_parse"


@pytest.mark.parametrize(
    "raw",
    [
        b"",
        b"not xml at all",
        b"<TEI><unclosed></TEI>",
        b'<?xml version="1.0"?><html xmlns="http://www.w3.org/1999/xhtml"/>',
        b'<?xml version="1.0"?><!DOCTYPE TEI [<!ENTITY x "y">]><TEI xmlns="http://www.tei-c.org/ns/1.0"/>',
    ],
)
def test_unusable_xml_is_malformed_tei(raw: bytes) -> None:
    with pytest.raises(ParseError) as error:
        parse_tei(raw)

    assert error.value.reason == "malformed_tei"


@pytest.mark.parametrize(
    "declaration",
    [b"<!DOCTYPE TEI>", b'<!DOCTYPE TEI [<!ENTITY note "x">]>'],
)
def test_otherwise_valid_tei_with_a_doctype_is_rejected(declaration: bytes) -> None:
    raw = tei(body=BODY).replace(b"<TEI ", declaration + b"\n<TEI ", 1)

    with pytest.raises(ParseError) as error:
        parse_tei(raw)

    assert error.value.reason == "malformed_tei"


def test_missing_parser_version_is_malformed_tei() -> None:
    with pytest.raises(ParseError) as error:
        parse_tei(tei(body=BODY).replace(b'version="0.9.1" ', b""))

    assert error.value.reason == "malformed_tei"


def test_parsing_is_deterministic() -> None:
    raw = tei(abstract=f"<div>{p('A.')}</div>", body=BODY)

    assert parse_tei(raw) == parse_tei(raw)


def test_error_messages_contain_no_document_text() -> None:
    with pytest.raises(ParseError) as error:
        parse(abstract=f"<div>{p('SECRET-LOOKING TEXT.')}</div>", body="")

    assert error.value.reason == "empty_parse"
    assert "SECRET" not in error.value.message
