"""Tests for Chicago Manual of Style citation formatting (18th edition)."""

from datetime import datetime

import pytest

from fastapi.testclient import TestClient

from app import citations
from app.citations import (
    CitationInput,
    author_date_citation_spans,
    author_date_reference_spans,
    bibliography_spans,
    note_spans,
    spans_to_dicts,
    spans_to_text,
)


from app.main import app
from tests.conftest import TEST_ADMIN_PASSWORD


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def auth(client):
    response = client.post(
        "/api/auth/login", json={"password": TEST_ADMIN_PASSWORD}
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['token']}"}


def note(data, locator=None) -> str:
    return spans_to_text(note_spans(data, locator))


def bibliography(data) -> str:
    return spans_to_text(bibliography_spans(data))


def parenthetical(data, locator=None) -> str:
    return spans_to_text(author_date_citation_spans(data, locator))


def reference(data) -> str:
    return spans_to_text(author_date_reference_spans(data))


ARTICLE = CitationInput(
    title="Senator Doe Reverses Course on Housing",
    url="https://www.nytimes.com/2026/01/14/housing.html",
    authors=[{"given": "Maria", "family": "Reyes"}],
    container_title="New York Times",
    published_date=datetime(2026, 1, 14),
    media_type="article",
)


# --- News article -------------------------------------------------------


def test_article_note():
    assert note(ARTICLE) == (
        'Maria Reyes, "Senator Doe Reverses Course on Housing," New York Times, '
        "January 14, 2026, https://www.nytimes.com/2026/01/14/housing.html."
    )


def test_article_bibliography_inverts_the_author():
    assert bibliography(ARTICLE) == (
        'Reyes, Maria. "Senator Doe Reverses Course on Housing." New York Times. '
        "January 14, 2026. https://www.nytimes.com/2026/01/14/housing.html."
    )


def test_article_parenthetical():
    assert parenthetical(ARTICLE) == "(Reyes 2026)"


def test_article_reference_moves_the_year_forward():
    assert reference(ARTICLE).startswith('Reyes, Maria. 2026. "Senator Doe')


def test_periodical_titles_are_italicised():
    spans = spans_to_dicts(note_spans(ARTICLE))
    italic = [s["text"] for s in spans if s["italic"]]
    assert italic == ["New York Times"]


def test_website_names_are_not_italicised():
    """Chicago sets plain website names in roman, unlike periodicals."""
    data = CitationInput(
        title="About",
        url="https://example.gov/about",
        container_title="Example Agency",
        media_type="webpage",
        accessed=datetime(2026, 2, 1),
    )
    assert all(not span["italic"] for span in spans_to_dicts(note_spans(data)))


# --- Punctuation --------------------------------------------------------


def test_comma_and_period_sit_inside_the_closing_quotation_mark():
    assert '"Senator Doe Reverses Course on Housing,"' in note(ARTICLE)
    assert '"Senator Doe Reverses Course on Housing."' in bibliography(ARTICLE)


def test_entries_end_with_exactly_one_period():
    for rendered in (note(ARTICLE), bibliography(ARTICLE), reference(ARTICLE)):
        assert rendered.endswith(".")
        assert not rendered.endswith("..")


def test_no_double_period_when_the_date_is_unknown():
    """"n.d." already carries a period; a second one must not be appended."""
    data = CitationInput(title="Undated Page", url="https://e.test/x", media_type="webpage")
    assert "n.d.." not in reference(data)
    assert reference(data).startswith("n.d. ")


# --- Authors ------------------------------------------------------------


def test_two_authors_are_joined_with_and():
    data = CitationInput(
        title="T",
        url="https://e.test/t",
        authors=[
            {"given": "Ann", "family": "Adams"},
            {"given": "Ben", "family": "Brown"},
        ],
        published_date=datetime(2026, 1, 1),
    )
    assert note(data).startswith("Ann Adams and Ben Brown, ")
    assert bibliography(data).startswith("Adams, Ann, and Ben Brown. ")


