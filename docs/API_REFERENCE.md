# Politician Position Tracker -- API Reference

Complete reference for the REST API. All endpoints are prefixed with `/api`.

---

## Table of Contents

1. [Base URL](#base-url)
2. [Authentication](#authentication)
3. [Pagination](#pagination)
4. [Error Responses](#error-responses)
5. [Auth Endpoints](#auth-endpoints)
6. [Politician Endpoints](#politician-endpoints)
7. [Issue Endpoints](#issue-endpoints)
8. [Statement Endpoints](#statement-endpoints)
9. [Upload Endpoint](#upload-endpoint)
10. [Export Endpoint](#export-endpoint)
11. [Import Endpoint](#import-endpoint)
12. [Health Endpoint](#health-endpoint)

---

## Base URL

All API routes are under the `/api` prefix.

- **Docker Compose default**: `http://localhost:9847/api`
- **Local development**: `http://localhost:8000/api`

---

## Authentication

### Obtaining a Token

Send a POST request to `/api/auth/login` with the admin password:

```bash
curl -X POST http://localhost:9847/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"password": "your-admin-password"}'
```

**Response:**
```json
{
  "token": "a1b2c3d4e5f6..."
}
```

### Using the Token

Include the token in the `Authorization` header as a Bearer token on all authenticated requests:

```
Authorization: Bearer a1b2c3d4e5f6...
```

### Token Lifetime

Tokens do not expire. They remain valid until the `ADMIN_PASSWORD` or `SECRET_KEY` environment variables are changed, which invalidates all existing tokens.

---

## Pagination

All list endpoints return paginated responses with the following structure:

```json
{
  "items": [ ... ],
  "total": 42,
  "skip": 0,
  "limit": 50
}
```

| Field | Type | Description |
|---|---|---|
| `items` | array | Array of objects for the current page |
| `total` | integer | Total number of records matching the query (before pagination) |
| `skip` | integer | Number of records skipped (offset) |
| `limit` | integer | Maximum number of records returned |

### Query Parameters

| Parameter | Type | Default | Min | Max | Description |
|---|---|---|---|---|---|
| `skip` | integer | `0` | `0` | -- | Number of records to skip |
| `limit` | integer | `50` | `1` | `200` | Maximum records to return |

---

## Error Responses

The API uses standard HTTP status codes. Error responses have the following format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

### Common Status Codes

| Code | Meaning | When |
|---|---|---|
| `200` | OK | Successful GET, PUT |
| `201` | Created | Successful POST (resource created) |
| `204` | No Content | Successful DELETE |
| `400` | Bad Request | Invalid input data (e.g., invalid issue IDs, disallowed file type) |
| `401` | Unauthorized | Missing or invalid authentication token |
| `404` | Not Found | Resource does not exist |
| `422` | Unprocessable Entity | Request body validation error (Pydantic) |

### 401 Unauthorized

Returned when a protected endpoint is called without a valid Bearer token:

```json
{
  "detail": "Invalid or missing token"
}
```

Or when the login password is incorrect:

```json
{
  "detail": "Invalid password"
}
```

### 404 Not Found

Returned when a resource with the specified ID does not exist:

```json
{
  "detail": "Politician not found"
}
```

### 422 Unprocessable Entity

Returned when the request body fails Pydantic validation:

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "name"],
      "msg": "Field required",
      "input": {},
      "url": "https://errors.pydantic.dev/2.7/v/missing"
    }
  ]
}
```

---

## Auth Endpoints

### POST /api/auth/login

Authenticate with the admin password and receive a Bearer token.

**Auth Required**: No

**Request Body:**
```json
{
  "password": "string"
}
```

**Response (200):**
```json
{
  "token": "string",
  "expires_in": 43200
}
```

`token` is a signed JWT carrying a subject and an expiry. Send it as
`Authorization: Bearer <token>`. It is valid for `expires_in` seconds
(`SESSION_TTL_HOURS`, 12 hours by default); after that every authenticated
endpoint returns 401 and a new login is required.

**Response (401):**
```json
{
  "detail": "Invalid password"
}
```

**Response (429):** returned once `LOGIN_MAX_ATTEMPTS` failed attempts have come
from the same client address within `LOGIN_WINDOW_SECONDS`. Carries a
`Retry-After` header. A successful login clears the count.
```json
{
  "detail": "Too many failed login attempts. Try again later."
}
```

**Example:**
```bash
curl -X POST http://localhost:9847/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"password": "your-admin-password"}'
```

---

## Politician Endpoints

### GET /api/politicians

List all politicians with pagination.

**Auth Required**: No

**Query Parameters:**
| Parameter | Type | Default | Description |
|---|---|---|---|
| `skip` | integer | `0` | Offset |
| `limit` | integer | `50` | Max results (1-200) |

**Response (200):**
```json
{
  "items": [
    {
      "id": 1,
      "name": "Jane Smith",
      "party": "Democrat",
      "office": "U.S. Senator",
      "state": "California",
      "photo_url": "https://example.com/photo.jpg",
      "created_at": "2025-06-01T12:00:00",
      "updated_at": "2025-06-01T12:00:00"
    }
  ],
  "total": 1,
  "skip": 0,
  "limit": 50
}
```

**Example:**
```bash
curl http://localhost:9847/api/politicians?skip=0&limit=10
```

---

### GET /api/politicians/{politician_id}

Get a single politician with all their statements.

**Auth Required**: No

**Path Parameters:**
| Parameter | Type | Description |
|---|---|---|
| `politician_id` | integer | Politician ID |

**Response (200):**
```json
{
  "id": 1,
  "name": "Jane Smith",
  "party": "Democrat",
  "office": "U.S. Senator",
  "state": "California",
  "photo_url": "https://example.com/photo.jpg",
  "created_at": "2025-06-01T12:00:00",
  "updated_at": "2025-06-01T12:00:00",
  "statements": [
    {
      "id": 1,
      "politician_id": 1,
      "title": "Senator calls for new climate legislation",
      "analysis": "Analysis text...",
      "post_url": "https://x.com/user/status/123",
      "post_platform": "X",
      "post_content": "Original post text...",
      "screenshot_url": null,
      "post_date": "2025-05-15T00:00:00",
      "created_at": "2025-06-01T12:00:00",
      "updated_at": "2025-06-01T12:00:00",
      "politician": {
        "id": 1,
        "name": "Jane Smith",
        "party": "Democrat",
        "office": "U.S. Senator",
        "state": "California",
        "photo_url": "https://example.com/photo.jpg",
        "created_at": "2025-06-01T12:00:00",
        "updated_at": "2025-06-01T12:00:00"
      },
      "issues": [
        {
          "id": 1,
          "name": "Climate Change",
          "description": "Environmental policy",
          "created_at": "2025-06-01T12:00:00"
        }
      ]
    }
  ]
}
```

**Response (404):**
```json
{
  "detail": "Politician not found"
}
```

**Example:**
```bash
curl http://localhost:9847/api/politicians/1
```

---

### POST /api/politicians

Create a new politician.

**Auth Required**: Yes

**Request Body:**
```json
{
  "name": "Jane Smith",
  "party": "Democrat",
  "office": "U.S. Senator",
  "state": "California",
  "photo_url": "https://example.com/photo.jpg"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Full name |
| `party` | string | Yes | Political party |
| `office` | string | Yes | Current office/title |
| `state` | string or null | No | U.S. state |
| `photo_url` | string or null | No | URL to profile photo |

**Response (201):**
```json
{
  "id": 1,
  "name": "Jane Smith",
  "party": "Democrat",
  "office": "U.S. Senator",
  "state": "California",
  "photo_url": "https://example.com/photo.jpg",
  "created_at": "2025-06-01T12:00:00",
  "updated_at": "2025-06-01T12:00:00"
}
```

**Example:**
```bash
curl -X POST http://localhost:9847/api/politicians \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "name": "Jane Smith",
    "party": "Democrat",
    "office": "U.S. Senator",
    "state": "California",
    "photo_url": null
  }'
```

---

### PUT /api/politicians/{politician_id}

Update an existing politician.

**Auth Required**: Yes

**Path Parameters:**
| Parameter | Type | Description |
|---|---|---|
| `politician_id` | integer | Politician ID |

**Request Body:** Same schema as POST.

**Response (200):** Updated `PoliticianOut` object.

**Response (404):**
```json
{
  "detail": "Politician not found"
}
```

**Example:**
```bash
curl -X PUT http://localhost:9847/api/politicians/1 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "name": "Jane Smith",
    "party": "Democrat",
    "office": "Governor",
    "state": "California",
    "photo_url": null
  }'
```

---

### DELETE /api/politicians/{politician_id}

Delete a politician. **This cascades**: all statements belonging to this politician will also be deleted.

**Auth Required**: Yes

**Path Parameters:**
| Parameter | Type | Description |
|---|---|---|
| `politician_id` | integer | Politician ID |

**Response (204):** No content.

**Response (404):**
```json
{
  "detail": "Politician not found"
}
```

**Example:**
```bash
curl -X DELETE http://localhost:9847/api/politicians/1 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Issue Endpoints

### GET /api/issues

List all issues with pagination.

**Auth Required**: No

**Query Parameters:**
| Parameter | Type | Default | Description |
|---|---|---|---|
| `skip` | integer | `0` | Offset |
| `limit` | integer | `50` | Max results (1-200) |

**Response (200):**
```json
{
  "items": [
    {
      "id": 1,
      "name": "Climate Change",
      "description": "Environmental policy and climate legislation",
      "created_at": "2025-06-01T12:00:00"
    }
  ],
  "total": 1,
  "skip": 0,
  "limit": 50
}
```

**Example:**
```bash
curl http://localhost:9847/api/issues
```

---

### GET /api/issues/{issue_id}

Get a single issue with all tagged statements.

**Auth Required**: No

**Path Parameters:**
| Parameter | Type | Description |
|---|---|---|
| `issue_id` | integer | Issue ID |

**Response (200):**
```json
{
  "id": 1,
  "name": "Climate Change",
  "description": "Environmental policy and climate legislation",
  "created_at": "2025-06-01T12:00:00",
  "statements": [
    {
      "id": 1,
      "politician_id": 1,
      "title": "Senator calls for new climate legislation",
      "analysis": "Analysis text...",
      "post_url": "https://x.com/user/status/123",
      "post_platform": "X",
      "post_content": "Original post text...",
      "screenshot_url": null,
      "post_date": "2025-05-15T00:00:00",
      "created_at": "2025-06-01T12:00:00",
      "updated_at": "2025-06-01T12:00:00",
      "politician": { ... },
      "issues": [ ... ]
    }
  ]
}
```

**Response (404):**
```json
{
  "detail": "Issue not found"
}
```

**Example:**
```bash
curl http://localhost:9847/api/issues/1
```

---

### POST /api/issues

Create a new issue.

**Auth Required**: Yes

**Request Body:**
```json
{
  "name": "Climate Change",
  "description": "Environmental policy and climate legislation"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Issue name (must be unique) |
| `description` | string or null | No | Description of the issue |

**Response (201):**
```json
{
  "id": 1,
  "name": "Climate Change",
  "description": "Environmental policy and climate legislation",
  "created_at": "2025-06-01T12:00:00"
}
```

**Example:**
```bash
curl -X POST http://localhost:9847/api/issues \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"name": "Climate Change", "description": "Environmental policy and climate legislation"}'
```

---

### PUT /api/issues/{issue_id}

Update an existing issue.

**Auth Required**: Yes

**Path Parameters:**
| Parameter | Type | Description |
|---|---|---|
| `issue_id` | integer | Issue ID |

**Request Body:** Same schema as POST.

**Response (200):** Updated `IssueOut` object.

**Response (404):**
```json
{
  "detail": "Issue not found"
}
```

**Example:**
```bash
curl -X PUT http://localhost:9847/api/issues/1 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"name": "Climate Policy", "description": "Updated description"}'
```

---

### DELETE /api/issues/{issue_id}

Delete an issue. The issue is removed from the `statement_issues` association table (via `ON DELETE CASCADE`), but the statements themselves are not deleted.

**Auth Required**: Yes

**Path Parameters:**
| Parameter | Type | Description |
|---|---|---|
| `issue_id` | integer | Issue ID |

**Response (204):** No content.

**Response (404):**
```json
{
  "detail": "Issue not found"
}
```

**Example:**
```bash
curl -X DELETE http://localhost:9847/api/issues/1 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Statement Endpoints

### GET /api/statements

List statements with pagination and optional filters.

**Auth Required**: No

**Query Parameters:**
| Parameter | Type | Default | Description |
|---|---|---|---|
| `politician_id` | integer | -- | Filter by politician ID |
| `issue_id` | integer | -- | Filter by issue ID (statements tagged with this issue) |
| `platform` | string | -- | Filter by platform (e.g., "X", "YouTube", "Bluesky", "Truth Social") |
| `search` | string | -- | Search in title, analysis, and post content (case-insensitive, partial match) |
| `sort` | string | `newest` | Ordering: `newest`, `oldest`, or `politician-az`. Any other value returns 422 |
| `skip` | integer | `0` | Offset |
| `limit` | integer | `50` | Max results (1-200) |

**Ordering**

Sorting is applied in the database, before `skip`/`limit` cut the page, so a
page of `oldest` results is the oldest of the whole matching set rather than
the oldest of one page.

| `sort` | Order |
|---|---|
| `newest` (default) | Post date descending, falling back to creation date when a statement has no `post_date` |
| `oldest` | The same date ascending |
| `politician-az` | Politician name A-Z, then that politician's statements newest first |

Every ordering ends with a unique tiebreaker on `id`, so statements sharing a
date keep a stable position across paged requests.

Note: the default order uses the post date where one exists. Previously it used
the creation date only, which meant a statement recorded today about a post from
last year sorted as though it were new.

**Response (200):**
```json
{
  "items": [
    {
      "id": 1,
      "politician_id": 1,
      "title": "Senator calls for new climate legislation",
      "analysis": "Full analysis text...",
      "post_url": "https://x.com/user/status/123",
      "post_platform": "X",
      "post_content": "Original post text...",
      "screenshot_url": "/uploads/abc123.png",
      "post_date": "2025-05-15T00:00:00",
      "created_at": "2025-06-01T12:00:00",
      "updated_at": "2025-06-01T12:00:00",
      "politician": {
        "id": 1,
        "name": "Jane Smith",
        "party": "Democrat",
        "office": "U.S. Senator",
        "state": "California",
        "photo_url": null,
        "created_at": "2025-06-01T12:00:00",
        "updated_at": "2025-06-01T12:00:00"
      },
      "issues": [
        {
          "id": 1,
          "name": "Climate Change",
          "description": "Environmental policy",
          "created_at": "2025-06-01T12:00:00"
        }
      ]
    }
  ],
  "total": 1,
  "skip": 0,
  "limit": 50
}
```

**Note:** The list endpoint returns `StatementListOut`, which does NOT include `sources`. Use the single-statement endpoint to get sources.

**Examples:**
```bash
# All statements
curl http://localhost:9847/api/statements

# Filter by politician
curl http://localhost:9847/api/statements?politician_id=1

# Filter by issue
curl http://localhost:9847/api/statements?issue_id=2

# Search
curl http://localhost:9847/api/statements?search=climate

# Combined filters with pagination
curl "http://localhost:9847/api/statements?politician_id=1&issue_id=2&search=climate&skip=0&limit=10"
```

---

### GET /api/statements/{statement_id}

Get a single statement with full details including sources.

**Auth Required**: No

**Path Parameters:**
| Parameter | Type | Description |
|---|---|---|
| `statement_id` | integer | Statement ID |

**Response (200):**
```json
{
  "id": 1,
  "politician_id": 1,
  "title": "Senator calls for new climate legislation",
  "analysis": "Full analysis text with **markdown** support...",
  "post_url": "https://x.com/user/status/123",
  "post_platform": "X",
  "post_content": "Original post text...",
  "screenshot_url": "/uploads/abc123.png",
  "post_date": "2025-05-15T00:00:00",
  "created_at": "2025-06-01T12:00:00",
  "updated_at": "2025-06-01T12:00:00",
  "politician": {
    "id": 1,
    "name": "Jane Smith",
    "party": "Democrat",
    "office": "U.S. Senator",
    "state": "California",
    "photo_url": null,
    "created_at": "2025-06-01T12:00:00",
    "updated_at": "2025-06-01T12:00:00"
  },
  "issues": [
    {
      "id": 1,
      "name": "Climate Change",
      "description": "Environmental policy",
      "created_at": "2025-06-01T12:00:00"
    }
  ],
  "sources": [
    {
      "id": 1,
      "source_type": "post",
      "title": "Original news article",
      "url": "https://example.com/article",
      "description": "The article the senator was responding to"
    },
    {
      "id": 2,
      "source_type": "analysis",
      "title": "Constitutional law reference",
      "url": "https://example.com/law",
      "description": null
    }
  ]
}
```

**Response (404):**
```json
{
  "detail": "Statement not found"
}
```

**Example:**
```bash
curl http://localhost:9847/api/statements/1
```

---

### POST /api/statements

Create a new statement.

**Auth Required**: Yes

**Request Body:**
```json
{
  "politician_id": 1,
  "issue_ids": [1, 2],
  "title": "Senator calls for new climate legislation",
  "analysis": "Analysis text with **markdown** support...",
  "post_url": "https://x.com/user/status/123",
  "post_platform": "X",
  "post_content": "Original post text...",
  "screenshot_url": "/uploads/abc123.png",
  "post_date": "2025-05-15T00:00:00",
  "sources": [
    {
      "source_type": "post",
      "title": "Original news article",
      "url": "https://example.com/article",
      "description": "The article the senator was responding to"
    },
    {
      "source_type": "analysis",
      "title": "Constitutional law reference",
      "url": "https://example.com/law",
      "description": ""
    }
  ]
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `politician_id` | integer | Yes | ID of the politician |
| `issue_ids` | array of integers | No (default `[]`) | IDs of issues to tag |
| `title` | string | Yes | Statement title |
| `analysis` | string | Yes | Analysis text (supports Markdown) |
| `post_url` | string | Yes | URL to the original post |
| `post_platform` | string | Yes | Platform: "X", "Bluesky", "Truth Social", "YouTube" |
| `post_content` | string or null | No | Quoted text from the post |
| `screenshot_url` | string or null | No | URL to screenshot image |
| `post_date` | datetime or null | No | Date of the original post |
| `sources` | array of SourceCreate | No (default `[]`) | Citation sources |

**Source object:**
| Field | Type | Required | Description |
|---|---|---|---|
| `uid` | string or null | No | Supply the existing `uid` when editing a source so it is updated in place and its citations keep working. Omit for a new source; one is assigned |
| `source_type` | string | Yes | `"post"` or `"analysis"` |
| `title` | string | Yes | Source title/label |
| `url` | string | Yes | URL to the source. Must be an absolute `http://` or `https://` URL |
| `description` | string or null | No | Brief editorial note |
| `media_type` | string | No (default `"webpage"`) | One of `webpage`, `document`, `video`, `audio`, `article`, `dataset`. Selects how the source is embedded |
| `publisher` | string or null | No | Issuing body, e.g. `"Congress.gov"` |
| `published_date` | datetime or null | No | When the source was published |
| `excerpt` | string or null | No | Verbatim passage being relied on |
| `locator` | string or null | No | Where the excerpt lives: `"p. 14"`, `"sec. 203"`, `"01:23:45"`. A timestamp locator starts a video embed at that point |
| `archive_url` | string or null | No | Snapshot URL. Must be absolute `http(s)` when present |
| `archived_at` | datetime or null | No | When the snapshot was taken |
| `retrieved_at` | datetime or null | No | When the original was last confirmed |

Responses also include `id` and `sort_order`. `sort_order` is derived from the
order sources are submitted in and is not read from the request.

**Validation (422):** returned when `url`, `archive_url` or `post_url` is not an
absolute http(s) URL, or when `media_type`/`source_type` is not one of the values
above.

**Response (201):** Full `StatementOut` object (includes politician, issues, sources).

**Response (400):**
```json
{
  "detail": "One or more issue IDs are invalid"
}
```

**Example:**
```bash
curl -X POST http://localhost:9847/api/statements \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "politician_id": 1,
    "issue_ids": [1],
    "title": "Senator calls for new climate legislation",
    "analysis": "This statement represents a significant shift...",
    "post_url": "https://x.com/user/status/123",
    "post_platform": "X",
    "post_content": "We need to act now on climate change.",
    "screenshot_url": null,
    "post_date": "2025-05-15",
    "sources": []
  }'
```

---

### PUT /api/statements/{statement_id}

Update an existing statement. Sources are reconciled by `uid`: a source
submitted with a `uid` belonging to this statement is updated in place, one
without a `uid` is created, and any existing source whose `uid` is absent from
the submission is deleted. Submit the `uid` values returned by `GET
/api/statements/{id}` to keep citation markers and `#source-<uid>` links
working across the edit.

**Auth Required**: Yes

**Path Parameters:**
| Parameter | Type | Description |
|---|---|---|
| `statement_id` | integer | Statement ID |

**Request Body:** Same schema as POST.

**Response (200):** Updated `StatementOut` object.

**Response (404):**
```json
{
  "detail": "Statement not found"
}
```

**Response (400):**
```json
{
  "detail": "One or more issue IDs are invalid"
}
```

**Example:**
```bash
curl -X PUT http://localhost:9847/api/statements/1 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "politician_id": 1,
    "issue_ids": [1, 3],
    "title": "Updated title",
    "analysis": "Updated analysis...",
    "post_url": "https://x.com/user/status/123",
    "post_platform": "X",
    "post_content": "Updated content...",
    "screenshot_url": null,
    "post_date": "2025-05-15",
    "sources": [
      {
        "source_type": "analysis",
        "title": "New source",
        "url": "https://example.com/new",
        "description": ""
      }
    ]
  }'
```

---

### DELETE /api/statements/{statement_id}

Delete a statement and all its sources.

---

### POST /api/statements/{statement_id}/sources/{uid}/archive

Capture a Wayback Machine snapshot for one source and store it on that source.

**Auth Required**: Yes

Works whether or not `ARCHIVE_ENABLED` is set, so a deployment that keeps
automatic archiving off can still archive deliberately, and a source whose
automatic capture failed can be retried without re-saving the statement.

**Response (200):**
```json
{
  "archive_url": "https://web.archive.org/web/20260114000000/https://congress.gov/bill",
  "archived_at": "2026-01-14T00:00:00"
}
```

**Response (400):** the source URL cannot be archived (not `http(s)`, or already a Wayback snapshot).

**Response (404):** no source with that `uid` belongs to this statement.

**Response (502):** the archive service could not be reached or refused the capture. The source is left unchanged.

**Auth Required**: Yes

**Path Parameters:**
| Parameter | Type | Description |
|---|---|---|
| `statement_id` | integer | Statement ID |

**Response (204):** No content.

**Response (404):**
```json
{
  "detail": "Statement not found"
}
```

**Example:**
```bash
curl -X DELETE http://localhost:9847/api/statements/1 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Upload Endpoint

### POST /api/uploads

Upload an image file. The file is saved with a UUID-based filename and served as a static file.

**Auth Required**: Yes

**Content-Type**: `multipart/form-data`

**Form Fields:**
| Field | Type | Description |
|---|---|---|
| `file` | file | Image file to upload |

**Allowed Extensions**: `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`, `.svg`

**Response (200):**
```json
{
  "url": "/uploads/a1b2c3d4e5f6.png"
}
```

**Response (400):**
```json
{
  "detail": "File type '.pdf' not allowed. Allowed: .png, .jpg, .jpeg, .gif, .webp, .svg"
}
```

**Example:**
```bash
curl -X POST http://localhost:9847/api/uploads \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@screenshot.png"
```

**Notes:**
- The returned URL path (e.g., `/uploads/a1b2c3d4e5f6.png`) can be used directly as the `screenshot_url` when creating or updating a statement.
- Files are stored in `/app/data/uploads/` inside the Docker container (persistent volume).
- Filenames are UUIDs to prevent collisions and path traversal.

---

## Export Endpoint

### GET /api/export

Export all data as a single JSON object containing all politicians, issues, and statements.

**Auth Required**: Yes

**Response (200):**
```json
{
  "politicians": [
    {
      "id": 1,
      "name": "Jane Smith",
      "party": "Democrat",
      "office": "U.S. Senator",
      "state": "California",
      "photo_url": null,
      "created_at": "2025-06-01T12:00:00",
      "updated_at": "2025-06-01T12:00:00"
    }
  ],
  "issues": [
    {
      "id": 1,
      "name": "Climate Change",
      "description": "Environmental policy",
      "created_at": "2025-06-01T12:00:00"
    }
  ],
  "statements": [
    {
      "id": 1,
      "politician_id": 1,
      "title": "Senator calls for new climate legislation",
      "analysis": "Analysis text...",
      "post_url": "https://x.com/user/status/123",
      "post_platform": "X",
      "post_content": "Original post text...",
      "screenshot_url": null,
      "post_date": "2025-05-15T00:00:00",
      "created_at": "2025-06-01T12:00:00",
      "updated_at": "2025-06-01T12:00:00",
      "politician": { ... },
      "issues": [ ... ],
      "sources": [ ... ]
    }
  ]
}
```

**Notes:**
- Politicians are sorted alphabetically by name.
- Issues are sorted alphabetically by name.
- Statements are sorted by creation date (newest first).
- Each statement includes nested `politician`, `issues`, and `sources` objects.

**Example:**
```bash
curl http://localhost:9847/api/export \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -o export.json
```

---

## Import Endpoint

### POST /api/import

Import data from a JSON backup file. Merges with existing data — duplicate politicians (by name), issues (by name), and statements (by title + politician) are skipped.

**Auth Required**: Yes

**Request Body:**
```json
{
  "politicians": [
    {"id": 1, "name": "John Smith", "party": "Democrat", "office": "U.S. Senator", "state": "California", "photo_url": null}
  ],
  "issues": [
    {"id": 1, "name": "First Amendment", "description": "Freedom of speech issues"}
  ],
  "statements": [
    {
      "id": 1,
      "politician_id": 1,
      "title": "Statement Title",
      "analysis": "Analysis text...",
      "post_url": "https://x.com/...",
      "post_platform": "X",
      "post_content": "Quoted text",
      "screenshot_url": null,
      "post_date": "2025-01-15T00:00:00",
      "issues": [{"id": 1, "name": "First Amendment"}],
      "sources": [
        {"source_type": "post", "title": "Source", "url": "https://...", "description": "desc"}
      ]
    }
  ]
}
```

> **Note:** The request body format matches the output of `GET /api/export`, so you can directly import a previously exported backup.

**Response (200):**
```json
{
  "message": "Import complete",
  "imported": {
    "politicians": 1,
    "issues": 0,
    "statements": 1,
    "sources": 2
  }
}
```

The `imported` object shows how many new records were created. Items that already existed (duplicates) are skipped and not counted.

**Example:**
```bash
curl -X POST http://localhost:9847/api/import \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d @backup.json
```

---

## Health Endpoint

### GET /api/health

Health check endpoint. Used by the Docker `HEALTHCHECK` instruction to monitor container health.

**Auth Required**: No

**Response (200):**
```json
{
  "status": "ok"
}
```

**Example:**
```bash
curl http://localhost:9847/api/health
```
