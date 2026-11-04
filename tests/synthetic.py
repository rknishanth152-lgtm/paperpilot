"""Synthetic test inputs shared by unit and integration tests.

No real paper content: small TEI documents shaped like GROBID 0.9.1 output
(docs/experiments/grobid-feasibility.md §5.1) and tiny valid PDFs.
"""

TEI_NS = "http://www.tei-c.org/ns/1.0"


def tei(
    *,
    header: str = "",
    abstract: str = "",
    body: str = "",
    back: str = "",
    pages: int = 2,
    version: str = "0.9.1",
    title: str = "A Synthetic Paper",
) -> bytes:
    """A TEI document; `header` is inserted after the authors (for example a DOI)."""
    surfaces = "".join(
        f'<surface n="{n}" ulx="0" uly="0" lrx="612" lry="792"/>'
        for n in range(1, pages + 1)
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="{TEI_NS}">
  <teiHeader>
    <fileDesc>
      <titleStmt><title level="a" type="main">{title}</title></titleStmt>
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


def tiny_pdf(page_content: bytes) -> bytes:
    """A valid one-page PDF with Helvetica and the given content stream."""
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
        ),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length %d >>\nstream\n" % len(page_content)
        + page_content
        + b"\nendstream",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % number + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    out += b"".join(b"%010d 00000 n \n" % o for o in offsets)
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objects) + 1,
        xref,
    )
    return bytes(out)


TEXT_PAGE_PDF = tiny_pdf(
    b"BT /F1 12 Tf 72 720 Td (A synthetic sentence for the parser test.) Tj ET"
)
BLANK_PAGE_PDF = tiny_pdf(b"")