def test_three_authors_use_a_serial_comma():
    data = CitationInput(
        title="T",
        url="https://e.test/t",
        authors=[
            {"given": "Ann", "family": "Adams"},
            {"given": "Ben", "family": "Brown"},
            {"given": "Cal", "family": "Clark"},
        ],
    )
    assert note(data).startswith("Ann Adams, Ben Brown, and Cal Clark, ")


def test_a_note_shortens_four_or_more_authors_to_et_al():
    data = CitationInput(
        title="T",
        url="https://e.test/t",
        authors=[
            {"given": "Ann", "family": "Adams"},
            {"given": "Ben", "family": "Brown"},
            {"given": "Cal", "family": "Clark"},
            {"given": "Dee", "family": "Davis"},
        ],
    )
    assert note(data).startswith("Ann Adams et al., ")
    # The bibliography still lists them all.
    assert "Dee Davis" in bibliography(data)


def test_bibliography_lists_all_authors_up_to_ten():
    authors = [{"given": f"A{i}", "family": f"F{i}"} for i in range(10)]
    data = CitationInput(title="T", url="https://e.test/t", authors=authors)
    assert "A9 F9" in bibliography(data)
    assert "et al." not in bibliography(data)


def test_bibliography_lists_the_first_seven_beyond_ten_authors():
    """Chicago: more than ten authors, list the first seven then "et al."."""
    authors = [{"given": f"A{i}", "family": f"F{i}"} for i in range(12)]
    data = CitationInput(title="T", url="https://e.test/t", authors=authors)
    rendered = bibliography(data)
    assert "A6 F6, et al." in rendered
    assert "A7 F7" not in rendered
    assert "et al.." not in rendered


def test_corporate_authors_are_never_inverted():
    data = CitationInput(
        title="Annual Report",
        url="https://hud.gov/r.pdf",
        authors=[{"literal": "U.S. Department of Housing and Urban Development"}],
        media_type="document",
    )
    assert bibliography(data).startswith(
        "U.S. Department of Housing and Urban Development. "
    )


def test_parenthetical_uses_surname_only():
    data = CitationInput(
        authors=[{"given": "Maria", "family": "Reyes"}],
        title="T",
        published_date=datetime(2026, 1, 1),
    )
    assert parenthetical(data) == "(Reyes 2026)"


def test_parenthetical_shortens_three_or_more_authors():
    data = CitationInput(
        authors=[
            {"given": "Ann", "family": "Adams"},
            {"given": "Ben", "family": "Brown"},
            {"given": "Cal", "family": "Clark"},
        ],
        title="T",
        published_date=datetime(2026, 1, 1),
    )
    assert parenthetical(data) == "(Adams et al. 2026)"


def test_parenthetical_falls_back_to_the_title_without_an_author():
    data = CitationInput(title="Untitled Study", published_date=datetime(2026, 1, 1))
    assert parenthetical(data) == '("Untitled Study" 2026)'


def test_parenthetical_includes_a_locator():
    assert parenthetical(ARTICLE, "14") == "(Reyes 2026, 14)"


# --- Access dates (18th edition rule) -----------------------------------


def test_access_date_is_shown_only_when_there_is_no_publication_date():
    undated = CitationInput(
        title="Page", url="https://e.test/p", accessed=datetime(2026, 2, 1)
    )
    assert "accessed February 1, 2026" in note(undated)

    dated = CitationInput(
        title="Page",
        url="https://e.test/p",
        published_date=datetime(2026, 1, 14),
        accessed=datetime(2026, 2, 1),
    )
    assert "accessed" not in note(dated)


# --- Standalone works ---------------------------------------------------


def test_standalone_documents_take_italics_not_quotation_marks():
    data = CitationInput(
        title="Annual Housing Report",
        url="https://hud.gov/r.pdf",
        media_type="document",
        published_date=datetime(2026, 3, 1),
    )
    spans = spans_to_dicts(note_spans(data))
    assert any(s["italic"] and s["text"] == "Annual Housing Report" for s in spans)
    assert '"Annual Housing Report' not in note(data)


# --- Legislative and legal material -------------------------------------


