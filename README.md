# Politician Position Tracker

A self-hosted web application for tracking and analyzing politician statements on social media. Link to posts on X (Twitter), Bluesky, Truth Social, or YouTube, write analysis with sourced citations, and organize everything by politician and issue.

Built as a single-container Docker application with a FastAPI backend serving a React SPA frontend, backed by SQLite.

---

## Features

- **Timeline Feed** -- Browse all tracked statements in a chronological timeline with search, filters, and sort options
- **Politician Profiles** -- View all statements from a specific politician with photo, party, office, and state
- **Issue Tracking** -- Tag statements with multiple issues and browse all statements for a given issue
- **Social Media Embeds** -- Native embeds for X/Twitter, YouTube, and Bluesky posts; styled blockquotes for Truth Social
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

# Edit docker-compose.yml to set your ADMIN_PASSWORD and SECRET_KEY
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
  -e ADMIN_PASSWORD=your-secure-password \
  -e SECRET_KEY=your-random-secret-key \
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

**Frontend:**

```bash
cd frontend
npm install
npm run dev
```

The frontend dev server runs on `http://localhost:5173` and proxies API requests to `http://localhost:8000`.

---

## Unraid Installation

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
| `ADMIN_PASSWORD` | `changeme` | Yes | Password for the admin panel. **Change this in production.** |
| `SECRET_KEY` | `politician-tracker-secret-key` | Yes | Secret used to generate auth tokens. Use a long random string. |
| `DATABASE_URL` | `sqlite:////app/data/politician_tracker.db` | No | SQLAlchemy database connection string. Defaults to SQLite in the data volume. |

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
