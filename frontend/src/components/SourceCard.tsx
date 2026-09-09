import { useState } from 'react';
import type { CitationStyle, Source } from '../types';
import { MEDIA_TYPE_LABELS } from '../types';
import { CitationText, CopyButton } from './CitationText';
import { inTextForm } from '../lib/citations';
import {
  getYouTubeVideoId,
  hostLabel,
  looksLikeAudioFile,
  looksLikePdf,
  parseTimestampSeconds,
} from '../lib/embeds';

function formatDate(value: string | null): string | null {
  if (!value) return null;
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return null;
  return parsed.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

/**
 * Third-party frames are only loaded once the reader asks for them: it keeps
 * the page from calling out to every embedded host on load, and a source whose
 * host refuses framing degrades to its link rather than to a blank box.
 */
function ClickToLoad({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  const [loaded, setLoaded] = useState(false);

  if (loaded) return <>{children}</>;

  return (
    <button
      type="button"
      onClick={() => setLoaded(true)}
      className="w-full mt-3 py-6 px-4 rounded-lg border border-dashed border-[var(--color-border)] text-sm text-[var(--color-text-secondary)] hover:border-[var(--color-accent)] hover:text-[var(--color-accent)] transition"
    >
      {label}
    </button>
  );
}

function VideoEmbed({ source }: { source: Source }) {
  const videoId = getYouTubeVideoId(source.url);
  if (!videoId) return null;

  const startAt = parseTimestampSeconds(source.locator);
  const src =
    `https://www.youtube-nocookie.com/embed/${videoId}` +
    (startAt !== null ? `?start=${startAt}` : '');

  return (
    <ClickToLoad
      label={
        startAt !== null
          ? `Load video from ${source.locator}`
          : 'Load video'
      }
    >
      <div className="relative w-full mt-3" style={{ paddingBottom: '56.25%' }}>
        <iframe
          className="absolute inset-0 w-full h-full rounded-lg"
          src={src}
          title={source.title}
          sandbox="allow-scripts allow-same-origin allow-popups allow-presentation"
          allow="accelerometer; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          allowFullScreen
        />
      </div>
    </ClickToLoad>
  );
}

function DocumentEmbed({ source }: { source: Source }) {
  if (!looksLikePdf(source.url)) return null;

  return (
    <ClickToLoad label="Load document preview">
      <div className="mt-3">
        <iframe
          className="w-full h-[28rem] rounded-lg border border-[var(--color-border)] bg-white"
          src={source.url}
          title={source.title}
          sandbox=""
        />
        <p className="text-xs text-[var(--color-text-secondary)] mt-2">
          If the document does not appear, the publisher does not allow
          embedding &mdash; use the link above to open it directly.
        </p>
      </div>
    </ClickToLoad>
  );
}

function AudioEmbed({ source }: { source: Source }) {
  if (!looksLikeAudioFile(source.url)) return null;
  return (
    <audio controls preload="none" src={source.url} className="w-full mt-3">
      Your browser does not support embedded audio.
    </audio>
  );
}

function SourceEmbed({ source }: { source: Source }) {
  switch (source.media_type) {
    case 'video':
      return <VideoEmbed source={source} />;
    case 'document':
      return <DocumentEmbed source={source} />;
    case 'audio':
      return <AudioEmbed source={source} />;
    default:
      return null;
  }
}

export default function SourceCard({
  source,
  index,
  citationStyle = 'notes-bibliography',
}: {
  source: Source;
  /** 1-based position, used as the citation marker number. */
  index: number;
  citationStyle?: CitationStyle;
}) {
  const published = formatDate(source.published_date);
  const archived = formatDate(source.archived_at);
  const retrieved = formatDate(source.retrieved_at);
  const host = hostLabel(source.url);

  return (
    <div
      id={`source-${source.uid}`}
      className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-lg p-4 scroll-mt-20"
    >
      {/* Provenance */}
      <div className="flex flex-wrap items-center gap-2 mb-2 text-xs">
        <span className="font-mono text-[var(--color-text-secondary)]">
          [{index}]
        </span>
        <span className="px-2 py-0.5 rounded-full bg-[var(--color-badge-bg)] text-[var(--color-badge-text)] font-medium">
          {MEDIA_TYPE_LABELS[source.media_type] ?? source.media_type}
        </span>
        {source.publisher && (
          <span className="text-[var(--color-text-secondary)]">
            {source.publisher}
          </span>
        )}
        {published && (
          <span className="text-[var(--color-text-secondary)]">
            &middot; {published}
          </span>
        )}
      </div>

      {/* Title */}
      <a
        href={source.url}
        target="_blank"
        rel="noopener noreferrer"
        className="text-sm font-medium text-[var(--color-accent)] hover:text-[var(--color-accent-hover)] transition break-words"
      >
        {source.title}
      </a>

      {/* Verbatim passage */}
      {source.excerpt && (
        <blockquote className="border-l-4 border-[var(--color-accent)] pl-4 py-1 my-3">
          <p className="text-sm text-[var(--color-text)] leading-relaxed italic whitespace-pre-wrap">
            {source.excerpt}
          </p>
          {source.locator && (
            <cite className="block mt-1 text-xs not-italic text-[var(--color-text-secondary)]">
              {source.locator}
            </cite>
          )}
        </blockquote>
      )}

      {!source.excerpt && source.locator && (
        <p className="text-xs text-[var(--color-text-secondary)] mt-1">
          {source.locator}
        </p>
      )}

      {source.description && (
        <p className="text-sm text-[var(--color-text-secondary)] mt-1 leading-relaxed">
          {source.description}
        </p>
      )}

      <SourceEmbed source={source} />

      {/* The formatted citation, so a reader can quote this source directly. */}
      {source.citations && (
        <div className="mt-3 pt-3 border-t border-[var(--color-border)]">
          <div className="flex items-start justify-between gap-3">
            <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed">
              <CitationText form={inTextForm(source.citations, citationStyle)} />
            </p>
            <CopyButton value={inTextForm(source.citations, citationStyle).text} />
          </div>
        </div>
      )}

      {/* Provenance footer */}
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-3 pt-3 border-t border-[var(--color-border)] text-xs text-[var(--color-text-secondary)]">
        {host && <span className="break-all">{host}</span>}
        {source.archive_url && (
          <a
            href={source.archive_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-[var(--color-accent)] hover:text-[var(--color-accent-hover)] transition"
          >
            Archived copy{archived ? ` (${archived})` : ''}
          </a>
        )}
        {retrieved && <span>Retrieved {retrieved}</span>}
      </div>
    </div>
  );
}