def test_bill_form():
    data = CitationInput(
        title="Fair Housing Improvement Act of 2026",
        url="https://www.congress.gov/bill/hr1234",
        document_type="bill",
        bill_number="H.R. 1234",
        congress_number=118,
        congress_session="2nd",
        published_date=datetime(2026, 1, 14),
        media_type="document",
    )
    assert note(data) == (
        "Fair Housing Improvement Act of 2026, H.R. 1234, 118th Cong., 2nd sess. "
        "(2026), https://www.congress.gov/bill/hr1234."
    )


def test_bill_without_a_session():
    data = CitationInput(
        title="Some Act",
        document_type="bill",
        bill_number="S. 99",
        congress_number=119,
        published_date=datetime(2026, 5, 1),
        media_type="document",
    )
    assert note(data) == "Some Act, S. 99, 119th Cong. (2026)."


def test_hearing_form():
    data = CitationInput(
        title="Oversight of Federal Housing Programs",
        document_type="hearing",
        committee="Committee on Financial Services",
        congress_number=118,
        published_date=datetime(2026, 2, 3),
        media_type="document",
    )
    assert note(data) == (
        "Oversight of Federal Housing Programs: Hearing before the Committee on "
        "Financial Services, 118th Cong. (2026)."
    )


def test_committee_report_form():
    data = CitationInput(
        title="Report on H.R. 1234",
        document_type="committee_report",
        report_number="H.R. Rep. No. 118-123",
        published_date=datetime(2026, 4, 1),
        media_type="document",
    )
    assert note(data) == "H.R. Rep. No. 118-123 (2026)."


@pytest.mark.parametrize("congress,expected", [(1, "1st"), (2, "2nd"), (3, "3rd"), (4, "4th"), (11, "11th"), (12, "12th"), (13, "13th"), (21, "21st"), (118, "118th")])
def test_congress_numbers_take_the_right_ordinal(congress, expected):
    data = CitationInput(
        document_type="bill", bill_number="H.R. 1", congress_number=congress
    )
    assert f"{expected} Cong." in note(data)


def test_public_documents_ignore_media_specific_formatting():
    """A document_type wins over media_type, so a bill is never a web page."""
    data = CitationInput(
        title="Some Act",
        document_type="bill",
        bill_number="H.R. 1",
        media_type="webpage",
        container_title="Congress.gov",
    )
    assert "Congress.gov" not in note(data)


# --- Social media posts -------------------------------------------------


POST = CitationInput(
    url="https://x.com/janedoe/status/1",
    authors=[{"given": "Jane", "family": "Doe"}],
    handle="@janedoe",
    post_text="I have always supported this bill and will continue to do so.",
    container_title="X",
    published_date=datetime(2026, 1, 14),
    media_type="post",
)


def test_post_note_includes_the_handle_and_platform():
    assert note(POST) == (
        'Jane Doe (@janedoe), "I have always supported this bill and will continue '
        'to do so," X, January 14, 2026, https://x.com/janedoe/status/1.'
    )


def test_post_bibliography_inverts_the_name():
    assert bibliography(POST).startswith("Doe, Jane (@janedoe). ")


def test_post_text_is_truncated():
    long_post = CitationInput(
        url="https://x.com/j/status/1",
        authors=[{"given": "Jane", "family": "Doe"}],
        post_text="word " * 100,
        container_title="X",
        media_type="post",
    )
    assert "..." in note(long_post)
    assert len(note(long_post)) < 400


def test_post_whitespace_is_collapsed():
    data = CitationInput(
        url="https://x.com/j/status/1",
        post_text="line one\n\n  line two",
        container_title="X",
        media_type="post",
    )
    assert "line one line two" in note(data)


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://x.com/janedoe/status/1", "@janedoe"),
        ("https://twitter.com/janedoe/status/1", "@janedoe"),
        ("https://bsky.app/profile/jane.bsky.social/post/abc", "@jane.bsky.social"),
        ("https://truthsocial.com/@janedoe/1", "@janedoe"),
        ("https://www.youtube.com/watch?v=abc", None),
        (None, None),
    ],
)
def test_handles_are_recovered_from_post_urls(url, expected):
    assert citations.extract_handle(url, None) == expected


