# Politician Position Tracker -- Training Guide

This guide walks you through every feature of the Politician Position Tracker, from first login to advanced usage. It is intended for end users who will be adding and managing content in the application.

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Admin Dashboard Overview](#admin-dashboard-overview)
3. [Adding a Politician](#adding-a-politician)
4. [Adding an Issue](#adding-an-issue)
5. [Adding a Statement](#adding-a-statement)
6. [Editing and Deleting Entries](#editing-and-deleting-entries)
7. [Browsing the Public Site](#browsing-the-public-site)
8. [Using Sort and Filter Features](#using-sort-and-filter-features)
9. [Exporting Data](#exporting-data)
10. [Sharing Statements](#sharing-statements)
11. [Light/Dark Mode Toggle](#lightdark-mode-toggle)

---

## Getting Started

### Accessing the Site

Open your web browser and navigate to the URL where the application is hosted. If you are running it locally with Docker Compose, the default address is:

```
http://localhost:9847
```

If running on an Unraid server, replace `localhost` with your server's IP address (e.g., `http://192.168.1.100:9847`).

### First Login

To manage content (add, edit, or delete politicians, issues, and statements), you need to log into the admin panel.

1. Click **Admin** in the top navigation bar.
2. You will see the **Admin Login** page with a single password field.

[Screenshot needed: Login page]

3. Enter the admin password. There is no default: it was chosen when the application was installed. If you do not know it, check the `ADMIN_PASSWORD` environment variable in the Docker configuration.

   Sessions last 12 hours by default, after which you will be asked to log in again. After five failed attempts, further logins from your address are refused for 15 minutes.
4. Click **Login**.
5. If the password is correct, you will be redirected to the Admin Dashboard. If incorrect, an error message will appear.

Your login session persists until you click **Logout** or clear your browser data. You do not need to log in again each time you visit the site.

---

## Admin Dashboard Overview

After logging in, the Admin Dashboard shows three tables:

- **Politicians** -- Lists all politicians with their name, party, office, and state. Each row has Edit and Delete buttons.
- **Issues** -- Lists all issues with their name and description. Each row has Edit and Delete buttons.
- **Statements** -- Lists all statements with their title, politician, issues, and date. Each row has Edit and Delete buttons.

Each section has a **+ New** button (e.g., "+ New Politician") to create a new entry.

At the top right of the dashboard, you will find:
- **Export Data** -- Downloads all data as a JSON file (see [Exporting Data](#exporting-data))
- **Logout** -- Ends your admin session

[Screenshot needed: Admin dashboard with data]

---

## Adding a Politician

Politicians are the people whose statements you are tracking. You must add a politician before you can add statements attributed to them.

### Step-by-Step

1. From the Admin Dashboard, click **+ New Politician**.
2. Fill in the form fields:
   - **Name** (required): The politician's full name (e.g., "Jane Smith").
   - **Party** (required): Select from the dropdown: Democrat, Republican, Independent, Libertarian, Green, or Other.
   - **Office** (required): Their current position (e.g., "U.S. Senator", "Governor", "U.S. Representative").
   - **State** (optional): Select their state from the dropdown, or leave as "None" for national figures or those without a state affiliation.
   - **Photo URL** (optional): A URL to a photo of the politician. This will be displayed on their profile page and in the politicians grid. Use a direct image URL (ending in .jpg, .png, etc.).
3. Click **Create Politician**.
4. You will see a "Politician saved successfully" toast notification and be redirected to the Admin Dashboard.

[Screenshot needed: New politician form filled out]

### Edge Cases

- **Duplicate names**: The system does not prevent adding two politicians with the same name. If you accidentally create a duplicate, delete one from the Admin Dashboard.
- **Photo URL**: If the photo URL is invalid or the image cannot be loaded, a placeholder circle with the politician's first initial will be shown instead.

---

## Adding an Issue

Issues are the topics or themes you use to categorize statements. Examples: "Climate Change", "Immigration", "First Amendment", "Healthcare".

### Step-by-Step

1. From the Admin Dashboard, click **+ New Issue**.
2. Fill in the form fields:
   - **Name** (required): A short, descriptive name for the issue (e.g., "Climate Change").
   - **Description** (optional): A longer explanation of what this issue covers.
3. Click **Create Issue**.
4. You will see a "Issue saved successfully" toast notification and be redirected to the Admin Dashboard.

[Screenshot needed: New issue form]

### Edge Cases

- **Unique names**: Issue names must be unique. If you try to create an issue with a name that already exists, the server will return an error. Use a different name or edit the existing issue instead.
- **Description**: The description is displayed on the public issue detail page. Even though it is optional, adding a description helps visitors understand what the issue covers.

---

## Adding a Statement

Statements are the core content of the application. Each statement links a politician to a social media post, provides analysis, and is tagged with one or more issues.

### Full Walkthrough

1. From the Admin Dashboard, click **+ New Statement**.
2. The form has several sections. Fill them out in order:

#### Selecting a Politician

- **Politician** (required): Select the politician from the dropdown. The dropdown shows all politicians you have added, in the format "Name (Party)".
- If the politician is not in the list, cancel and add the politician first.

#### Selecting Issues

- **Issues** (required): Click one or more issue buttons to tag this statement. Selected issues are highlighted with the accent color. Click again to deselect.
- At least one issue must be selected.

[Screenshot needed: Statement form with issue toggle buttons]

#### Post Information

- **Title** (required): A descriptive headline for the statement (e.g., "Senator calls for repeal of environmental protections").
- **Post URL** (required): The full URL to the original social media post. This is what will be embedded on the statement detail page.
- **Post Platform** (required): Select the platform where the post was made: X, Bluesky, Truth Social, or YouTube.
- **Post Content** (optional): Copy and paste the text of the original post. This serves as a backup in case the post is deleted, and is also used for search.
- **Post Date** (optional): The date the original post was published. If left blank, the statement creation date will be used for sorting.

#### Entering the Post URL and Selecting the Platform

The post URL and platform must match for embeds to work correctly:

| Platform | Expected URL Format | Example |
|---|---|---|
| X | `https://x.com/{user}/status/{id}` or `https://twitter.com/{user}/status/{id}` | `https://x.com/user/status/1234567890` |
| YouTube | `https://www.youtube.com/watch?v={id}` or `https://youtu.be/{id}` | `https://www.youtube.com/watch?v=dQw4w9WgXcQ` |
| Bluesky | `https://bsky.app/profile/{handle}/post/{rkey}` | `https://bsky.app/profile/user.bsky.social/post/abc123` |
| Truth Social | `https://truthsocial.com/@{user}/posts/{id}` | `https://truthsocial.com/@user/posts/123456` |

#### Uploading a Screenshot

- **Screenshot URL**: You can either enter a URL to an externally hosted screenshot, or upload one directly.
- To upload a screenshot:
  1. Click the file picker ("Choose File") and select an image from your computer.
  2. Click the **Upload** button next to the file picker.
  3. Wait for the upload to complete. The screenshot URL field will be automatically populated with the path to the uploaded file.
  4. Supported file types: PNG, JPG, JPEG, GIF, WebP, SVG.

[Screenshot needed: Screenshot upload section]

**Why upload a screenshot?** Social media posts can be deleted or edited. A screenshot provides a permanent record of what was originally posted.

#### Writing the Analysis

- **Analysis** (required): Write your analysis of the statement. This field supports **Markdown formatting**:
  - `**bold text**` for **bold text**
  - `*italic text*` for *italic text*
  - `## Heading` for section headings
  - `- item` for bullet lists
  - `1. item` for numbered lists
  - `[link text](url)` for links
  - `> quote` for blockquotes
  - `` `code` `` for inline code

#### Adding Sources

Sources are citations that support either the original post or your analysis. There are two types:

- **Post Sources**: Citations related to the original social media post (e.g., a news article that the politician was responding to, or a fact-check of the post).
- **Analysis Sources**: Citations that support your analysis (e.g., constitutional law references, previous voting records, expert opinions).

For each source type:
1. Click **+ Add Post Source** or **+ Add Analysis Source**.
2. Fill in:
   - **Source title**: A descriptive label (e.g., "Congressional Research Service report on H.R. 1234").
   - **URL**: The full URL to the source.
   - **Description** (optional): A brief note about what this source provides.
3. Add as many sources as needed. Click **Remove** to delete a source.

[Screenshot needed: Sources section with both types]

#### Saving

3. Click **Create Statement**.
4. The form validates all required fields. If any are missing, error messages appear below the respective fields.
5. On success, you will see a "Statement saved!" toast notification and be redirected to the Admin Dashboard.

### Edge Cases

- **Original post deleted**: If the original social media post is later deleted, the screenshot backup (if uploaded) and the quoted post content will still be available on the statement detail page. The embed will fail gracefully -- for X/Twitter, the blockquote text remains; for YouTube, nothing will be shown if the video is unavailable.
- **YouTube URL format**: YouTube embeds require the video ID to be extractable from the URL. Both `youtube.com/watch?v=VIDEO_ID` and `youtu.be/VIDEO_ID` formats work. YouTube Shorts URLs (`youtube.com/shorts/VIDEO_ID`) are not supported for embedding.
- **Empty sources**: Sources with empty title or URL fields are automatically filtered out when saving.

---

## Editing and Deleting Entries

### Editing

1. In the Admin Dashboard, find the entry you want to edit in the relevant table.
2. Click **Edit** on that row.
3. The form will be pre-filled with the existing data.
4. Make your changes and click **Update** (e.g., "Update Politician").
5. You will see a success toast and be redirected to the Admin Dashboard.

[Screenshot needed: Edit button in admin table]

### Deleting

1. In the Admin Dashboard, click **Delete** on the row you want to remove.
2. A confirmation dialog will appear.

**Important cascade behaviors:**

- **Deleting a Politician**: All statements attributed to that politician will also be deleted. The confirmation dialog will tell you exactly how many statements will be affected:
  > Delete politician "Jane Smith"? This will also delete 5 statements. Are you sure?

- **Deleting an Issue**: The issue will be removed from all statements that reference it, but the statements themselves are NOT deleted. The confirmation dialog will tell you how many statements are affected:
  > Delete issue "Climate Change"? 3 statements tagged with this issue will be affected. Are you sure?

- **Deleting a Statement**: Only that statement and its sources are deleted. No other records are affected:
  > Delete statement "Senator calls for..."? This cannot be undone.

3. Click **OK** to confirm or **Cancel** to abort.
4. On success, you will see a success toast and the table will refresh.

---

## Browsing the Public Site

The public site is accessible to anyone without logging in. It includes the following pages:

### Timeline

The Timeline is the home page (`/`). It shows all statements in a vertical timeline format with:

- A dot on the timeline line for each statement
- Politician name and party badge
- Issue badges for each tagged issue
- Platform icon and name
- Statement title
- Post date
- Analysis snippet (first ~180 characters)
- "Read more" link to the full statement

[Screenshot needed: Timeline page with filters]

At the top of the Timeline:
- A **search bar** to filter statements by text (searches title, analysis, and post content)
- A **politician dropdown** to filter by politician
- An **issue dropdown** to filter by issue
- A **sort dropdown** (see [Using Sort and Filter Features](#using-sort-and-filter-features))

### Politician Profiles

The Politicians page (`/politicians`) shows a grid of all politicians with:
- Photo (or initial placeholder)
- Name
- Party badge
- Office
- State

Clicking a politician opens their detail page (`/politicians/:id`), which shows:
- Full profile header with photo, name, party, office, and state
- A list of all their statements, sorted by date

[Screenshot needed: Politician detail page]

### Issue Pages

The Issues page (`/issues`) shows a grid of all issues with:
- Issue name
- Description snippet

Clicking an issue opens its detail page (`/issues/:id`), which shows:
- Issue name and full description
- A list of all statements tagged with that issue

### Statement Detail

Clicking "Read more" on any statement card opens the full statement detail page (`/statements/:id`). This page includes:

- **Politician info**: Name (linked to profile), party badge, office
- **Issue badges**: Linked to their respective issue pages
- **Title and date**
- **Social media embed**: The original post embedded directly on the page (see [Social Media Embeds](#social-embed-integration) in the Wiki for details on how each platform's embed works)
- **Screenshot**: If a screenshot was uploaded, it appears below the embed
- **Analysis**: Full analysis text rendered as Markdown
- **Post Sources**: Citation list for the original post
- **Analysis Sources**: Citation list for the analysis
- **Share buttons**: Share the statement via social media or copy the link

[Screenshot needed: Statement detail with YouTube embed]

---

## Using Sort and Filter Features

The Timeline page provides several ways to find and organize statements.

### Search

Type in the search bar to filter statements. The search checks:
- Statement titles
- Analysis text
- Post content (quoted text from the original post)

Search is case-insensitive and uses partial matching (e.g., searching "climate" will match "Climate Change legislation" in any of those fields). There is a brief delay (400ms) after you stop typing before the search executes, so you can type without triggering a request for every keystroke.

### Filter by Politician

Select a politician from the "All politicians" dropdown to show only their statements. Select "All politicians" again to clear the filter.

### Filter by Issue

Select an issue from the "All issues" dropdown to show only statements tagged with that issue. Select "All issues" again to clear the filter.

### Sort

Use the sort dropdown to change the order of results:

- **Newest First** (default): Statements are sorted by post date (or creation date if no post date) with the most recent first.
- **Oldest First**: Same as above but reversed.
- **Politician A-Z**: Statements are sorted alphabetically by politician name.

[Screenshot needed: Sort dropdown on timeline]

### Results Count

Below the filters, a results count shows "Showing X of Y results" so you know how many statements match your current filters.

### Combining Filters

All filters can be combined. For example, you can search for "immigration" while filtering by a specific politician, sorted by oldest first.

---

## Exporting Data

The Export feature lets you download all data from the application as a single JSON file. This is useful for:

- Creating backups
- Migrating data to another instance
- Analysis in external tools

### How to Export

1. Log into the Admin Dashboard.
2. Click the **Export Data** button in the top-right corner.
3. A file named `export.json` will be downloaded to your computer.

[Screenshot needed: Export button on admin dashboard]

### What the JSON Export Contains

The export file contains three top-level arrays:

```json
{
  "politicians": [
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
  "issues": [
    {
      "id": 1,
      "name": "Climate Change",
      "description": "Environmental policy and climate legislation",
      "created_at": "2025-06-01T12:00:00"
    }
  ],
  "statements": [
    {
      "id": 1,
      "politician_id": 1,
      "title": "Senator calls for new climate legislation",
      "analysis": "Full analysis text here...",
      "post_url": "https://x.com/user/status/123",
      "post_platform": "X",
      "post_content": "Original post text...",
      "screenshot_url": "/uploads/abc123.png",
      "post_date": "2025-05-15T00:00:00",
      "created_at": "2025-06-01T12:00:00",
      "updated_at": "2025-06-01T12:00:00",
      "politician": { ... },
      "issues": [ ... ],
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
  ]
}
```

**Notes:**
- Statements include nested `politician`, `issues`, and `sources` objects for completeness.
- Screenshot URLs that point to uploaded files (e.g., `/uploads/abc123.png`) reference files stored in the Docker volume. The export does not include the actual image files -- only the database records. To fully back up uploaded images, you should also copy the `/app/data/uploads/` directory.

---

## Sharing Statements

Each statement detail page includes share buttons at the bottom, allowing you to share the statement with others.

[Screenshot needed: Share buttons on statement detail]

### Available Share Options

- **Copy Link**: Copies the statement page URL to your clipboard. A checkmark icon appears briefly to confirm the copy was successful.
- **Share on X (Twitter)**: Opens a new tab with a pre-filled tweet containing the statement title and URL.
- **Share on Facebook**: Opens the Facebook share dialog with the statement URL.
- **Share via Email**: Opens your default email client with the statement title as the subject and URL in the body.

### How It Works

The share buttons use the current page URL (`window.location.href`) and the statement title. The URL and title are URL-encoded for compatibility with each platform's sharing API.

---

## Light/Dark Mode Toggle

The application supports light and dark color themes.

### How to Toggle

Click the **sun/moon icon** in the top navigation bar (next to the navigation links on desktop, or next to the hamburger menu on mobile).

- **Sun icon**: Currently in dark mode. Click to switch to light mode.
- **Moon icon**: Currently in light mode. Click to switch to dark mode.

[Screenshot needed: Dark mode comparison]

### Automatic Detection

When you first visit the site, the theme is automatically set based on your operating system or browser preference. If your system is set to dark mode, the site will start in dark mode.

### Persistence

Your theme preference is saved in your browser's local storage. It will persist across sessions until you clear your browser data or toggle it again.
