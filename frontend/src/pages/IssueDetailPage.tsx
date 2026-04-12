import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { fetchIssue } from '../api';
import type { IssueDetail } from '../types';

function partyBadgeClass(party: string): string {
  const p = party.toLowerCase();
  if (p.includes('democrat')) return 'bg-blue-600 text-white';
  if (p.includes('republican')) return 'bg-red-600 text-white';
  return 'bg-gray-500 text-white';
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

export default function IssueDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [issue, setIssue] = useState<IssueDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    fetchIssue(id)
      .then(setIssue)
      .catch((err) =>
        setError(err instanceof Error ? err.message : 'Failed to load issue'),
      )
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <div className="w-8 h-8 border-4 border-[var(--color-border)] border-t-[var(--color-accent)] rounded-full animate-spin" />
      </div>
    );
  }

  if (error || !issue) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-16 text-center">
        <p className="text-[var(--color-danger)] mb-4">{error ?? 'Issue not found'}</p>
        <Link
          to="/issues"
          className="text-[var(--color-accent)] hover:text-[var(--color-accent-hover)] transition"
        >
          &larr; Back to issues
        </Link>
      </div>
    );
  }

  const sortedStatements = [...issue.statements].sort(
    (a, b) =>
      new Date(b.post_date ?? b.created_at).getTime() -
      new Date(a.post_date ?? a.created_at).getTime(),
  );

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 py-8">
      {/* Back link */}
      <Link
        to="/issues"
        className="inline-flex items-center gap-1 text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-accent)] transition mb-6"
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
        </svg>
        All Issues
      </Link>

      {/* Issue header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-3">
          <span className="inline-block text-xs font-medium px-2.5 py-0.5 rounded-full bg-[var(--color-badge-bg)] text-[var(--color-badge-text)]">
            Issue
          </span>
        </div>
        <h1 className="text-3xl font-bold text-[var(--color-text)] mb-3">{issue.name}</h1>
        {issue.description && (
          <p className="text-[var(--color-text-secondary)] leading-relaxed">{issue.description}</p>
        )}
      </div>

      {/* Statements */}
      <h2 className="text-xl font-semibold text-[var(--color-text)] mb-4">
        Statements ({sortedStatements.length})
      </h2>

      {sortedStatements.length === 0 && (
        <p className="text-[var(--color-text-secondary)] py-8 text-center">
          No statements recorded for this issue yet.
        </p>
      )}

      <div className="space-y-4">
        {sortedStatements.map((stmt) => (
          <div
            key={stmt.id}
            className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-xl p-5 transition hover:border-[var(--color-accent)]"
          >
            <div className="flex flex-wrap items-center gap-2 mb-2">
              <span className="font-semibold text-[var(--color-text)]">
                {stmt.politician.name}
              </span>
              <span
                className={`text-xs font-medium px-2 py-0.5 rounded-full ${partyBadgeClass(stmt.politician.party)}`}
              >
                {stmt.politician.party}
              </span>
              {stmt.issues.map((iss) => (
                <span
                  key={iss.id}
                  className="text-xs font-medium px-2 py-0.5 rounded-full bg-[var(--color-badge-bg)] text-[var(--color-badge-text)]"
                >
                  {iss.name}
                </span>
              ))}
              <span className="text-xs text-[var(--color-text-secondary)] ml-auto">
                {formatDate(stmt.post_date ?? stmt.created_at)}
              </span>
            </div>

            <h3 className="text-lg font-semibold text-[var(--color-text)] mb-2">{stmt.title}</h3>

            <p className="text-sm text-[var(--color-text-secondary)] leading-relaxed mb-3">
              {snippetText(stmt.analysis)}
            </p>

            <Link
              to={`/statements/${stmt.id}`}
              className="text-sm font-medium text-[var(--color-accent)] hover:text-[var(--color-accent-hover)] transition"
            >
              Read more &rarr;
            </Link>
          </div>
        ))}
      </div>
    </div>
  );
}