@pytest.mark.parametrize(
    ("platform", "label"),
    [("x", "X"), ("twitter", "X"), ("Bluesky", "Bluesky"), ("truth social", "Truth Social")],
)
def test_platform_labels(platform, label):
    assert citations.platform_label(platform) == label


# --- Rendering ----------------------------------------------------------


def test_spans_carry_no_markup():
    """The API emits structured spans, never HTML, so nothing needs escaping."""
    data = CitationInput(
        title="Bread & Butter <script>",
        url="https://e.test/x",
        container_title="Journal & Review",
        media_type="article",
    )
    spans = spans_to_dicts(note_spans(data))
    combined = "".join(span["text"] for span in spans)
    assert "<script>" in combined
    assert "&amp;" not in combined
    assert all(set(span) == {"text", "italic"} for span in spans)


def test_render_all_returns_every_form():
    rendered = citations.render_all(ARTICLE)
    assert set(rendered) == {
        "note",
        "bibliography",
        "author_date_citation",
        "author_date_reference",
    }
    for form in rendered.values():
        assert form["text"]
        assert form["spans"]


# --- Export formats -----------------------------------------------------


def test_csl_json_entry():
    entry = citations.to_csl_json(ARTICLE, "src-1")
    assert entry["id"] == "src-1"
    assert entry["type"] == "article-newspaper"
    assert entry["author"] == [{"family": "Reyes", "given": "Maria"}]
    assert entry["container-title"] == "New York Times"
    assert entry["issued"] == {"date-parts": [[2026, 1, 14]]}


def test_csl_json_uses_literal_for_corporate_authors():
    data = CitationInput(title="T", authors=[{"literal": "U.S. Congress"}])
    assert citations.to_csl_json(data, "x")["author"] == [{"literal": "U.S. Congress"}]


@pytest.mark.parametrize(
    ("document_type", "media_type", "expected"),
    [
        (None, "webpage", "webpage"),
        (None, "article", "article-newspaper"),
        (None, "video", "motion_picture"),
        (None, "dataset", "dataset"),
        ("bill", "document", "bill"),
        ("hearing", "document", "hearing"),
        ("court_opinion", "document", "legal_case"),
    ],
)
def test_csl_types(document_type, media_type, expected):
    data = CitationInput(document_type=document_type, media_type=media_type)
    assert citations.csl_type(data) == expected


def test_bibtex_entry():
    entry = citations.to_bibtex(ARTICLE, "src-1")
    assert entry.startswith("@article{src-1,")
    assert "author = {Reyes, Maria}" in entry
    assert "journal = {New York Times}" in entry
    assert "year = {2026}" in entry
    assert entry.endswith("}")


def test_bibtex_joins_authors_with_and():
    data = CitationInput(
        title="T",
        authors=[
            {"given": "Ann", "family": "Adams"},
            {"given": "Ben", "family": "Brown"},
        ],
    )
    assert "author = {Adams, Ann and Brown, Ben}" in citations.to_bibtex(data, "k")


def test_bibtex_escapes_special_characters():
    data = CitationInput(title="Cost & Benefit: 50% of $5_x")
    entry = citations.to_bibtex(data, "k")
    assert r"\&" in entry
    assert r"\%" in entry
    assert r"\$" in entry
    assert r"\_" in entry


def test_bibtex_uses_techreport_for_public_documents():
    data = CitationInput(title="Some Act", document_type="bill", bill_number="H.R. 1")
    assert citations.to_bibtex(data, "k").startswith("@techreport{")


# --- Robustness ---------------------------------------------------------


def test_an_empty_source_does_not_crash():
    data = CitationInput()
    for renderer in (note, bibliography, parenthetical, reference):
        assert isinstance(renderer(data), str)


def test_blank_author_entries_are_ignored():
    data = CitationInput(
        title="T",
        url="https://e.test/t",
        authors=[{"given": "", "family": ""}, {"given": "Ann", "family": "Adams"}],
    )
    assert note(data).startswith("Ann Adams, ")


