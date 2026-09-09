# Politician Position Tracker

A self-hosted web application for tracking and analyzing politician statements on social media. Link to posts on X (Twitter), Bluesky, Truth Social, or YouTube, write analysis with sourced citations, and organize everything by politician and issue.

Built as a single-container Docker application with a FastAPI backend serving a React SPA frontend, backed by SQLite.

---

## Features

- **Timeline Feed** -- Browse all tracked statements in a chronological timeline with search, filters, and sort options
- **Politician Profiles** -- View all statements from a specific politician with photo, party, office, and state
- **Issue Tracking** -- Tag statements with multiple issues and browse all statements for a given issue
- **Social Media Embeds** -- Native embeds for X/Twitter, YouTube, and Bluesky posts; styled blockquotes for Truth Social
- **Primary Source Embeds** -- Attach primary sources with publisher, date, verbatim excerpt and locator (page, section or timestamp); documents, video and audio embed inline behind a click-to-load control
- **Chicago Citations** -- Every source, the tracked post, and the page itself formatted to the Chicago Manual of Style (18th ed.), in both Notes-Bibliography and Author-Date, with a per-reader style toggle
- **Bibliography and Export** -- A reference list on every statement, copy-to-clipboard per entry, and BibTeX / CSL-JSON export for Zotero and pandoc
- **Inline Citations** -- Cite a source from the analysis body with `[^1]`; the marker links to that source's card
- **Link Rot Protection** -- Record an archive URL, archive date and retrieval date alongside every source
- **Sourced Analysis** -- Write analysis with Markdown formatting and attach separate citation lists for the original post and your analysis
- **Screenshot Backup** -- Upload screenshots of posts as a backup in case the original is deleted
- **Admin Panel** -- Password-protected admin dashboard for managing all data with full CRUD operations
- **Import/Export Backup** -- Export all data as JSON for backup, import from a backup file to restore or migrate
- **Dark Mode** -- Light and dark themes with system preference detection and manual toggle
- **Share Buttons** -- Share statements via X, Facebook, email, or copy link
- **Cascade Delete Warnings** -- Deleting a politician warns how many statements will be affected
- **Toast Notifications** -- Success and error feedback for all admin operations
- **SEO / Open Graph** -- Meta tags for search engines and social media link previews
- **Docker Healthcheck** -- Built-in health endpoint for container orchestration
- **Unraid Support** -- Community Applications template for one-click Unraid installation
- **Responsive Design** -- Mobile-friendly layout with collapsible navigation

---

## Screenshots

[Screenshot needed: Timeline page showing statement cards with search and filter controls]

[Screenshot needed: Politician detail page with profile header and statement list]

[Screenshot needed: Statement detail page with YouTube embed and markdown analysis]

[Screenshot needed: Admin dashboard showing tables for politicians, issues, and statements]

[Screenshot needed: Statement form with issue toggle buttons and screenshot upload]

[Screenshot needed: Dark mode comparison showing the same page in light and dark themes]

---

## Quick Start

### Docker Compose (recommended)

```bash
git clone https://github.com/thegspiro/politician-position-tracker.git
cd politician-position-tracker

# Both credentials are required; the app will not start without them.
cat > .env <<EOF
ADMIN_PASSWORD=$(openssl rand -base64 24)
SECRET_KEY=$(openssl rand -base64 32)
EOF

docker compose up -d
```

The application will be available at **http://localhost:9847**.

### Docker Run

```bash
docker build -t politician-tracker .

docker run -d \
  --name politician-tracker \
  -p 9847:8000 \
  -v politician-tracker-data:/app/data \
  -e ADMIN_PASSWORD="$(openssl rand -base64 24)" \
  -e SECRET_KEY="$(openssl rand -base64 32)" \
  politician-tracker
```

### Local Development

**Backend:**

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Outside Docker the default upload directory (`/app/data/uploads`) is usually not
writable. Set `UPLOAD_DIR` to a local path when running from a source checkout:

