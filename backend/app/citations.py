"""Chicago Manual of Style citation formatting.

Targets the 18th edition (2024) and supports both Chicago systems:

* **Notes-Bibliography** -- a numbered note plus a bibliography entry.
* **Author-Date** -- an in-text parenthetical plus a reference-list entry.

Formatted output is built as a list of :class:`Span` rather than a string so
that italics survive into HTML without the formatter emitting markup, and so
the plain-text form used for copying is derived from the same structure.

Scope and honesty about it: this covers the source types the tracker records --
web pages, news and magazine articles, video, audio, datasets, generic
documents, legislative and legal material, and social media posts. Chicago
defers to Bluebook conventions for much legal material and carries far more
special cases than are implemented here, so unusual sources may need an
editor's hand. Where the 18th edition differs from the 17th in a way that
affects output, the difference is noted at the point it applies.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime

SITE_STYLE_NOTES = "notes-bibliography"
SITE_STYLE_AUTHOR_DATE = "author-date"
CITATION_STYLES = (SITE_STYLE_NOTES, SITE_STYLE_AUTHOR_DATE)

# Longest run of post text quoted inside a social-media citation. Chicago
# quotes enough of a short post to identify it, not the whole thing.
POST_QUOTE_LIMIT = 160

# Notes name up to three authors, then fall back to "et al.". A bibliography
# lists up to ten; beyond that Chicago lists the first seven and then "et al."
NOTE_AUTHOR_LIMIT = 3
BIBLIOGRAPHY_AUTHOR_LIMIT = 10
BIBLIOGRAPHY_AUTHOR_TRUNCATED_COUNT = 7


@dataclass(frozen=True)
class Span:
    """A run of citation text, optionally italicised."""

    text: str
    italic: bool = False


def spans_to_text(spans: list[Span]) -> str:
    return "".join(span.text for span in spans)


def spans_to_dicts(spans: list[Span]) -> list[dict]:
    """Serialise for the API.

    The client renders these as elements rather than as markup, so no HTML is
    produced here and nothing needs to be trusted on the way out.
    """
    return [{"text": span.text, "italic": span.italic} for span in spans]


@dataclass
class CitationInput:
    """Everything the formatters need, normalised away from the ORM."""

    title: str = ""
    url: str | None = None
    authors: list[dict] = field(default_factory=list)
    container_title: str | None = None
    publisher: str | None = None
    published_date: datetime | None = None
    accessed: datetime | None = None
    locator: str | None = None
    edition: str | None = None
    media_type: str = "webpage"
    document_type: str | None = None
    bill_number: str | None = None
    congress_number: int | None = None
    congress_session: str | None = None
    committee: str | None = None
    report_number: str | None = None
    # Social media only.
    handle: str | None = None
    post_text: str | None = None


# --- Names --------------------------------------------------------------


def _display_name(author: dict) -> str:
    """Natural order: "Jane Doe", or a corporate name unchanged."""
    literal = (author.get("literal") or "").strip()
    if literal:
        return literal
    given = (author.get("given") or "").strip()
    family = (author.get("family") or "").strip()
    return " ".join(part for part in (given, family) if part)


def _inverted_name(author: dict) -> str:
    """Bibliography order: "Doe, Jane". Corporate names are never inverted."""
    literal = (author.get("literal") or "").strip()
    if literal:
        return literal
    given = (author.get("given") or "").strip()
    family = (author.get("family") or "").strip()
    if family and given:
        return f"{family}, {given}"
    return family or given


def _clean_authors(authors: list[dict] | None) -> list[dict]:
    if not authors:
        return []
    return [a for a in authors if isinstance(a, dict) and _display_name(a)]


def _join_series(names: list[str]) -> str:
    """Serial-comma join: "A", "A and B", "A, B, and C"."""
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]} and {names[1]}"
    return f"{', '.join(names[:-1])}, and {names[-1]}"


def format_authors_note(authors: list[dict] | None) -> str:
    cleaned = _clean_authors(authors)
    if not cleaned:
        return ""
    if len(cleaned) > NOTE_AUTHOR_LIMIT:
        return f"{_display_name(cleaned[0])} et al."
    return _join_series([_display_name(a) for a in cleaned])


def format_authors_bibliography(authors: list[dict] | None) -> str:
    cleaned = _clean_authors(authors)
    if not cleaned:
        return ""

    if len(cleaned) > BIBLIOGRAPHY_AUTHOR_LIMIT:
        kept = cleaned[:BIBLIOGRAPHY_AUTHOR_TRUNCATED_COUNT]
        listed = [_inverted_name(kept[0])] + [_display_name(a) for a in kept[1:]]
        return f"{', '.join(listed)}, et al."

    names = [_inverted_name(cleaned[0])] + [_display_name(a) for a in cleaned[1:]]
    if len(names) == 1:
        return names[0]
    # The leading name is inverted and so already contains a comma; Chicago
    # therefore keeps the comma before "and" even with only two authors:
    # "Ward, Geoffrey C., and Ken Burns."
    return f"{', '.join(names[:-1])}, and {names[-1]}"


def author_date_name(authors: list[dict] | None) -> str:
    """Surname (or corporate name) used in an author-date parenthetical."""
    cleaned = _clean_authors(authors)
    if not cleaned:
        return ""
    first = cleaned[0]
    literal = (first.get("literal") or "").strip()
    if literal:
        return literal
    surname = (first.get("family") or "").strip() or _display_name(first)
    if len(cleaned) == 1:
        return surname
    if len(cleaned) == 2:
        second = cleaned[1]
        second_name = (second.get("literal") or "").strip() or (
            second.get("family") or ""
        ).strip()
        return f"{surname} and {second_name}"
    return f"{surname} et al."


# --- Dates --------------------------------------------------------------


def format_full_date(value: datetime | None) -> str:
    if value is None:
        return ""
    # %-d is not portable, so the leading zero is stripped explicitly.
    return f"{value.strftime('%B')} {value.day}, {value.year}"


def format_year(value: datetime | None) -> str:
    return str(value.year) if value else "n.d."


def _sentence(text: str) -> str:
    """End a bibliography element with a single period and a space."""
    return text + (" " if text.endswith(".") else ". ")


def _year_sentence(value: datetime | None) -> str:
    """The year as its own sentence in a reference list entry.

    "n.d." already carries a final period, so appending another would produce
    "n.d..".
    """
    year = format_year(value)
    return year + (" " if year.endswith(".") else ". ")


def _ordinal(number: int) -> str:
    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


def _should_show_access_date(data: CitationInput) -> bool:
    """Chicago 18th: give an access date only when nothing else dates the source.

    The 17th edition encouraged access dates more broadly; if you need that
    behaviour, return True whenever ``data.accessed`` is set.
    """
    return data.accessed is not None and data.published_date is None


# --- Shared pieces ------------------------------------------------------


def _titled_work_is_italic(data: CitationInput) -> bool:
    """Whether the source's own title takes italics rather than quotation marks.

    Standalone works -- books, reports, bills, datasets -- are italicised.
    Pieces within a larger work -- articles, web pages, posts -- take quotes.
    """
    if data.document_type:
        return True
    return data.media_type in {"document", "dataset"}


def _container_is_italic(data: CitationInput) -> bool:
    """Periodicals are italicised; plain website names are set in roman."""
    return data.media_type == "article"


def _media_descriptor(data: CitationInput) -> str:
    return {"video": "video", "audio": "audio"}.get(data.media_type, "")


def _locator_is_timestamp(locator: str | None) -> bool:
    return bool(locator and re.fullmatch(r"\d{1,2}:\d{2}(:\d{2})?", locator.strip()))


# --- Legislative and legal material -------------------------------------


def _legal_spans(data: CitationInput) -> list[Span] | None:
    """Chicago's forms for public documents, or None if this is not one.

    Chicago follows Bluebook conventions here, and these materials normally
    appear in notes rather than in a bibliography.
    """
    if not data.document_type or data.document_type == "other":
        return None

    year = f"({data.published_date.year})" if data.published_date else "(n.d.)"
    congress = (
        f"{_ordinal(data.congress_number)} Cong." if data.congress_number else ""
    )
    if congress and data.congress_session:
        congress = f"{congress}, {data.congress_session} sess."

    spans: list[Span] = []

    if data.document_type in {"bill", "statute"}:
        # Fair Housing Act of 2026, H.R. 1234, 118th Cong., 2nd sess. (2026).
        segments = [
            segment
            for segment in (data.title, data.bill_number, congress)
            if segment
        ]
        spans.append(Span(", ".join(segments)))
        spans.append(Span(f" {year}" if segments else year))
    elif data.document_type == "hearing":
        # Title: Hearing before the Committee on X, 118th Cong. (2026).
        if data.title:
            spans.append(Span(data.title, italic=True))
            spans.append(Span(": "))
        if data.committee:
            spans.append(Span(f"Hearing before the {data.committee}, "))
        if congress:
            spans.append(Span(f"{congress} "))
        spans.append(Span(year))
    elif data.document_type == "committee_report":
        # H.R. Rep. No. 118-123 (2026).
        label = data.report_number or data.title or "Report"
        spans.append(Span(f"{label} "))
        spans.append(Span(year))
    elif data.document_type == "court_opinion":
        spans.append(Span(data.title, italic=True))
        spans.append(Span(f" {year}"))
    elif data.document_type == "executive_order":
        spans.append(Span(f"{data.title} "))
        spans.append(Span(year))
    else:
        return None

    if data.url:
        spans.append(Span(f", {data.url}"))
    spans.append(Span("."))
    return _collapse(spans)


# --- Note form ----------------------------------------------------------


def note_spans(data: CitationInput, locator: str | None = None) -> list[Span]:
    """A Chicago note (footnote/endnote) entry, without its number."""
    legal = _legal_spans(data)
    if legal is not None:
        return legal

    if data.handle is not None or data.media_type == "post":
        return _social_post_spans(data, inverted=False)

    spans: list[Span] = []

    authors = format_authors_note(data.authors)
    if authors:
        spans.append(Span(f"{authors}, "))

    spans.extend(_title_spans(data, trailing=", "))

    if data.container_title:
        spans.append(Span(data.container_title, italic=_container_is_italic(data)))
        spans.append(Span(", "))

    if data.publisher and data.publisher != data.container_title:
        spans.append(Span(f"{data.publisher}, "))

    if data.edition:
        spans.append(Span(f"{data.edition}, "))

    published = format_full_date(data.published_date)
    if published:
        spans.append(Span(f"{published}, "))

    descriptor = _media_descriptor(data)
    if descriptor:
        spans.append(Span(f"{descriptor}, "))

    effective_locator = locator or data.locator
    if effective_locator:
        spans.append(Span(f"{effective_locator}, "))

    if _should_show_access_date(data):
        spans.append(Span(f"accessed {format_full_date(data.accessed)}, "))

    if data.url:
        spans.append(Span(f"{data.url}"))

    return _finish(spans)


# --- Bibliography form --------------------------------------------------


def bibliography_spans(data: CitationInput) -> list[Span]:
    """A Chicago bibliography entry."""
    legal = _legal_spans(data)
    if legal is not None:
        # Public documents are normally listed in notes only. Reproducing the
        # note form keeps the entry usable when a bibliography is requested.
        return legal

    if data.handle is not None or data.media_type == "post":
        return _social_post_spans(data, inverted=True)

    spans: list[Span] = []

    authors = format_authors_bibliography(data.authors)
    if authors:
        spans.append(Span(_sentence(authors)))

    spans.extend(_title_spans(data, trailing=". "))

    if data.container_title:
        spans.append(Span(data.container_title, italic=_container_is_italic(data)))
        spans.append(Span(". "))

    if data.publisher and data.publisher != data.container_title:
        spans.append(Span(f"{data.publisher}. "))

    if data.edition:
        spans.append(Span(f"{data.edition}. "))

    published = format_full_date(data.published_date)
    if published:
        spans.append(Span(f"{published}. "))

    descriptor = _media_descriptor(data)
    if descriptor:
        spans.append(Span(f"{descriptor.capitalize()}. "))

    if _should_show_access_date(data):
        spans.append(Span(f"Accessed {format_full_date(data.accessed)}. "))

    if data.url:
        spans.append(Span(f"{data.url}"))

    return _finish(spans)


# --- Author-date form ---------------------------------------------------


def author_date_citation_spans(
    data: CitationInput, locator: str | None = None
) -> list[Span]:
    """The in-text parenthetical, e.g. "(Doe 2026, 14)"."""
    name = author_date_name(data.authors)
    year = format_year(data.published_date)

    if not name:
        # With no author, Chicago falls back to the title.
        inner: list[Span] = []
        inner.extend(_title_spans(data, trailing=" "))
        inner.append(Span(year))
    else:
        inner = [Span(f"{name} {year}")]

    effective_locator = locator or data.locator
    if effective_locator:
        inner.append(Span(f", {effective_locator}"))

    return _collapse([Span("("), *inner, Span(")")])


def author_date_reference_spans(data: CitationInput) -> list[Span]:
    """A reference-list entry: the bibliography form with the year moved up."""
    legal = _legal_spans(data)
    if legal is not None:
        return legal

    if data.handle is not None or data.media_type == "post":
        return _social_post_spans(data, inverted=True, author_date=True)

    spans: list[Span] = []

    authors = format_authors_bibliography(data.authors)
    if authors:
        spans.append(Span(_sentence(authors)))

    spans.append(Span(_year_sentence(data.published_date)))

    spans.extend(_title_spans(data, trailing=". "))

    if data.container_title:
        spans.append(Span(data.container_title, italic=_container_is_italic(data)))
        spans.append(Span(". "))

    if data.publisher and data.publisher != data.container_title:
        spans.append(Span(f"{data.publisher}. "))

    published = format_full_date(data.published_date)
    if published:
        spans.append(Span(f"{published}. "))

    descriptor = _media_descriptor(data)
    if descriptor:
        spans.append(Span(f"{descriptor.capitalize()}. "))

    if _should_show_access_date(data):
        spans.append(Span(f"Accessed {format_full_date(data.accessed)}. "))

    if data.url:
        spans.append(Span(f"{data.url}"))

    return _finish(spans)


# --- Social media -------------------------------------------------------

PLATFORM_LABELS = {
    "x": "X",
    "twitter": "X",
    "bluesky": "Bluesky",
    "truth social": "Truth Social",
    "youtube": "YouTube",
    "facebook": "Facebook",
    "instagram": "Instagram",
}


def platform_label(platform: str | None) -> str:
    if not platform:
        return ""
    return PLATFORM_LABELS.get(platform.strip().lower(), platform.strip())


def extract_handle(url: str | None, platform: str | None) -> str | None:
    """Recover an @handle from a post URL where the platform's shape allows it."""
    if not url:
        return None
    patterns = (
        r"^https?://(?:www\.)?(?:x|twitter)\.com/([^/?#]+)/status/",
        r"^https?://(?:www\.)?bsky\.app/profile/([^/?#]+)/post/",
        r"^https?://(?:www\.)?truthsocial\.com/@([^/?#]+)/",
    )
    for pattern in patterns:
        match = re.match(pattern, url.strip())
        if match:
            handle = match.group(1)
            return handle if handle.startswith("@") else f"@{handle}"
    return None


