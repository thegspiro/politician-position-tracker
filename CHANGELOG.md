# Changelog

All notable changes to the Politician Position Tracker are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.1.0] - 2025-07-15

### Added

- **Admin Authentication** -- Password-protected admin panel with HMAC-based token authentication. The admin password is set via the `ADMIN_PASSWORD` environment variable and the token is generated using the `SECRET_KEY`. Tokens are stored in `localStorage` and sent as `Bearer` tokens on all mutating API requests.

- **Pagination** -- All list endpoints (`/api/politicians`, `/api/issues`, `/api/statements`) now return paginated responses with `items`, `total`, `skip`, and `limit` fields. Supports `skip` and `limit` query parameters for offset-based pagination.

- **Multi-Tag (Many-to-Many Statements to Issues)** -- Statements can now be tagged with multiple issues using a many-to-many relationship via the `statement_issues` association table. The statement form uses toggle buttons for issue selection.

- **Image Upload** -- Admins can upload screenshot images (PNG, JPG, JPEG, GIF, WebP, SVG) via the `/api/uploads` endpoint. Files are stored in the persistent data volume at `/app/data/uploads` and served as static files. The statement form includes a file picker with an upload button.

- **Data Export** -- New `/api/export` endpoint (admin-only) returns all politicians, issues, and statements as a single JSON payload. The admin dashboard includes an "Export Data" button that triggers a browser download of `export.json`.

- **Social Media Embeds** -- Statement detail pages now embed the original social media post:
  - **X (Twitter)**: Native Twitter widget embed via `platform.twitter.com/widgets.js`
  - **YouTube**: Privacy-enhanced iframe embed (`youtube-nocookie.com`) with responsive 16:9 aspect ratio. Supports both `youtube.com/watch?v=` and `youtu.be/` URL formats.
  - **Bluesky**: Native Bluesky embed via `embed.bsky.app/static/embed.js`. Automatically converts web URLs to AT protocol URIs.
  - **Truth Social**: Styled blockquote fallback with link to original post.

- **Markdown Support in Analysis** -- Analysis text is rendered with `react-markdown`, supporting headings, bold, italic, lists, links, blockquotes, and inline code. Custom CSS styles are applied via the `.prose` class in `index.css`.

- **Toast Notifications** -- Global toast notification system using React context. Shows success (green), error (red), and info (blue) messages with a 3-second auto-dismiss and slide-in animation. Used for all admin CRUD operations and data export.

- **Sort Options** -- Timeline page includes a sort dropdown with three options: Newest First, Oldest First, and Politician A-Z. Sorting is applied client-side on the fetched results.

- **Cascade Delete Warnings** -- When deleting a politician from the admin dashboard, the confirmation dialog shows how many statements will also be deleted. When deleting an issue, the dialog shows how many statements are tagged with that issue.

- **Docker Healthcheck** -- Dockerfile includes a `HEALTHCHECK` instruction that pings `/api/health` every 30 seconds with a 5-second timeout. Returns `{"status": "ok"}` on success.

- **Unraid Community Applications Template** -- Added `unraid-template.xml` for one-click installation on Unraid servers. Includes configuration for web UI port, data path, admin password, secret key, and database URL.

- **SEO / Open Graph Meta Tags** -- Added `<meta>` tags in `index.html` for search engine description, Open Graph (og:title, og:description, og:type, og:site_name), and Twitter Card (twitter:card, twitter:title, twitter:description).

- **Data Import** -- Admin can import data from a JSON backup file via `POST /api/import`. Import merges with existing data: duplicate politicians (by name), issues (by name), and statements (by title + politician) are skipped. Shows a summary of how many records were imported.

- **Non-Standard Docker Port** -- Docker Compose maps host port `9847` to container port `8000` to avoid conflicts with common services.

- **Share Buttons** -- Statement detail pages include share buttons for X/Twitter, Facebook, email, and copy-to-clipboard with visual feedback.

- **Light/Dark Theme System** -- CSS custom property-based theming with 13 color tokens. Supports system preference detection via `prefers-color-scheme`, manual toggle saved to `localStorage`, and smooth transition animations.

### Changed

- Statements now use `issue_ids` (array of integers) instead of a single `issue_id` in create and update payloads.
- Source citations are now categorized as either `"post"` (citations for the original social media post) or `"analysis"` (citations supporting the analysis/response).

---

## [1.0.0] - 2025-06-01

### Added

- **Core Application** -- Single-container Docker application with FastAPI backend serving a React SPA frontend, backed by SQLite.

- **Politician Management** -- CRUD operations for politicians with name, party, office, state, and photo URL fields.

- **Issue Management** -- CRUD operations for issues with name and description fields. Issue names are enforced as unique.

- **Statement Management** -- CRUD operations for statements linking a politician to issues, with title, analysis, post URL, post platform, post content, screenshot URL, and post date fields.

- **Source Citations** -- Statements can have multiple source citations, each with a title, URL, and optional description.

- **Timeline Feed** -- Public timeline page showing all statements in reverse chronological order with politician info, issue badges, platform icons, analysis snippets, and links to full detail pages.

- **Politician Profiles** -- Public politician detail pages showing profile information and all associated statements sorted by date.

- **Issue Pages** -- Public issue listing page with cards, and issue detail pages showing all statements tagged with that issue.

- **Statement Detail Pages** -- Full statement view with politician info, issue badges, post embed area, full analysis text, source citations (separated by type), and share buttons.

- **Politicians Page** -- Grid layout of all politicians with photo/initial avatar, name, party badge, office, and state.

- **Client-Side Search** -- Timeline search with debounced input that filters statements by title, analysis, and post content via server-side `ILIKE` queries.

- **Filter Controls** -- Timeline filters for politician and issue via dropdown selects.

- **Platform Icons** -- SVG icons for X/Twitter, Facebook, Instagram, YouTube, Bluesky, and Truth Social displayed on timeline cards and statement detail pages.

- **Responsive Navigation** -- Sticky top navigation bar with desktop horizontal links and mobile hamburger menu.

- **React Router** -- Client-side routing for all public and admin pages with SPA catch-all on the backend.

- **FastAPI SPA Serving** -- Backend serves the built React frontend from `backend/static/`, with a catch-all route that returns `index.html` for any non-API path so React Router works correctly.

- **SQLAlchemy Models** -- Four database models: `Politician`, `Issue`, `Statement`, and `Source`, with proper relationships, cascade deletes, and a many-to-many association table for `statement_issues`.

- **Pydantic Schemas** -- Request and response schemas with validation, including nested output schemas (e.g., `StatementOut` includes full `PoliticianOut` and `IssueOut` objects).

- **CORS Middleware** -- Configured for local development with Vite on port 5173 proxying to FastAPI on port 8000.

- **Docker Multi-Stage Build** -- Stage 1 builds the React frontend with Node 20, Stage 2 runs the Python backend with the built frontend copied into the static directory.

- **Docker Compose** -- Service configuration with persistent named volume for the SQLite database and uploaded files.

- **Error Handling** -- Loading spinners, error messages with retry buttons, and empty state messages throughout the frontend.
