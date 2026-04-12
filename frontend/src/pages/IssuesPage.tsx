import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { fetchIssues } from '../api';
import type { Issue } from '../types';

export default function IssuesPage() {
  const [issues, setIssues] = useState<Issue[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchIssues()
      .then((res) => setIssues(res.items))
      .catch((err) =>
        setError(err instanceof Error ? err.message : 'Failed to load issues'),
      )
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <div className="w-8 h-8 border-4 border-[var(--color-border)] border-t-[var(--color-accent)] rounded-full animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-16 text-center">
        <p className="text-[var(--color-danger)] mb-4">{error}</p>
        <button
          onClick={() => window.location.reload()}
          className="px-4 py-2 bg-[var(--color-accent)] text-white rounded-lg hover:bg-[var(--color-accent-hover)] transition"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
      <h1 className="text-3xl font-bold text-[var(--color-text)] mb-8">Issues</h1>

      {issues.length === 0 && (
        <p className="text-center text-[var(--color-text-secondary)] text-lg py-16">
          No issues found.
        </p>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
        {issues.map((issue) => (
          <Link
            key={issue.id}
            to={`/issues/${issue.id}`}
            className="group bg-[var(--color-card)] border border-[var(--color-border)] rounded-xl p-5 transition hover:border-[var(--color-accent)] hover:shadow-md"
          >
            <div className="flex items-center gap-2 mb-3">
              <span className="inline-block text-xs font-medium px-2.5 py-0.5 rounded-full bg-[var(--color-badge-bg)] text-[var(--color-badge-text)]">
                Issue
              </span>
            </div>

            <h2 className="text-lg font-semibold text-[var(--color-text)] group-hover:text-[var(--color-accent)] transition mb-2">
              {issue.name}
            </h2>

            {issue.description && (
              <p className="text-sm text-[var(--color-text-secondary)] leading-relaxed line-clamp-3">
                {issue.description}
              </p>
            )}
          </Link>
        ))}
      </div>
    </div>
  );
}
