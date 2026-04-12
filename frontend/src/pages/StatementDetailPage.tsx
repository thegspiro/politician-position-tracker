import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { fetchStatement } from '../api';
import type { Statement } from '../types';

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

function platformLabel(platform: string): string {
  const p = platform.toLowerCase();
  if (p === 'x') return 'X (Twitter)';
  return platform.charAt(0).toUpperCase() + platform.slice(1);
}

function platformIcon(platform: string): React.ReactNode {
  const p = platform.toLowerCase();
  const baseClass = 'w-5 h-5 inline-block';
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
  // Generic link icon
  return (
    <svg className={baseClass} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
    </svg>
  );
}

function ShareButtons({ url, title }: { url: string; title: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(url).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  const encodedUrl = encodeURIComponent(url);
  const encodedTitle = encodeURIComponent(title);

  return (
    <div className="flex items-center gap-2">
      <span className="text-sm text-[var(--color-text-secondary)] mr-1">Share:</span>

      {/* Copy link */}
      <button
        onClick={handleCopy}
        title="Copy link"
        className="p-2 rounded-lg border border-[var(--color-border)] hover:bg-[var(--color-bg-secondary)] transition text-[var(--color-text-secondary)] hover:text-[var(--color-text)]"
      >
        {copied ? (
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
        ) : (
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
          </svg>
        )}
      </button>

      {/* Share to X / Twitter */}
      <a
        href={`https://twitter.com/intent/tweet?url=${encodedUrl}&text=${encodedTitle}`}
        target="_blank"
        rel="noopener noreferrer"
        title="Share on X"
        className="p-2 rounded-lg border border-[var(--color-border)] hover:bg-[var(--color-bg-secondary)] transition text-[var(--color-text-secondary)] hover:text-[var(--color-text)]"
      >
        <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
          <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
        </svg>
      </a>

      {/* Share to Facebook */}
      <a
        href={`https://www.facebook.com/sharer/sharer.php?u=${encodedUrl}`}
        target="_blank"
        rel="noopener noreferrer"
        title="Share on Facebook"
        className="p-2 rounded-lg border border-[var(--color-border)] hover:bg-[var(--color-bg-secondary)] transition text-[var(--color-text-secondary)] hover:text-[var(--color-text)]"
      >
        <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
          <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z" />
        </svg>
      </a>

      {/* Share via email */}
      <a
        href={`mailto:?subject=${encodedTitle}&body=${encodedUrl}`}
        title="Share via email"
        className="p-2 rounded-lg border border-[var(--color-border)] hover:bg-[var(--color-bg-secondary)] transition text-[var(--color-text-secondary)] hover:text-[var(--color-text)]"
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
        </svg>
      </a>
    </div>
  );
}

export default function StatementDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [statement, setStatement] = useState<Statement | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    fetchStatement(id)
      .then(setStatement)
      .catch((err) =>
        setError(err instanceof Error ? err.message : 'Failed to load statement'),
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

  if (error || !statement) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-16 text-center">
        <p className="text-[var(--color-danger)] mb-4">{error ?? 'Statement not found'}</p>
        <Link
          to="/"
          className="text-[var(--color-accent)] hover:text-[var(--color-accent-hover)] transition"
        >
          &larr; Back to timeline
        </Link>
      </div>
    );
  }

  const pageUrl = typeof window !== 'undefined' ? window.location.href : '';

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 py-8">
      {/* Back link */}
      <Link
        to="/"
        className="inline-flex items-center gap-1 text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-accent)] transition mb-6"
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
        </svg>
        Back to Timeline
      </Link>

      {/* Politician info */}
      <div className="flex flex-wrap items-center gap-3 mb-4">
        <Link
          to={`/politicians/${statement.politician.id}`}
          className="font-semibold text-[var(--color-text)] hover:text-[var(--color-accent)] transition"
        >
          {statement.politician.name}
        </Link>
        <span
          className={`text-xs font-medium px-2.5 py-0.5 rounded-full ${partyBadgeClass(statement.politician.party)}`}
        >
          {statement.politician.party}
        </span>
        {statement.politician.office && (
          <span className="text-sm text-[var(--color-text-secondary)]">
            {statement.politician.office}
          </span>
        )}
      </div>

      {/* Issue badge */}
      <div className="mb-4">
        <Link
          to={`/issues/${statement.issue.id}`}
          className="inline-block text-xs font-medium px-2.5 py-0.5 rounded-full bg-[var(--color-badge-bg)] text-[var(--color-badge-text)] hover:opacity-80 transition"
        >
          {statement.issue.name}
        </Link>
      </div>

      {/* Title */}
      <h1 className="text-3xl font-bold text-[var(--color-text)] mb-3">{statement.title}</h1>

      {/* Date */}
      <p className="text-sm text-[var(--color-text-secondary)] mb-6">
        {formatDate(statement.post_date ?? statement.created_at)}
      </p>

      {/* Social embed area */}
      <div className="mb-8 bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-xl p-5">
        <div className="flex items-center gap-2 mb-3">
          <span className="text-[var(--color-text-secondary)]">
            {platformIcon(statement.post_platform)}
          </span>
          <a
            href={statement.post_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm font-medium text-[var(--color-accent)] hover:text-[var(--color-accent-hover)] transition break-all"
          >
            View on {platformLabel(statement.post_platform)}
          </a>
        </div>

        {statement.post_content && (
          <blockquote className="border-l-4 border-[var(--color-accent)] pl-4 py-2 my-3">
            <p className="text-[var(--color-text)] text-sm leading-relaxed italic whitespace-pre-wrap">
              {statement.post_content}
            </p>
          </blockquote>
        )}

        {statement.screenshot_url && (
          <img
            src={statement.screenshot_url}
            alt="Post screenshot"
            className="mt-4 rounded-lg border border-[var(--color-border)] max-w-full"
          />
        )}
      </div>

      {/* Full analysis */}
      <div className="mb-8">
        <h2 className="text-xl font-semibold text-[var(--color-text)] mb-3">Analysis</h2>
        <div className="text-[var(--color-text)] leading-relaxed whitespace-pre-wrap">
          {statement.analysis}
        </div>
      </div>

      {/* Post Sources */}
      {statement.sources && statement.sources.filter((s) => s.source_type === 'post').length > 0 && (
        <div className="mb-8">
          <h2 className="text-xl font-semibold text-[var(--color-text)] mb-3">Post Sources</h2>
          <p className="text-sm text-[var(--color-text-secondary)] mb-3">Citations for the original post</p>
          <div className="space-y-3">
            {statement.sources.filter((s) => s.source_type === 'post').map((source) => (
              <div
                key={source.id}
                className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-lg p-4"
              >
                <a
                  href={source.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm font-medium text-[var(--color-accent)] hover:text-[var(--color-accent-hover)] transition break-all"
                >
                  {source.title}
                </a>
                {source.description && (
                  <p className="text-sm text-[var(--color-text-secondary)] mt-1 leading-relaxed">
                    {source.description}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Analysis Sources */}
      {statement.sources && statement.sources.filter((s) => s.source_type === 'analysis').length > 0 && (
        <div className="mb-8">
          <h2 className="text-xl font-semibold text-[var(--color-text)] mb-3">Analysis Sources</h2>
          <p className="text-sm text-[var(--color-text-secondary)] mb-3">Citations supporting the analysis</p>
          <div className="space-y-3">
            {statement.sources.filter((s) => s.source_type === 'analysis').map((source) => (
              <div
                key={source.id}
                className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-lg p-4"
              >
                <a
                  href={source.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm font-medium text-[var(--color-accent)] hover:text-[var(--color-accent-hover)] transition break-all"
                >
                  {source.title}
                </a>
                {source.description && (
                  <p className="text-sm text-[var(--color-text-secondary)] mt-1 leading-relaxed">
                    {source.description}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Share buttons */}
      <div className="border-t border-[var(--color-border)] pt-6">
        <ShareButtons url={pageUrl} title={statement.title} />
      </div>
    </div>
  );
}