def test_authors_may_be_none():
    data = CitationInput(title="T", url="https://e.test/t", authors=None)
    assert note(data).startswith('"T,"')


# --- API surface --------------------------------------------------------


class TestCitationEndpoints:
    """The citation endpoints, exercised through the running application."""

    @staticmethod
    def _statement(client, auth):
        politician = client.post(
            "/api/politicians",
            headers=auth,
            json={"name": "Jane Doe", "party": "Independent", "office": "Senate"},
        ).json()
        import uuid

        issue = client.post(
            "/api/issues",
            headers=auth,
            json={"name": f"Housing {uuid.uuid4().hex[:6]}"},
        ).json()
        response = client.post(
            "/api/statements",
            headers=auth,
            json={
                "politician_id": politician["id"],
                "issue_ids": [issue["id"]],
                "title": "Vote on H.R. 1234",
                "analysis": "She voted against it[^1].",
                "post_url": "https://x.com/janedoe/status/1",
                "post_platform": "X",
                "post_content": "I have always supported this bill.",
                "post_date": "2026-01-14T00:00:00",
                "sources": [
                    {
                        "source_type": "analysis",
                        "title": "Senator Doe Reverses Course",
                        "url": "https://www.nytimes.com/2026/01/14/housing.html",
                        "media_type": "article",
                        "container_title": "New York Times",
                        "authors": [{"given": "Maria", "family": "Reyes"}],
                        "published_date": "2026-01-14T00:00:00",
                    },
                    {
                        "source_type": "post",
                        "title": "Fair Housing Improvement Act of 2026",
                        "url": "https://www.congress.gov/bill/hr1234",
                        "media_type": "document",
                        "document_type": "bill",
                        "bill_number": "H.R. 1234",
                        "congress_number": 118,
                        "congress_session": "2nd",
                        "published_date": "2026-01-14T00:00:00",
                    },
                ],
            },
        )
        assert response.status_code == 201, response.text
        return response.json()

    def test_sources_carry_rendered_citations(self, client, auth):
        statement = self._statement(client, auth)
        source = next(
            s for s in statement["sources"] if s["media_type"] == "article"
        )
        assert source["citations"]["note"]["text"].startswith("Maria Reyes, ")
        assert source["citations"]["bibliography"]["text"].startswith("Reyes, Maria. ")
        assert source["citations"]["author_date_citation"]["text"] == "(Reyes 2026)"
        assert any(span["italic"] for span in source["citations"]["note"]["spans"])

    def test_citation_fields_round_trip(self, client, auth):
        statement = self._statement(client, auth)
        bill = next(s for s in statement["sources"] if s["document_type"] == "bill")
        assert bill["bill_number"] == "H.R. 1234"
        assert bill["congress_number"] == 118
        assert bill["congress_session"] == "2nd"
        article = next(s for s in statement["sources"] if s["media_type"] == "article")
        assert article["authors"] == [{"given": "Maria", "family": "Reyes", "literal": None}]
        assert article["container_title"] == "New York Times"

    def test_citations_endpoint_covers_sources_post_and_page(self, client, auth):
        statement = self._statement(client, auth)
        body = client.get(f"/api/statements/{statement['id']}/citations").json()

        assert body["default_style"] in ("notes-bibliography", "author-date")
        assert len(body["sources"]) == 2
        assert "Jane Doe (@janedoe)" in body["post"]["note"]["text"]
        assert "I have always supported this bill" in body["post"]["note"]["text"]
        assert statement["title"] in body["page"]["note"]["text"]
        assert f"/statements/{statement['id']}" in body["page"]["note"]["text"]

    def test_citations_endpoint_404s_for_an_unknown_statement(self, client):
        assert client.get("/api/statements/999999/citations").status_code == 404

    def test_citations_are_public(self, client, auth):
        """Readers need citations; they must not require an admin session."""
        statement = self._statement(client, auth)
        assert client.get(f"/api/statements/{statement['id']}/citations").status_code == 200

    def test_csl_json_export(self, client, auth):
        statement = self._statement(client, auth)
        response = client.get(f"/api/statements/{statement['id']}/citations.json")
        assert response.status_code == 200
        assert "attachment" in response.headers["content-disposition"]

        entries = response.json()
        assert len(entries) == 4  # two sources, the post, the page
        types = {entry["type"] for entry in entries}
        assert "article-newspaper" in types
        assert "bill" in types
        assert all(entry["id"] for entry in entries)

    def test_bibtex_export(self, client, auth):
        statement = self._statement(client, auth)
        response = client.get(f"/api/statements/{statement['id']}/citations.bib")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/plain")
        body = response.text
        assert body.count("@") >= 4
        assert "author = {Reyes, Maria}" in body
        assert "journal = {New York Times}" in body

    def test_config_endpoint_reports_the_default_style(self, client):
        body = client.get("/api/config").json()
        assert body["citation_style"] in body["citation_styles"]
        assert body["site_name"]