```bash
UPLOAD_DIR=./data/uploads uvicorn app.main:app --reload --port 8000
```

The schema is managed by Alembic, so apply migrations before the first run (and
after pulling changes that add any):

```bash
cd backend
alembic upgrade head
```

**Frontend:**

```bash
cd frontend
npm install
npm run dev
```

The frontend dev server runs on `http://localhost:5173` and proxies API requests to `http://localhost:8000`.

**Backend tests:**

```bash
cd backend
pip install -r requirements-dev.txt
python -m pytest tests/ -q
```

**Frontend tests:**

```bash
cd frontend
npm test
```

---

## Working With Primary Sources

Each statement carries two source lists: **Post Sources** (primary sources for
the original post) and **Analysis Sources** (primary sources supporting your
analysis). Beyond a title and URL, each source records:

| Field | Purpose |
|---|---|
| Media type | `webpage`, `document`, `video`, `audio`, `article` or `dataset`. Selects how the source is embedded |
| Publisher / Published date | Provenance, e.g. "Congress.gov", 14 Jan 2026 |
| Excerpt | The verbatim passage being relied on, shown as a pull quote |
| Locator | Where the excerpt lives: `p. 14`, `sec. 203`, `01:23:45` |
| Archive URL / Archived on | A snapshot to fall back on when the original link rots |
| Retrieved on | When the original was last confirmed to say what is quoted |

**Embedding.** A `video` source pointing at YouTube embeds inline, and a
timestamp locator such as `01:23:45` starts playback at that point. A `document`
source whose URL ends in `.pdf` offers an inline preview. An `audio` source
pointing directly at an audio file gets a player. Third-party frames only load
when the reader clicks, so the page does not call out to every embedded host on
load, and a publisher that refuses framing degrades to a plain link.

**Citations.** Write `[^1]` in the analysis to cite source `[1]`. Numbering runs
across both lists combined -- post sources first, then analysis sources -- and
each source card in the admin form shows the number to use. Rearrange sources
with the arrow buttons; the numbers follow. Each marker renders as a link to
that source's card.

**Stable links.** Every source has a `uid` and its card is addressable as
`#source-<uid>`. Editing a statement updates sources in place rather than
recreating them, so those links survive edits.

---

## Citations

Sources are formatted to the **Chicago Manual of Style, 18th edition**, in both
of Chicago's systems:

| System | At the point of citation | In the list |
|---|---|---|
| Notes-Bibliography (default) | A note: `Maria Reyes, "Senator Doe Reverses Course," New York Times, January 14, 2026, https://...` | Bibliography, lead author inverted |
| Author-Date | A parenthetical: `(Reyes 2026, 14)` | References, year moved forward |

`CITATION_STYLE` sets the site default; readers can switch with the toggle on
any statement page, and their choice is remembered.

### What each field feeds

| Field | Effect on the citation |
|---|---|
| Authors | Structured given/family names, or an organisation. Chicago inverts only the lead author in a bibliography, and never inverts an organisation |
| Container title | The publication the source sits in. Italicised for a periodical, roman for a plain website name |
| Publisher, edition | Included when they differ from the container |
| Published date | The date in the citation and the year in author-date forms |
| Retrieved on | Shown as an access date **only when the source has no publication date**, per the 18th edition |
| Locator | The page, section or timestamp: `p. 14`, `sec. 203`, `01:23:45` |
| Document type | Selects Chicago's public-document form for bills, hearings, committee reports, court opinions and executive orders |

A source with only a title and URL still cites correctly; the extra fields add
precision rather than being required.

### The post and the page

The tracked social media post is cited in Chicago's social-media form, with the
`@handle` recovered from the post URL for X, Bluesky and Truth Social. Each
statement page also carries a **Cite this page** block for the tracker entry
itself, using `SITE_NAME` and the page's own URL.

### Export

Every statement offers its whole bibliography as BibTeX or CSL-JSON:

