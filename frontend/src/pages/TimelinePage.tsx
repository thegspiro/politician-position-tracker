import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { fetchStatements, fetchPoliticians, fetchIssues } from '../api';
import type { Statement, Politician, Issue, StatementSort } from '../types';

function partyBadgeClass(party: string): string {
  const p = party.toLowerCase();
  if (p.includes('democrat')) return 'bg-blue-600 text-white';
  if (p.includes('republican')) return 'bg-red-600 text-white';
  return 'bg-gray-500 text-white';
}

function platformIcon(platform: string): React.ReactNode {
  const p = platform.toLowerCase();
  const baseClass = 'w-4 h-4 inline-block';
  if (p === 'twitter' || p === 'x') {
    return (
      <svg className={baseClass} viewBox="0 0 24 24" fill="currentColor">
        <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
      </svg>
    );
  }
  if (p === 'facebook') {
    return (
      <svg className={baseClass} viewBox="0 0 24 24" fill="currentColor">
        <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z" />
      </svg>
    );
  }
  if (p === 'instagram') {
    return (
      <svg className={baseClass} viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zM12 0C8.741 0 8.333.014 7.053.072 2.695.272.273 2.69.073 7.052.014 8.333 0 8.741 0 12c0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98C8.333 23.986 8.741 24 12 24c3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98C15.668.014 15.259 0 12 0zm0 5.838a6.162 6.162 0 100 12.324 6.162 6.162 0 000-12.324zM12 16a4 4 0 110-8 4 4 0 010 8zm6.406-11.845a1.44 1.44 0 100 2.881 1.44 1.44 0 000-2.881z" />
      </svg>
    );
  }
  if (p === 'youtube') {
    return (
      <svg className={baseClass} viewBox="0 0 24 24" fill="currentColor">
        <path d="M23.498 6.186a3.016 3.016 0 00-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 00.502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 002.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 002.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z" />
      </svg>
    );
  }
  if (p === 'bluesky') {
    return (
      <svg className={baseClass} viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 10.8c-1.087-2.114-4.046-6.053-6.798-7.995C2.566.944 1.561 1.266.902 1.565.139 1.908 0 3.08 0 3.768c0 .69.378 5.65.624 6.479.785 2.627 3.6 3.502 6.204 3.17-4.024.578-7.577 2.199-3.844 7.683 4.245 5.709 7.672-.927 9.016-5.27.344-1.108.508-1.627.508-1.188 0-.44.164.08.508 1.188 1.344 4.343 4.771 10.979 9.016 5.27 3.733-5.484.18-7.105-3.844-7.683 2.604.332 5.42-.543 6.204-3.17.246-.828.624-5.79.624-6.479 0-.688-.139-1.86-.902-2.203-.66-.299-1.664-.62-4.3 1.24C16.046 4.748 13.087 8.687 12 10.8z" />
      </svg>
    );
  }
  if (p === 'truth social') {
    return (
      <span className={`${baseClass} font-bold text-sm leading-4 text-center`}>T</span>
    );
  }
  // Generic link icon
  return (
    <svg className={baseClass} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
    </svg>
  );
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return 'Unknown date';
  return new Date(dateStr).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
}

function snippetText(text: string, maxLen = 180): string {
  if (text.length <= maxLen) return text;
  return text.slice(0, maxLen).trimEnd() + '...';
}