def test_invalid_document_type_is_rejected(client, auth):
    politician = client.post(
        "/api/politicians",
        headers=auth,
        json={"name": "X", "party": "I", "office": "Senate"},
    ).json()
    import uuid

    issue = client.post(
        "/api/issues", headers=auth, json={"name": f"I{uuid.uuid4().hex[:6]}"}
    ).json()
    response = client.post(
        "/api/statements",
        headers=auth,
        json={
            "politician_id": politician["id"],
            "issue_ids": [issue["id"]],
            "title": "T",
            "analysis": "A",
            "post_url": "https://x.com/a/status/1",
            "post_platform": "X",
            "sources": [
                {
                    "source_type": "analysis",
                    "title": "T",
                    "url": "https://e.test/t",
                    "document_type": "treaty",
                }
            ],
        },
    )
    assert response.status_code == 422


@pytest.mark.parametrize(
    "authors",
    [
        [{"given": "", "family": "", "literal": ""}],
        [{"given": "Jane", "family": "Doe", "literal": "U.S. Congress"}],
    ],
)
def test_invalid_author_shapes_are_rejected(client, auth, authors):
    politician = client.post(
        "/api/politicians",
        headers=auth,
        json={"name": "X", "party": "I", "office": "Senate"},
    ).json()
    import uuid

    issue = client.post(
        "/api/issues", headers=auth, json={"name": f"I{uuid.uuid4().hex[:6]}"}
    ).json()
    response = client.post(
        "/api/statements",
        headers=auth,
        json={
            "politician_id": politician["id"],
            "issue_ids": [issue["id"]],
            "title": "T",
            "analysis": "A",
            "post_url": "https://x.com/a/status/1",
            "post_platform": "X",
            "sources": [
                {
                    "source_type": "analysis",
                    "title": "T",
                    "url": "https://e.test/t",
                    "authors": authors,
                }
            ],
        },
    )
    assert response.status_code == 422


# --- Shortened titles ---------------------------------------------------


def test_parenthetical_shortens_a_long_title_standing_in_for_an_author():
    data = CitationInput(
        title="Fair Housing Improvement and Tenant Protection Act of 2026",
        published_date=datetime(2026, 1, 1),
        document_type="bill",
        media_type="document",
    )
    assert parenthetical(data) == "(Fair Housing Improvement and 2026)"


def test_shortened_titles_drop_a_leading_article():
    assert citations.shorten_title("The Fair Housing Improvement Act of 2026") == (
        "Fair Housing Improvement Act"
    )


def test_a_short_title_is_left_alone():
    assert citations.shorten_title("Housing Report") == "Housing Report"


def test_shortened_titles_keep_the_style_of_the_full_title():
    """A standalone work stays italic when shortened; a web page keeps quotes."""
    document = CitationInput(
        title="A Very Long Standalone Report Title Here",
        media_type="document",
        published_date=datetime(2026, 1, 1),
    )
    spans = spans_to_dicts(author_date_citation_spans(document))
    assert any(span["italic"] for span in spans)

    webpage = CitationInput(
        title="A Very Long Web Page Title Here",
        media_type="webpage",
        published_date=datetime(2026, 1, 1),
    )
    assert '"' in parenthetical(webpage)