def _truncate_post(text: str | None) -> str:
    if not text:
        return ""
    collapsed = " ".join(text.split())
    if len(collapsed) <= POST_QUOTE_LIMIT:
        return collapsed
    return collapsed[:POST_QUOTE_LIMIT].rstrip() + "..."


def _social_post_spans(
    data: CitationInput, *, inverted: bool, author_date: bool = False
) -> list[Span]:
    """Chicago 18th form for a social-media post.

    Jane Doe (@janedoe), "Post text," X, January 14, 2026, URL.
    """
    spans: list[Span] = []

    cleaned = _clean_authors(data.authors)
    if cleaned:
        name = _inverted_name(cleaned[0]) if inverted else _display_name(cleaned[0])
    else:
        name = ""

    if name:
        spans.append(Span(name))
        if data.handle:
            spans.append(Span(f" ({data.handle})"))
        spans.append(Span(". " if inverted else ", "))
    elif data.handle:
        spans.append(Span(f"{data.handle}"))
        spans.append(Span(". " if inverted else ", "))

    if author_date:
        spans.append(Span(_year_sentence(data.published_date)))

    quote = _truncate_post(data.post_text)
    if quote:
        # Chicago puts the separating punctuation inside the quotation marks,
        # replacing any terminal punctuation the post already ends with.
        stripped = quote if quote.endswith("...") else quote.rstrip(".,;:")
        spans.append(Span(f'"{stripped},"' if not inverted else f'"{stripped}."'))
        spans.append(Span(" "))

    label = platform_label(data.container_title)
    if label:
        spans.append(Span(f"{label} post" if not quote else label))
        spans.append(Span(". " if inverted else ", "))

    published = format_full_date(data.published_date)
    if published:
        spans.append(Span(f"{published}" + (". " if inverted else ", ")))

    if data.url:
        spans.append(Span(data.url))

    return _finish(spans)