```
GET /api/statements/{id}/citations       # all forms, as JSON
GET /api/statements/{id}/citations.bib   # BibTeX
GET /api/statements/{id}/citations.json  # CSL-JSON, for Zotero and pandoc
```

Citations are rendered on the server, so an exported file and the page always
agree.

### Scope

This covers the source types the tracker records. Chicago defers to Bluebook
conventions for much legal material and carries far more special cases than are
implemented, so an unusual source may need an editor's hand. Where the 18th
edition differs from the 17th in a way that changes output -- access dates,
most notably -- `backend/app/citations.py` notes it at the point it applies.

---

## Database Migrations

The schema is owned by [Alembic](https://alembic.sqlalchemy.org/). The container
entrypoint runs `alembic upgrade head` on every start, before the server binds,
so a `docker compose pull && docker compose up -d` applies pending migrations
automatically. Nothing needs to be run by hand for a normal upgrade.

Working with migrations locally, from `backend/`:

```bash
alembic upgrade head        # apply everything pending
alembic current             # show the revision the database is on
alembic history             # list the migration chain
alembic downgrade -1        # roll back one revision
```

To add a migration after changing `app/models.py`:

```bash
alembic revision --autogenerate -m "describe the change"
```

Review the generated file before committing it -- autogenerate does not detect
every change, and column additions to a populated table usually need an explicit
backfill (see `migrations/versions/0002_primary_source_fields.py` for the
add-nullable, backfill, then set-NOT-NULL pattern).

`DATABASE_URL` drives both the application and the migrations, so the same
commands work against SQLite and MySQL without edits.

---

## Unraid Installation

### One-Line Terminal Install

Open the Unraid terminal and run:

```bash
curl -sSL https://raw.githubusercontent.com/thegspiro/politician-position-tracker/main/install-unraid.sh | bash
```

To customize the port or admin password:

```bash
PORT=9847 ADMIN_PASSWORD=mysecurepassword curl -sSL https://raw.githubusercontent.com/thegspiro/politician-position-tracker/main/install-unraid.sh | bash
```

This clones the repo, builds the Docker image locally, creates the data directory, and starts the container.

### Via Community Applications

1. In the Unraid web UI, go to **Apps** (Community Applications)
2. Search for **Politician Tracker**
3. Click **Install**
4. Configure the required variables:
   - **Admin Password**: Set a secure password for the admin panel
   - **Secret Key**: Set a random string for token generation
5. Click **Apply**

### Manual Template Install

1. Copy the `unraid-template.xml` file to your Unraid flash drive at `/boot/config/plugins/dockerMan/templates-user/`
2. In the Unraid Docker tab, click **Add Container** and select the Politician Tracker template
3. Configure environment variables and click **Apply**

### Unraid Data Path

By default, data is stored at `/mnt/user/appdata/politician-tracker` on the Unraid host. This directory contains the SQLite database and uploaded screenshot files.

---

## Environment Variables

| Variable | Default | Required | Description |
|---|---|---|---|
| `ADMIN_PASSWORD` | *(none)* | **Yes** | Password for the admin panel. The application refuses to start if this is unset or `changeme`. |
| `SECRET_KEY` | *(none)* | **Yes** | Signs admin session tokens. Use a long random string: `openssl rand -base64 32`. The application refuses to start on a published default. |
| `DATABASE_URL` | `sqlite:////app/data/politician_tracker.db` | No | SQLAlchemy database connection string. Defaults to SQLite in the data volume. |
| `SESSION_TTL_HOURS` | `12` | No | How long an admin session lasts before re-login is required. |
| `LOGIN_MAX_ATTEMPTS` | `5` | No | Failed logins allowed per client address before further attempts are refused. |
| `LOGIN_WINDOW_SECONDS` | `900` | No | Window over which failed logins are counted. |
| `MAX_UPLOAD_MB` | `5` | No | Largest accepted upload. |
| `UPLOAD_DIR` | `/app/data/uploads` | No | Where uploads are stored. Set this when running outside Docker. |
| `CONTENT_SECURITY_POLICY` | *(built-in)* | No | Overrides the default CSP. Set to an empty string to disable it while diagnosing a blocked embed. |
| `SITE_NAME` | `Politician Tracker` | No | Site name used in the "cite this page" citation. |
| `SITE_URL` | *(derived from the request)* | No | Public base URL, used in the "cite this page" citation. Set this when behind a reverse proxy that does not forward the original host. |
| `CITATION_STYLE` | `notes-bibliography` | No | Default Chicago system: `notes-bibliography` or `author-date`. Readers can override it per browser. |
| `CORS_ORIGINS` | *(empty)* | No | Comma-separated origins allowed to make credentialed API requests. Leave empty in production; the Vite dev server proxies `/api`, so local development does not need it either. |
| `ALLOW_INSECURE_DEFAULTS` | *(unset)* | No | Set to `1` to start with a default or missing password/secret. **Never set this on a reachable host.** |

### Setting credentials

`docker-compose.yml` reads both required values from the environment, so create a
`.env` file next to it:

```bash
cat > .env <<EOF
ADMIN_PASSWORD=$(openssl rand -base64 24)
SECRET_KEY=$(openssl rand -base64 32)
EOF
```

`docker compose up -d` will refuse to start until both are set.

---

## Security Notes

The admin panel is the only authenticated surface; everything else is public by
design. What protects it:

- **Sessions expire.** Logging in mints a signed token valid for
  `SESSION_TTL_HOURS`. The token is not derived from the password, so it can
  lapse without a password change.
- **Login attempts are rate limited** per client address. The limit is held in
  memory, so it applies per process -- correct for this single-container
  application, but a multi-replica deployment would need shared state.
- **No shipped credentials.** The application will not start on a default or
  missing `ADMIN_PASSWORD`/`SECRET_KEY`.
- **Uploads are restricted** to PNG, JPEG, GIF and WebP, verified against the
  file's leading bytes rather than its extension, and capped at `MAX_UPLOAD_MB`.
  SVG is rejected: uploads are served from the application's own origin, and an
  SVG can carry script. Uploaded files are additionally served under a
  `default-src 'none'; sandbox` policy.
- **A Content-Security-Policy** restricts script to the application itself and
  the embed providers it uses. `frame-src` is permissive because embedding an
  arbitrary publisher's document is the point; `script-src` is what keeps that
  from becoming code execution.

If you put this behind a reverse proxy, terminate TLS there and forward the real
client address, otherwise every login attempt appears to come from the proxy and
the rate limit will apply to all users collectively.

---

## Tech Stack

### Backend
- **Python 3.12** with **FastAPI 0.111**
- **SQLAlchemy 2.0** ORM with SQLite
- **Pydantic 2.7** for request/response validation
- **Uvicorn** ASGI server
- **python-multipart** for file uploads

### Frontend
- **React 19** with **TypeScript 6**
- **React Router 7** for client-side routing
- **Tailwind CSS 4** for styling
- **react-markdown** for rendering Markdown analysis
- **Vite 8** for development and production builds

### Infrastructure
- **Docker** multi-stage build (Node for frontend, Python for runtime)
- **SQLite** database with persistent volume
- Single-container architecture: FastAPI serves the built React SPA

---

## Project Structure

```
politician-position-tracker/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── auth.py              # Authentication (login, token validation)
│   │   ├── database.py          # SQLAlchemy engine & session
│   │   ├── main.py              # FastAPI app, uploads, export, SPA serving
│   │   ├── models.py            # SQLAlchemy models (Politician, Issue, Statement, Source)
│   │   ├── schemas.py           # Pydantic request/response schemas
│   │   └── routers/
│   │       ├── __init__.py
│   │       ├── politicians.py   # CRUD endpoints for politicians
│   │       ├── issues.py        # CRUD endpoints for issues
│   │       └── statements.py    # CRUD endpoints for statements
│   └── requirements.txt
├── frontend/
│   ├── public/
│   │   ├── favicon.svg
│   │   └── icons.svg
│   ├── src/
│   │   ├── api.ts               # API client with auth token management
│   │   ├── App.tsx              # Root component with routing
│   │   ├── AuthContext.tsx       # React context for authentication state
│   │   ├── ThemeContext.tsx      # React context for light/dark theme
│   │   ├── Toast.tsx            # Toast notification system
│   │   ├── types.ts             # TypeScript interfaces
│   │   ├── index.css            # CSS custom properties & theme variables
│   │   ├── main.tsx             # Entry point
│   │   └── pages/
│   │       ├── TimelinePage.tsx
│   │       ├── PoliticiansPage.tsx
│   │       ├── PoliticianDetailPage.tsx
│   │       ├── IssuesPage.tsx
│   │       ├── IssueDetailPage.tsx
│   │       ├── StatementDetailPage.tsx
│   │       └── admin/
│   │           ├── AdminDashboard.tsx
│   │           ├── LoginPage.tsx
│   │           ├── PoliticianForm.tsx
│   │           ├── IssueForm.tsx
│   │           └── StatementForm.tsx
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
├── Dockerfile                   # Multi-stage Docker build
├── docker-compose.yml           # Docker Compose configuration
├── unraid-template.xml          # Unraid Community Applications template
└── docs/
    ├── WIKI.md                  # Architecture & technical documentation
    ├── TRAINING.md              # End-user training guide
    └── API_REFERENCE.md         # Complete API reference
```

---

## API Reference Summary

The backend exposes a REST API at `/api`. All mutating endpoints require Bearer token authentication.

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/auth/login` | No | Authenticate and receive a token |
| `GET` | `/api/politicians` | No | List politicians (paginated) |
| `GET` | `/api/politicians/:id` | No | Get politician with statements |
| `POST` | `/api/politicians` | Yes | Create a politician |
| `PUT` | `/api/politicians/:id` | Yes | Update a politician |
| `DELETE` | `/api/politicians/:id` | Yes | Delete a politician (cascades to statements) |
| `GET` | `/api/issues` | No | List issues (paginated) |
| `GET` | `/api/issues/:id` | No | Get issue with statements |
| `POST` | `/api/issues` | Yes | Create an issue |
| `PUT` | `/api/issues/:id` | Yes | Update an issue |
| `DELETE` | `/api/issues/:id` | Yes | Delete an issue |
| `GET` | `/api/statements` | No | List statements (paginated, filterable) |
| `GET` | `/api/statements/:id` | No | Get statement with sources |
| `POST` | `/api/statements` | Yes | Create a statement |
| `PUT` | `/api/statements/:id` | Yes | Update a statement |
| `DELETE` | `/api/statements/:id` | Yes | Delete a statement |
| `POST` | `/api/uploads` | Yes | Upload an image file |
| `GET` | `/api/export` | Yes | Export all data as JSON |
| `POST` | `/api/import` | Yes | Import data from a JSON backup |
| `GET` | `/api/health` | No | Health check |

For full request/response schemas and examples, see [docs/API_REFERENCE.md](docs/API_REFERENCE.md).

---

## Contributing

Contributions are welcome! To get started:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Set up local development (see Quick Start above)
4. Make your changes
5. Test locally with both the frontend dev server and the Docker build
6. Submit a pull request with a clear description of the changes

### Development Tips

- The frontend dev server (Vite on port 5173) proxies `/api` requests to the backend on port 8000
- CORS is configured to allow the Vite dev server origin during local development
- The SQLite database is auto-created on first run via `Base.metadata.create_all()`
- Uploaded files are stored in `/app/data/uploads` (inside the Docker volume)

### Code Style

- Backend: Python with type hints, FastAPI dependency injection patterns
- Frontend: TypeScript with React functional components and hooks
- Styling: Tailwind CSS utility classes with CSS custom properties for theming

---

## License

This project is licensed under the MIT License.

```
MIT License

Copyright (c) 2025 thegspiro

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