export default function TimelinePage() {
  const [statements, setStatements] = useState<Statement[]>([]);
  const [totalResults, setTotalResults] = useState(0);
  const [politicians, setPoliticians] = useState<Politician[]>([]);
  const [issues, setIssues] = useState<Issue[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [search, setSearch] = useState('');
  const [selectedPolitician, setSelectedPolitician] = useState('');
  const [selectedIssue, setSelectedIssue] = useState('');
  const [sortBy, setSortBy] = useState<StatementSort>('newest');

  // Load filter options on mount
  useEffect(() => {
    Promise.all([fetchPoliticians(), fetchIssues()])
      .then(([polsRes, issRes]) => {
        setPoliticians(polsRes.items);
        setIssues(issRes.items);
      })
      .catch(() => {
        // Non-critical: filters just won't be populated
      });
  }, []);

  const loadStatements = useCallback(() => {
    setLoading(true);
    setError(null);
    fetchStatements({
      search: search || undefined,
      politician_id: selectedPolitician || undefined,
      issue_id: selectedIssue || undefined,
      sort: sortBy,
    })
      .then((data) => {
        setStatements(data.items);
        setTotalResults(data.total);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : 'Failed to load statements');
      })
      .finally(() => setLoading(false));
  }, [search, selectedPolitician, selectedIssue, sortBy]);

  useEffect(() => {
    loadStatements();
  }, [loadStatements]);

  // Debounced search
  const [searchInput, setSearchInput] = useState('');
  useEffect(() => {
    const timer = setTimeout(() => setSearch(searchInput), 400);
    return () => clearTimeout(timer);
  }, [searchInput]);

  // Sorting happens in the database. Reordering here would only reorder the
  // page already loaded, so "oldest" would show the oldest of the newest page.

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 py-8">
      <h1 className="text-3xl font-bold text-[var(--color-text)] mb-6">Timeline</h1>

      {/* Search and filters */}
      <div className="flex flex-col sm:flex-row gap-3 mb-4">
        <div className="flex-1 relative">
          <svg
            className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--color-text-secondary)]"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            type="text"
            placeholder="Search statements..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] text-[var(--color-text)] placeholder:text-[var(--color-text-secondary)] focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)] transition"
          />
        </div>
        <select
          value={selectedPolitician}
          onChange={(e) => setSelectedPolitician(e.target.value)}
          className="px-3 py-2.5 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] text-[var(--color-text)] focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)] transition"
        >
          <option value="">All politicians</option>
          {politicians.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
        <select
          value={selectedIssue}
          onChange={(e) => setSelectedIssue(e.target.value)}
          className="px-3 py-2.5 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] text-[var(--color-text)] focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)] transition"
        >
          <option value="">All issues</option>
          {issues.map((i) => (
            <option key={i.id} value={i.id}>
              {i.name}
            </option>
          ))}
        </select>
      </div>

      {/* Sort dropdown + results count */}
      <div className="flex items-center justify-between mb-8">
        <p className="text-sm text-[var(--color-text-secondary)]">
          {!loading && !error && `Showing ${statements.length} of ${totalResults} results`}
        </p>
        <select
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value as StatementSort)}
          className="px-3 py-2 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] text-[var(--color-text)] text-sm focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)] transition"
        >
          <option value="newest">Newest First</option>
          <option value="oldest">Oldest First</option>
          <option value="politician-az">Politician A-Z</option>
        </select>
      </div>

      {/* Loading */}
      {loading && (
        <div className="flex justify-center py-16">
          <div className="w-8 h-8 border-4 border-[var(--color-border)] border-t-[var(--color-accent)] rounded-full animate-spin" />
        </div>
      )}

      {/* Error */}
      {error && !loading && (
        <div className="text-center py-16">
          <p className="text-[var(--color-danger)] mb-4">{error}</p>
          <button
            onClick={loadStatements}
            className="px-4 py-2 bg-[var(--color-accent)] text-white rounded-lg hover:bg-[var(--color-accent-hover)] transition"
          >
            Retry
          </button>
        </div>
      )}

      {/* Empty */}
      {!loading && !error && statements.length === 0 && (
        <div className="text-center py-16">
          <p className="text-[var(--color-text-secondary)] text-lg">No statements found.</p>
          {(search || selectedPolitician || selectedIssue) && (
            <p className="text-[var(--color-text-secondary)] text-sm mt-2">
              Try adjusting your search or filters.
            </p>
          )}
        </div>
      )}

      {/* Timeline feed */}
      {!loading && !error && statements.length > 0 && (
        <div className="relative">
          {/* Vertical line */}
          <div className="absolute left-4 top-0 bottom-0 w-px bg-[var(--color-border)]" />

          <div className="space-y-6">
            {statements.map((stmt) => (
              <div key={stmt.id} className="relative pl-10">
                {/* Dot on timeline */}
                <div className="absolute left-2.5 top-6 w-3 h-3 rounded-full bg-[var(--color-accent)] ring-4 ring-[var(--color-bg)]" />

                <div className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-xl p-5 transition hover:border-[var(--color-accent)]">
                  {/* Header row */}
                  <div className="flex flex-wrap items-center gap-2 mb-2">
                    <span className="font-semibold text-[var(--color-text)]">
                      {stmt.politician.name}
                    </span>
                    <span
                      className={`text-xs font-medium px-2 py-0.5 rounded-full ${partyBadgeClass(stmt.politician.party)}`}
                    >
                      {stmt.politician.party}
                    </span>
                    {stmt.issues.map((issue) => (
                      <span
                        key={issue.id}
                        className="text-xs font-medium px-2 py-0.5 rounded-full bg-[var(--color-badge-bg)] text-[var(--color-badge-text)]"
                      >
                        {issue.name}
                      </span>
                    ))}
                    <span className="ml-auto flex items-center gap-1 text-[var(--color-text-secondary)]">
                      {platformIcon(stmt.post_platform)}
                      <span className="text-xs">{stmt.post_platform}</span>
                    </span>
                  </div>

                  {/* Title */}
                  <h3 className="text-lg font-semibold text-[var(--color-text)] mb-1">
                    {stmt.title}
                  </h3>

                  {/* Date */}
                  <p className="text-xs text-[var(--color-text-secondary)] mb-3">
                    {formatDate(stmt.post_date ?? stmt.created_at)}
                  </p>

                  {/* Analysis snippet */}
                  <p className="text-sm text-[var(--color-text-secondary)] leading-relaxed mb-3">
                    {snippetText(stmt.analysis)}
                  </p>

                  {/* Read more link */}
                  <Link
                    to={`/statements/${stmt.id}`}
                    className="text-sm font-medium text-[var(--color-accent)] hover:text-[var(--color-accent-hover)] transition"
                  >
                    Read more &rarr;
                  </Link>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