# --- Assembly helpers ---------------------------------------------------


def _title_spans(data: CitationInput, trailing: str) -> list[Span]:
    if not data.title:
        return []
    if _titled_work_is_italic(data):
        return [Span(data.title, italic=True), Span(trailing)]
    # Chicago places the comma or period inside the closing quotation mark.
    punctuation = trailing.strip()
    remainder = trailing[len(punctuation):]
    return [Span(f'"{data.title}{punctuation}"{remainder}')]


def _collapse(spans: list[Span]) -> list[Span]:
    """Merge adjacent spans of the same style and drop empty ones."""
    merged: list[Span] = []
    for span in spans:
        if not span.text:
            continue
        if merged and merged[-1].italic == span.italic:
            merged[-1] = Span(merged[-1].text + span.text, span.italic)
        else:
            merged.append(span)
    return merged


def _finish(spans: list[Span]) -> list[Span]:
    """Trim trailing separators and end the entry with a single period."""
    merged = _collapse(spans)
    if not merged:
        return []
    last = merged[-1]
    trimmed = last.text.rstrip()
    while trimmed.endswith(",") or trimmed.endswith("."):
        trimmed = trimmed[:-1].rstrip()
    merged[-1] = Span(trimmed + ".", last.italic)
    return merged


# --- Adapters -----------------------------------------------------------


