# Politician Position Tracker -- Technical Wiki

This document provides comprehensive technical documentation for the Politician Position Tracker application, covering architecture, database schema, API endpoints, authentication, frontend routing, data flow, and configuration.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Database Schema](#database-schema)
3. [API Endpoints](#api-endpoints)
4. [Authentication Flow](#authentication-flow)
5. [Frontend Routing](#frontend-routing)
6. [Data Flow](#data-flow)
7. [File Upload Flow](#file-upload-flow)
8. [Social Embed Integration](#social-embed-integration)
9. [Theme System](#theme-system)
10. [Environment Variables Reference](#environment-variables-reference)

---

## Architecture Overview

The Politician Position Tracker is a **single-container** web application.

```
                    +---------------------------+
                    |      Docker Container      |
                    |                           |
  Browser -------->|  Uvicorn (port 8000)      |
  (port 9847)      |    |                      |
                    |    +-- FastAPI            |
                    |    |   |                  |
                    |    |   +-- /api/*         |------> SQLite DB
                    |    |   |   (REST API)     |        (/app/data/)
                    |    |   |                  |
                    |    |   +-- /uploads/*     |------> Uploaded files
                    |    |   |   (static)       |        (/app/data/uploads/)
                    |    |   |                  |
                    |    |   +-- /assets/*      |------> Built React JS/CSS
                    |    |   |   (static)       |        (/app/static/assets/)
                    |    |   |                  |
                    |    |   +-- /*             |------> index.html
                    |    |       (SPA catch-all)|        (React Router)
                    |    |                      |
                    +---------------------------+
```

### Key Design Decisions

- **Single Container**: The FastAPI backend serves both the REST API and the built React SPA. No separate web server (nginx) or frontend container is needed.
- **SQLite**: The database is a single file in the persistent volume. No external database server is required.
- **Multi-Stage Docker Build**: Stage 1 uses Node 20 Alpine to build the React frontend. Stage 2 uses Python 3.12 Slim to run the backend, with the built frontend copied into `backend/static/`.
- **SPA Catch-All**: Any request that does not match an API route or static file returns `index.html`, allowing React Router to handle client-side routing.
- **Port Mapping**: The container internally runs on port 8000, but Docker Compose maps it to host port 9847 to avoid conflicts.

---

## Database Schema

The application uses SQLAlchemy ORM with SQLite. The database file is stored at the path specified by the `DATABASE_URL` environment variable (default: `/app/data/politician_tracker.db`).

Tables are auto-created on application startup via `Base.metadata.create_all(bind=engine)`.

### Tables

#### `politicians`

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | INTEGER | PRIMARY KEY, AUTOINCREMENT | Unique identifier |
| `name` | VARCHAR(200) | NOT NULL | Full name of the politician |
| `party` | VARCHAR(100) | NOT NULL | Political party (e.g., "Democrat", "Republican") |
| `office` | VARCHAR(200) | NOT NULL | Current office (e.g., "U.S. Senator") |
| `state` | VARCHAR(100) | NULLABLE | U.S. state, if applicable |
| `photo_url` | VARCHAR(500) | NULLABLE | URL to a profile photo |
| `created_at` | DATETIME | DEFAULT now() | Record creation timestamp |
| `updated_at` | DATETIME | DEFAULT now(), ON UPDATE now() | Last update timestamp |

**Relationships**: Has many `statements` (cascade delete -- deleting a politician deletes all their statements).

#### `issues`

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | INTEGER | PRIMARY KEY, AUTOINCREMENT | Unique identifier |
| `name` | VARCHAR(200) | NOT NULL, UNIQUE | Issue name (e.g., "Climate Change") |
| `description` | TEXT | NULLABLE | Description of the issue |
| `created_at` | DATETIME | DEFAULT now() | Record creation timestamp |

**Relationships**: Has many `statements` via the `statement_issues` association table.

#### `statements`

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | INTEGER | PRIMARY KEY, AUTOINCREMENT | Unique identifier |
| `politician_id` | INTEGER | FOREIGN KEY -> politicians.id, NOT NULL | The politician who made the statement |
| `title` | VARCHAR(500) | NOT NULL | Descriptive title for the statement |
| `analysis` | TEXT | NOT NULL | Analysis text (supports Markdown) |
| `post_url` | VARCHAR(1000) | NOT NULL | URL to the original social media post |
| `post_platform` | VARCHAR(50) | NOT NULL | Platform name: "X", "Bluesky", "Truth Social", "YouTube" |
| `post_content` | TEXT | NULLABLE | Quoted text from the original post |
| `screenshot_url` | VARCHAR(1000) | NULLABLE | URL to a screenshot of the post |
| `post_date` | DATETIME | NULLABLE | Date the original post was made |
| `created_at` | DATETIME | DEFAULT now() | Record creation timestamp |
| `updated_at` | DATETIME | DEFAULT now(), ON UPDATE now() | Last update timestamp |

**Relationships**:
- Belongs to one `politician`
- Has many `issues` via the `statement_issues` association table
- Has many `sources` (cascade delete)

#### `sources`

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | INTEGER | PRIMARY KEY, AUTOINCREMENT | Unique identifier |
| `uid` | VARCHAR(12) | NOT NULL, UNIQUE | Stable public identifier, preserved across statement edits |
| `statement_id` | INTEGER | FOREIGN KEY -> statements.id, NOT NULL | Parent statement |
| `source_type` | VARCHAR(20) | NOT NULL, DEFAULT "analysis" | Either `"post"` or `"analysis"` |
| `title` | VARCHAR(500) | NOT NULL | Source title/label |
| `url` | VARCHAR(1000) | NOT NULL | URL to the source (http/https only) |
| `description` | TEXT | NULLABLE | Brief editorial note about the source |
| `media_type` | VARCHAR(20) | NOT NULL, DEFAULT "webpage" | One of `webpage`, `document`, `video`, `audio`, `article`, `dataset`. Selects the embed renderer |
| `publisher` | VARCHAR(200) | NULLABLE | Issuing body, e.g. "Congress.gov", "C-SPAN", "FEC" |
| `published_date` | DATETIME | NULLABLE | When the source was published |
| `excerpt` | TEXT | NULLABLE | Verbatim passage being relied on |
| `locator` | VARCHAR(100) | NULLABLE | Where the excerpt lives: "p. 14", "sec. 203", "01:23:45" |
| `archive_url` | VARCHAR(1000) | NULLABLE | Snapshot used when the original rots (http/https only) |
| `archived_at` | DATETIME | NULLABLE | When the snapshot was taken |
| `retrieved_at` | DATETIME | NULLABLE | When the original was last confirmed |
| `sort_order` | INTEGER | NOT NULL, DEFAULT 0 | Display order; also the citation marker number |
| `authors` | JSON | NULLABLE | Ordered list of `{given, family}` or `{literal}` objects. Nullable rather than defaulted because MySQL before 8.0.13 rejects DEFAULT on a JSON column; readers treat NULL as an empty list |
| `container_title` | VARCHAR(300) | NULLABLE | The publication the source sits in. Italicised for periodicals, roman for plain website names |
| `edition` | VARCHAR(100) | NULLABLE | Edition statement |
| `document_type` | VARCHAR(40) | NULLABLE | One of `bill`, `statute`, `hearing`, `committee_report`, `court_opinion`, `executive_order`, `other`. Selects Chicago's public-document form |
| `bill_number` | VARCHAR(50) | NULLABLE | e.g. "H.R. 1234" |
| `congress_number` | INTEGER | NULLABLE | e.g. 118 |
| `congress_session` | VARCHAR(20) | NULLABLE | e.g. "2nd" |
| `committee` | VARCHAR(300) | NULLABLE | Committee holding a hearing |
| `report_number` | VARCHAR(50) | NULLABLE | e.g. "H.R. Rep. No. 118-123" |

**Relationships**: Belongs to one `statement`.

**Why `uid` exists**: saving a statement rewrites its source rows, so `id` is not
stable across edits. `uid` is generated once and preserved, so citation markers
and `#source-<uid>` fragment links keep working after an edit.

**Citations**: a `[^1]` marker in a statement's `analysis` refers to the source
numbered `[1]` in the rendered source list, which is ordered by `sort_order`.
Markers are rendered as links to that source's card.

#### `statement_issues` (Association Table)

| Column | Type | Constraints | Description |
|---|---|---|---|
| `statement_id` | INTEGER | PRIMARY KEY, FOREIGN KEY -> statements.id (ON DELETE CASCADE) | Statement side of the relationship |
| `issue_id` | INTEGER | PRIMARY KEY, FOREIGN KEY -> issues.id (ON DELETE CASCADE) | Issue side of the relationship |

This is a many-to-many join table. Deleting a statement or issue automatically removes the corresponding rows from this table via `ON DELETE CASCADE`.

### Entity Relationship Diagram

```
  politicians 1---* statements *---* issues
                       |
                       1
                       |
                       *
                    sources
```

---

## API Endpoints

All API endpoints are prefixed with `/api`. Endpoints that modify data require Bearer token authentication (see [Authentication Flow](#authentication-flow)).

### Auth

#### `POST /api/auth/login`

Authenticate with the admin password and receive a Bearer token.

- **Auth Required**: No
- **Request Body**: `{ "password": "string" }`
- **Response** (200): `{ "token": "string" }`
- **Response** (401): `{ "detail": "Invalid password" }`

### Politicians

#### `GET /api/politicians`

List all politicians with pagination.

- **Auth Required**: No
- **Query Parameters**:
  - `skip` (int, default 0, min 0) -- Number of records to skip
  - `limit` (int, default 50, min 1, max 200) -- Maximum number of records to return
- **Response** (200): `PaginatedResponse<PoliticianOut>`

#### `GET /api/politicians/{politician_id}`

Get a single politician with all their statements.

- **Auth Required**: No
- **Path Parameters**: `politician_id` (int)
- **Response** (200): `PoliticianDetailOut` (includes `statements` array)
- **Response** (404): `{ "detail": "Politician not found" }`

#### `POST /api/politicians`

Create a new politician.

- **Auth Required**: Yes
- **Request Body**: `PoliticianCreate`
  - `name` (string, required)
  - `party` (string, required)
  - `office` (string, required)
  - `state` (string or null, optional)
  - `photo_url` (string or null, optional)
- **Response** (201): `PoliticianOut`

#### `PUT /api/politicians/{politician_id}`

Update an existing politician.

- **Auth Required**: Yes
- **Path Parameters**: `politician_id` (int)
- **Request Body**: `PoliticianCreate` (same schema as create)
- **Response** (200): `PoliticianOut`
- **Response** (404): `{ "detail": "Politician not found" }`

#### `DELETE /api/politicians/{politician_id}`

Delete a politician and all their statements (cascade).

- **Auth Required**: Yes
- **Path Parameters**: `politician_id` (int)
- **Response** (204): No content
- **Response** (404): `{ "detail": "Politician not found" }`

### Issues

#### `GET /api/issues`

List all issues with pagination.

- **Auth Required**: No
- **Query Parameters**:
  - `skip` (int, default 0, min 0)
  - `limit` (int, default 50, min 1, max 200)
- **Response** (200): `PaginatedResponse<IssueOut>`

#### `GET /api/issues/{issue_id}`

Get a single issue with all tagged statements.

- **Auth Required**: No
- **Path Parameters**: `issue_id` (int)
- **Response** (200): `IssueDetailOut` (includes `statements` array)
- **Response** (404): `{ "detail": "Issue not found" }`

#### `POST /api/issues`

Create a new issue.

- **Auth Required**: Yes
- **Request Body**: `IssueCreate`
  - `name` (string, required, must be unique)
  - `description` (string or null, optional)
- **Response** (201): `IssueOut`

#### `PUT /api/issues/{issue_id}`

Update an existing issue.

- **Auth Required**: Yes
- **Path Parameters**: `issue_id` (int)
- **Request Body**: `IssueCreate`
- **Response** (200): `IssueOut`
- **Response** (404): `{ "detail": "Issue not found" }`

#### `DELETE /api/issues/{issue_id}`

Delete an issue. Removes the issue from all tagged statements (via cascade on the association table), but does not delete the statements themselves.

- **Auth Required**: Yes
- **Path Parameters**: `issue_id` (int)
- **Response** (204): No content
- **Response** (404): `{ "detail": "Issue not found" }`

### Statements

#### `GET /api/statements`

List statements with pagination and filtering.

- **Auth Required**: No
- **Query Parameters**:
  - `politician_id` (int, optional) -- Filter by politician
  - `issue_id` (int, optional) -- Filter by issue tag
  - `platform` (string, optional) -- Filter by platform (e.g., "X", "YouTube")
  - `search` (string, optional) -- Search in title, analysis, and post content (case-insensitive)
  - `skip` (int, default 0, min 0)
  - `limit` (int, default 50, min 1, max 200)
- **Response** (200): `PaginatedResponse<StatementListOut>`

Note: `StatementListOut` includes nested `politician` and `issues` but does not include `sources`. Use the single-statement endpoint to get sources.

#### `GET /api/statements/{statement_id}`

Get a single statement with full details including sources.

- **Auth Required**: No
- **Path Parameters**: `statement_id` (int)
- **Response** (200): `StatementOut` (includes `politician`, `issues`, and `sources`)
- **Response** (404): `{ "detail": "Statement not found" }`

#### `POST /api/statements`

Create a new statement.

- **Auth Required**: Yes
- **Request Body**: `StatementCreate`
  - `politician_id` (int, required)
  - `issue_ids` (array of int, default [])
  - `title` (string, required)
  - `analysis` (string, required)
  - `post_url` (string, required)
  - `post_platform` (string, required)
  - `post_content` (string or null, optional)
  - `screenshot_url` (string or null, optional)
  - `post_date` (datetime or null, optional)
  - `sources` (array of SourceCreate, default [])
    - Each source: `{ "source_type": "post"|"analysis", "title": "string", "url": "string", "description": "string|null" }`
- **Response** (201): `StatementOut`
- **Response** (400): `{ "detail": "One or more issue IDs are invalid" }`

#### `PUT /api/statements/{statement_id}`

Update an existing statement. Replaces all sources (old sources are deleted, new ones are created).

- **Auth Required**: Yes
- **Path Parameters**: `statement_id` (int)
- **Request Body**: `StatementUpdate` (same schema as create)
- **Response** (200): `StatementOut`
- **Response** (404): `{ "detail": "Statement not found" }`
- **Response** (400): `{ "detail": "One or more issue IDs are invalid" }`

#### `DELETE /api/statements/{statement_id}`

Delete a statement and all its sources.

- **Auth Required**: Yes
- **Path Parameters**: `statement_id` (int)
- **Response** (204): No content
- **Response** (404): `{ "detail": "Statement not found" }`

### Uploads

#### `POST /api/uploads`

Upload an image file. Returns the URL path to the uploaded file.

- **Auth Required**: Yes
- **Content-Type**: `multipart/form-data`
- **Form Field**: `file` (file upload)
- **Allowed Extensions**: `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`, `.svg`
- **Response** (200): `{ "url": "/uploads/{filename}" }`
- **Response** (400): `{ "detail": "File type '.xyz' not allowed. Allowed: .png, .jpg, .jpeg, .gif, .webp, .svg" }`

Uploaded files are stored in `/app/data/uploads/` with a UUID-based filename to avoid collisions.

### Export

#### `GET /api/export`

Export all data as JSON.

- **Auth Required**: Yes
- **Response** (200):
  ```json
  {
    "politicians": [ ... ],
    "issues": [ ... ],
    "statements": [ ... ]
  }
  ```
  Each array contains fully serialized objects (statements include nested politician, issues, and sources).

### Health

#### `GET /api/health`

Health check endpoint used by Docker HEALTHCHECK.

- **Auth Required**: No
- **Response** (200): `{ "status": "ok" }`

---

## Authentication Flow

The application uses a simple password-based authentication scheme with HMAC tokens.

### How It Works

1. **Login**: The user sends a POST request to `/api/auth/login` with `{ "password": "..." }`.

2. **Password Validation**: The server compares the provided password against the `ADMIN_PASSWORD` environment variable. If it does not match, a 401 error is returned.

3. **Token Generation**: If the password is correct, the server generates an HMAC-SHA256 token:
   ```
   token = HMAC-SHA256(key=SECRET_KEY, message=ADMIN_PASSWORD)
   ```
   The token is deterministic -- the same password and secret key always produce the same token.

4. **Token Storage**: The frontend stores the token in `localStorage` under the key `auth_token`.

5. **Authenticated Requests**: For all subsequent API requests, the frontend includes the token as a Bearer token in the `Authorization` header:
   ```
   Authorization: Bearer <token>
   ```

6. **Token Validation**: On the server side, the `require_admin` dependency recalculates the expected token using the same HMAC process and uses `hmac.compare_digest` for constant-time comparison.

7. **Logout**: The frontend removes the token from `localStorage` and sets the auth state to logged out.

8. **Token Invalidation**: If any API request returns a 401 status, the frontend automatically clears the token (in case the server password or secret changed).

### Security Notes

- There is no token expiration. Tokens remain valid as long as the `ADMIN_PASSWORD` and `SECRET_KEY` environment variables do not change.
- Changing either `ADMIN_PASSWORD` or `SECRET_KEY` invalidates all existing tokens.
- The password and secret key should be changed from their defaults in production.
- There is only one admin account (single shared password).

---

## Frontend Routing

The frontend uses React Router v7 with the following routes:

| Path | Component | Description |
|---|---|---|
| `/` | `TimelinePage` | Main timeline feed with search, filters, and sort |
| `/politicians` | `PoliticiansPage` | Grid listing of all politicians |
| `/politicians/:id` | `PoliticianDetailPage` | Politician profile with their statements |
| `/issues` | `IssuesPage` | Grid listing of all issues |
| `/issues/:id` | `IssueDetailPage` | Issue detail with tagged statements |
| `/statements/:id` | `StatementDetailPage` | Full statement view with embeds and sources |
| `/admin` | `AdminDashboard` | Admin panel (shows LoginPage if not authenticated) |
| `/admin/politicians/new` | `PoliticianForm` | Create new politician form |
| `/admin/politicians/:id/edit` | `PoliticianForm` | Edit existing politician form |
| `/admin/issues/new` | `IssueForm` | Create new issue form |
| `/admin/issues/:id/edit` | `IssueForm` | Edit existing issue form |
| `/admin/statements/new` | `StatementForm` | Create new statement form |
| `/admin/statements/:id/edit` | `StatementForm` | Edit existing statement form |

### Navigation

The navigation bar contains four links:
- **Timeline** (`/`) -- The default home page
- **Politicians** (`/politicians`)
- **Issues** (`/issues`)
- **Admin** (`/admin`)

On mobile, the navigation collapses into a hamburger menu. The theme toggle button (sun/moon icon) is always visible.

### Admin Route Protection

Admin routes are not protected by a route guard. Instead, the `AdminDashboard` component checks `isLoggedIn` from `AuthContext` and conditionally renders either the `LoginPage` or the dashboard content. Admin form pages (PoliticianForm, IssueForm, StatementForm) rely on the API returning 401 if the token is missing or invalid.

---

## Data Flow

### Reading Data (Public Pages)

```
User navigates to page
       |
       v
React component mounts
       |
       v
useEffect calls API function (e.g., fetchStatements)
       |
       v
api.ts sends GET request to /api/...
  - Includes Authorization header if token exists
       |
       v
FastAPI endpoint queries SQLAlchemy
  - Uses joinedload for related objects
  - Applies filters, pagination
       |
       v
SQLAlchemy queries SQLite database
       |
       v
Results serialized via Pydantic schema
       |
       v
JSON response sent to browser
       |
       v
React state updated (useState setter)
       |
       v
Component re-renders with data
```

### Writing Data (Admin Operations)

```
Admin fills out form and clicks Submit
       |
       v
Form validation runs (client-side)
       |
       v
api.ts sends POST/PUT request to /api/...
  - Authorization: Bearer <token>
  - Content-Type: application/json
  - Body: JSON payload
       |
       v
FastAPI require_admin dependency validates token
       |
       v (if valid)
Router function creates/updates SQLAlchemy model
       |
       v
SQLAlchemy commits to SQLite
       |
       v
Response with created/updated object
       |
       v
Toast notification shown
       |
       v
Navigate back to admin dashboard
```

### Deleting Data

```
Admin clicks Delete button
       |
       v
Confirmation dialog with cascade warning
  (e.g., "This will delete 3 statements")
       |
       v (if confirmed)
api.ts sends DELETE request
  - Authorization: Bearer <token>
       |
       v
FastAPI validates token, finds record
       |
       v
SQLAlchemy deletes record (cascade deletes related records)
       |
       v
204 No Content response
       |
       v
Toast notification, reload data
```

---

## File Upload Flow

```
Admin selects file in statement form
       |
       v
Clicks "Upload" button
       |
       v
uploadFile() in api.ts creates FormData
  - Appends file as "file" field
  - Sets Authorization header (no Content-Type -- browser sets multipart boundary)
       |
       v
POST /api/uploads
       |
       v
FastAPI validates:
  1. Token is valid (require_admin)
  2. File extension is allowed (.png, .jpg, .jpeg, .gif, .webp, .svg)
       |
       v
File saved to /app/data/uploads/{uuid}{ext}
  - UUID-based filename prevents collisions
       |
       v
Response: { "url": "/uploads/{filename}" }
       |
       v
Screenshot URL field populated in form
       |
       v
When statement is saved, the URL is stored in the database
       |
       v
On the public page, <img src="/uploads/{filename}"> loads the image
  - Served by FastAPI StaticFiles mount
```

### Important Notes

- Files are stored in `/app/data/uploads/`, which is inside the Docker persistent volume. This means uploaded files survive container restarts.
- The upload endpoint does not resize or process images. Files are stored as-is.
- Maximum file size is limited by Uvicorn/FastAPI defaults (typically ~100MB).
- Old uploaded files are never automatically cleaned up, even if the statement that referenced them is deleted.

---

## Social Embed Integration

The `StatementDetailPage` includes an `EmbedPost` component that renders social media embeds based on the `post_platform` field.

### X (Twitter)

**How it works**: Uses the official Twitter widget JavaScript.

1. The component renders a `<blockquote class="twitter-tweet">` element containing the post URL.
2. On mount, it loads the Twitter widget script from `https://platform.twitter.com/widgets.js`.
3. If the script is already loaded, it calls `window.twttr.widgets.load()` to re-render.
4. The Twitter script finds the blockquote and replaces it with an interactive embedded tweet.

**Requirements**: The post URL must be a valid Twitter/X status URL (e.g., `https://x.com/user/status/123456`).

### YouTube

**How it works**: Uses a privacy-enhanced iframe embed.

1. The component extracts the video ID from the URL using `getYouTubeVideoId()`.
2. Supported URL formats:
   - `https://www.youtube.com/watch?v=VIDEO_ID`
   - `https://youtu.be/VIDEO_ID`
   - `https://www.youtube-nocookie.com/...`
3. Renders a responsive iframe with `src="https://www.youtube-nocookie.com/embed/{videoId}"`.
4. The iframe has a 16:9 aspect ratio using the padding-bottom percentage technique.

**Requirements**: The URL must contain a valid YouTube video ID.

### Bluesky

**How it works**: Uses the official Bluesky embed JavaScript.

1. The component converts the Bluesky web URL to an AT protocol URI:
   - Input: `https://bsky.app/profile/{handle}/post/{rkey}`
   - Output: `at://{handle}/app.bsky.feed.post/{rkey}`
2. Renders a `<blockquote class="bluesky-embed" data-bluesky-uri="...">` element.
3. Loads the Bluesky embed script from `https://embed.bsky.app/static/embed.js`.
4. The script replaces the blockquote with an interactive embedded post.

**Requirements**: The URL must be a valid Bluesky post URL.

### Truth Social and Other Platforms

**How it works**: Falls back to a styled blockquote.

1. If `post_content` is provided, it is displayed in a blockquote with a left border accent.
2. A "View original post" link is provided that opens the URL in a new tab.

There is no native embed support for Truth Social since it does not provide an embed API.

---

## Theme System

The theme system uses CSS custom properties (variables) defined in `frontend/src/index.css`, toggled via a `dark` class on the `<html>` element.

### CSS Custom Properties

| Property | Light Value | Dark Value | Usage |
|---|---|---|---|
| `--color-bg` | `#ffffff` | `#0f172a` | Page background |
| `--color-bg-secondary` | `#f9fafb` | `#1e293b` | Secondary backgrounds, hover states |
| `--color-text` | `#111827` | `#f1f5f9` | Primary text |
| `--color-text-secondary` | `#6b7280` | `#94a3b8` | Secondary/muted text |
| `--color-border` | `#e5e7eb` | `#334155` | Borders and dividers |
| `--color-accent` | `#2563eb` | `#3b82f6` | Primary action color (buttons, links) |
| `--color-accent-hover` | `#1d4ed8` | `#60a5fa` | Hover state for accent color |
| `--color-card` | `#ffffff` | `#1e293b` | Card/panel backgrounds |
| `--color-badge-bg` | `#dbeafe` | `#1e3a5f` | Issue badge backgrounds |
| `--color-badge-text` | `#1e40af` | `#93c5fd` | Issue badge text |
| `--color-danger` | `#dc2626` | `#ef4444` | Error/delete actions |
| `--color-danger-hover` | `#b91c1c` | `#f87171` | Hover state for danger color |

### Theme Toggle Logic

The theme is managed by `ThemeContext.tsx`:

1. **Initial State**: Checks `localStorage` for a saved preference (`"light"` or `"dark"`). If none exists, falls back to the system preference via `window.matchMedia('(prefers-color-scheme: dark)')`.

2. **Toggle**: Clicking the sun/moon button in the header calls `toggleTheme()`, which flips the boolean state.

3. **Effect**: When `isDark` changes:
   - Adds or removes the `dark` class on `document.documentElement` (the `<html>` element).
   - Saves the preference to `localStorage` under the key `theme`.

4. **CSS Cascade**: The `:root` selector defines light mode variables. The `.dark` selector overrides them with dark mode values. All components use `var(--color-*)` references, so they automatically update when the class changes.

5. **Transition**: The `body` element has `transition: background-color 0.2s, color 0.2s` for a smooth theme change.

---

## Environment Variables Reference

| Variable | Default | Required | Where Used | Description |
|---|---|---|---|---|
| `ADMIN_PASSWORD` | *(none)* | **Yes** | `backend/app/auth.py` | The single admin password, compared in constant time. Startup fails if unset or `changeme`. |
| `SECRET_KEY` | *(none)* | **Yes** | `backend/app/auth.py` | HS256 signing key for session tokens. Startup fails on a published default. |
| `DATABASE_URL` | `sqlite:///./politician_tracker.db` (dev) / `sqlite:////app/data/politician_tracker.db` (Docker) | No | `backend/app/database.py` | SQLAlchemy database connection string. |
| `SESSION_TTL_HOURS` | `12` | No | `backend/app/auth.py` | Session token lifetime. |
| `LOGIN_MAX_ATTEMPTS` | `5` | No | `backend/app/auth.py` | Failed logins per client address before throttling. |
| `LOGIN_WINDOW_SECONDS` | `900` | No | `backend/app/auth.py` | Window over which failures are counted. |
| `MAX_UPLOAD_MB` | `5` | No | `backend/app/main.py` | Largest accepted upload. |
| `UPLOAD_DIR` | `/app/data/uploads` | No | `backend/app/main.py` | Upload storage directory. |
| `CONTENT_SECURITY_POLICY` | *(built-in)* | No | `backend/app/main.py` | Overrides the CSP; empty string disables it. |
| `CORS_ORIGINS` | *(empty)* | No | `backend/app/main.py` | Comma-separated allowed origins. Off by default. |
| `SITE_NAME` | `Politician Tracker` | No | `backend/app/settings.py` | Site name used in the "cite this page" citation. |
| `SITE_URL` | *(from request)* | No | `backend/app/routers/statements.py` | Public base URL for the "cite this page" citation. |
| `CITATION_STYLE` | `notes-bibliography` | No | `backend/app/settings.py` | Default Chicago system. An unrecognised value falls back to the default rather than failing the boot. |
| `ALLOW_INSECURE_DEFAULTS` | *(unset)* | No | `backend/app/auth.py` | Permits startup without real credentials. Never set on a reachable host. |

### Notes on Defaults

- In the Dockerfile, `DATABASE_URL` is set to `sqlite:////app/data/politician_tracker.db` (four slashes for an absolute path) so the database is stored in the persistent volume.
- In local development (without Docker), the default is `sqlite:///./politician_tracker.db` (three slashes for a relative path), which creates the database in the `backend/` directory.
- `ADMIN_PASSWORD` and `SECRET_KEY` no longer have defaults. The application raises at startup rather than running with a value published in this repository. `ALLOW_INSECURE_DEFAULTS=1` overrides this for local development only.
- Session tokens are signed JWTs with an expiry, not a value derived from the password. Changing `SECRET_KEY` invalidates every existing session.