def from_source(source) -> CitationInput:
    """Build citation input from a Source ORM row."""
    return CitationInput(
        title=source.title or "",
        url=source.url,
        authors=source.authors or [],
        container_title=source.container_title,
        publisher=source.publisher,
        published_date=source.published_date,
        accessed=source.retrieved_at,
        locator=source.locator,
        edition=source.edition,
        media_type=source.media_type or "webpage",
        document_type=source.document_type,
        bill_number=source.bill_number,
        congress_number=source.congress_number,
        congress_session=source.congress_session,
        committee=source.committee,
        report_number=source.report_number,
    )


def _politician_author(name: str | None) -> list[dict]:
    """Split a display name into given/family for citation purposes.

    Politicians are stored as a single display name. The last whitespace-
    separated token is treated as the family name, which is right for the
    overwhelming majority of the names this tracker holds and degrades to a
    literal name when there is only one token.
    """
    if not name or not name.strip():
        return []
    parts = name.split()
    if len(parts) == 1:
        return [{"literal": parts[0]}]
    return [{"given": " ".join(parts[:-1]), "family": parts[-1]}]


def from_statement_post(statement) -> CitationInput:
    """Citation input for the tracked social media post itself."""
    politician = getattr(statement, "politician", None)
    return CitationInput(
        title="",
        url=statement.post_url,
        authors=_politician_author(getattr(politician, "name", None)),
        container_title=statement.post_platform,
        published_date=statement.post_date,
        media_type="post",
        handle=extract_handle(statement.post_url, statement.post_platform)
        or "",
        post_text=statement.post_content,
    )


def from_statement_page(statement, site_name: str, page_url: str) -> CitationInput:
    """Citation input for this tracker's own page about a statement."""
    return CitationInput(
        title=statement.title or "",
        url=page_url,
        authors=[],
        container_title=site_name,
        published_date=statement.post_date or statement.created_at,
        accessed=None,
        media_type="webpage",
    )


# --- Rendering the four forms ------------------------------------------


def render_all(data: CitationInput) -> dict:
    """Every supported form of one citation, as text plus renderable spans."""

    def rendered(spans: list[Span]) -> dict:
        return {"text": spans_to_text(spans), "spans": spans_to_dicts(spans)}

    return {
        "note": rendered(note_spans(data)),
        "bibliography": rendered(bibliography_spans(data)),
        "author_date_citation": rendered(author_date_citation_spans(data)),
        "author_date_reference": rendered(author_date_reference_spans(data)),
    }


# --- Export formats -----------------------------------------------------

_CSL_TYPES = {
    "webpage": "webpage",
    "article": "article-newspaper",
    "video": "motion_picture",
    "audio": "broadcast",
    "dataset": "dataset",
    "document": "report",
    "post": "post",
}

_CSL_DOCUMENT_TYPES = {
    "bill": "bill",
    "statute": "legislation",
    "hearing": "hearing",
    "committee_report": "report",
    "court_opinion": "legal_case",
    "executive_order": "legislation",
}


def csl_type(data: CitationInput) -> str:
    if data.document_type:
        return _CSL_DOCUMENT_TYPES.get(data.document_type, "report")
    return _CSL_TYPES.get(data.media_type, "webpage")


def _date_parts(value: datetime | None) -> dict | None:
    if value is None:
        return None
    return {"date-parts": [[value.year, value.month, value.day]]}


def to_csl_json(data: CitationInput, entry_id: str) -> dict:
    """A CSL-JSON entry, the interchange format Zotero and pandoc read."""
    entry: dict = {"id": entry_id, "type": csl_type(data)}

    if data.title:
        entry["title"] = data.title
    elif data.post_text:
        entry["title"] = _truncate_post(data.post_text)

    authors = _clean_authors(data.authors)
    if authors:
        entry["author"] = [
            {"literal": a["literal"]}
            if (a.get("literal") or "").strip()
            else {
                key: value
                for key, value in (
                    ("family", (a.get("family") or "").strip()),
                    ("given", (a.get("given") or "").strip()),
                )
                if value
            }
            for a in authors
        ]

    for key, value in (
        ("container-title", data.container_title),
        ("publisher", data.publisher),
        ("edition", data.edition),
        ("URL", data.url),
        ("locator", data.locator),
        ("number", data.bill_number or data.report_number),
    ):
        if value:
            entry[key] = value

    issued = _date_parts(data.published_date)
    if issued:
        entry["issued"] = issued
    accessed = _date_parts(data.accessed)
    if accessed:
        entry["accessed"] = accessed

    return entry


_BIBTEX_TYPES = {
    "webpage": "online",
    "article": "article",
    "video": "misc",
    "audio": "misc",
    "dataset": "misc",
    "document": "techreport",
    "post": "online",
}

# Characters BibTeX treats as markup rather than as text.
_BIBTEX_ESCAPES = {
    "\\": r"\textbackslash{}",
    "{": r"\{",
    "}": r"\}",
    "$": r"\$",
    "&": r"\&",
    "%": r"\%",
    "#": r"\#",
    "_": r"\_",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def bibtex_escape(value: str) -> str:
    return "".join(_BIBTEX_ESCAPES.get(char, char) for char in value)


def to_bibtex(data: CitationInput, entry_key: str) -> str:
    entry_type = (
        "techreport" if data.document_type else _BIBTEX_TYPES.get(data.media_type, "misc")
    )

    fields: list[tuple[str, str]] = []

    authors = _clean_authors(data.authors)
    if authors:
        rendered = " and ".join(
            a["literal"].strip()
            if (a.get("literal") or "").strip()
            else _inverted_name(a)
            for a in authors
        )
        fields.append(("author", rendered))

    title = data.title or _truncate_post(data.post_text)
    if title:
        fields.append(("title", title))

    if data.container_title:
        key = "journal" if data.media_type == "article" else "howpublished"
        fields.append((key, data.container_title))
    if data.publisher:
        fields.append(("institution" if entry_type == "techreport" else "publisher", data.publisher))
    if data.published_date:
        fields.append(("year", str(data.published_date.year)))
        fields.append(("month", data.published_date.strftime("%b").lower()))
    if data.url:
        fields.append(("url", data.url))
    if data.accessed:
        fields.append(("urldate", data.accessed.strftime("%Y-%m-%d")))
    if data.bill_number or data.report_number:
        fields.append(("number", data.bill_number or data.report_number))

    body = ",\n".join(
        f"  {name} = {{{bibtex_escape(value)}}}" for name, value in fields
    )
    return f"@{entry_type}{{{entry_key},\n{body}\n}}"
