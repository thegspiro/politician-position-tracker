import React, { useState } from 'react';
import { archiveSource } from '../api';
import type { Author, SourceInput } from '../types';
import {
  DOCUMENT_TYPES,
  DOCUMENT_TYPE_LABELS,
  MEDIA_TYPES,
  MEDIA_TYPE_LABELS,
} from '../types';

function emptySource(type: 'post' | 'analysis'): SourceInput {
  return {
    source_type: type,
    title: '',
    url: '',
    description: '',
    media_type: 'webpage',
    publisher: '',
    published_date: '',
    excerpt: '',
    locator: '',
    archive_url: '',
    archived_at: '',
    retrieved_at: '',
    authors: [],
    container_title: '',
    edition: '',
    document_type: '',
    bill_number: '',
    congress_number: '',
    congress_session: '',
    committee: '',
    report_number: '',
  };
}

/**
 * Chicago inverts the lead author in a bibliography but not in a note, and
 * never inverts a corporate name, so names are captured in parts rather than
 * as one string.
 */
/**
 * Capture a Wayback snapshot for a saved source.
 *
 * Only offered for a source that already exists on the server: a uid is what
 * the endpoint addresses, and one is assigned on save.
 */
function ArchiveNowButton({
  statementId,
  uid,
  onArchived,
}: {
  statementId: number;
  uid: string;
  onArchived: (url: string, archivedAt: string) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleClick() {
    setBusy(true);
    setError(null);
    try {
      const result = await archiveSource(statementId, uid);
      onArchived(result.archive_url, (result.archived_at ?? '').slice(0, 10));
    } catch (err) {
      setError(
        err instanceof Error
          ? 'Could not archive. The archive service may be busy; try again.'
          : 'Could not archive.',
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <button
        type="button"
        onClick={handleClick}
        disabled={busy}
        className="px-2 py-1 text-xs rounded border border-[var(--color-border)] text-[var(--color-text-secondary)] hover:text-[var(--color-accent)] hover:border-[var(--color-accent)] transition disabled:opacity-50"
      >
        {busy ? 'Archiving...' : 'Archive now'}
      </button>
      {error && (
        <p className="text-xs text-[var(--color-danger)] mt-1">{error}</p>
      )}
    </div>
  );
}

function AuthorsEditor({
  authors,
  onChange,
}: {
  authors: Author[];
  onChange: (next: Author[]) => void;
}) {
  function update(index: number, patch: Partial<Author>) {
    const next = [...authors];
    next[index] = { ...next[index], ...patch };
    onChange(next);
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <label className={labelClass}>
          Authors
          <span className="block font-normal opacity-80">
            Leave the name fields blank and use the organisation field for a
            corporate author such as &ldquo;U.S. Congress&rdquo;
          </span>
        </label>
        <button
          type="button"
          onClick={() => onChange([...authors, { given: '', family: '' }])}
          className="px-2 py-1 text-xs rounded border border-[var(--color-border)] text-[var(--color-text-secondary)] hover:text-[var(--color-text)] transition"
        >
          + Add author
        </button>
      </div>

      {authors.length === 0 && (
        <p className="text-xs text-[var(--color-text-secondary)] italic">
          No authors. The citation will begin with the title.
        </p>
      )}

      <div className="space-y-2">
        {authors.map((author, index) => (
          <div key={index} className="flex flex-wrap items-center gap-2">
            <input
              type="text"
              placeholder="Given name"
              value={author.given ?? ''}
              onChange={(e) => update(index, { given: e.target.value, literal: '' })}
              className={`${inputClass} flex-1 min-w-[8rem]`}
            />
            <input
              type="text"
              placeholder="Family name"
              value={author.family ?? ''}
              onChange={(e) => update(index, { family: e.target.value, literal: '' })}
              className={`${inputClass} flex-1 min-w-[8rem]`}
            />
            <input
              type="text"
              placeholder="or Organisation"
              value={author.literal ?? ''}
              onChange={(e) =>
                update(index, { literal: e.target.value, given: '', family: '' })
              }
              className={`${inputClass} flex-1 min-w-[8rem]`}
            />
            <button
              type="button"
              onClick={() => onChange(authors.filter((_, i) => i !== index))}
              aria-label="Remove author"
              className="px-2 py-1 text-xs rounded border border-[var(--color-border)] text-[var(--color-danger)] hover:border-[var(--color-danger)] transition"
            >
              Remove
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

const inputClass =
  'w-full px-3 py-2 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] text-[var(--color-text)] focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)]';

const labelClass =
  'block text-xs font-medium text-[var(--color-text-secondary)] mb-1';

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label className={labelClass}>
        {label}
        {hint && (
          <span className="block font-normal opacity-80">{hint}</span>
        )}
      </label>
      {children}
    </div>
  );
}

export default function SourceListEditor({
  legend,
  blurb,
  addLabel,
  emptyLabel,
  sourceType,
  sources,
  onChange,
  statementId,
  numberOffset,
}: {
  legend: string;
  blurb: string;
  addLabel: string;
  emptyLabel: string;
  sourceType: 'post' | 'analysis';
  sources: SourceInput[];
  onChange: (next: SourceInput[]) => void;
  /** Set when editing a saved statement, which is what enables archiving. */
  statementId?: number;
  /**
   * Number of sources listed before this one. Citation markers are numbered
   * across both lists combined, so the number shown here has to match the one
   * the statement page renders rather than restarting at 1.
   */
  numberOffset: number;
}) {
  function update<K extends keyof SourceInput>(
    index: number,
    field: K,
    value: SourceInput[K],
  ) {
    const next = [...sources];
    next[index] = { ...next[index], [field]: value };
    onChange(next);
  }

  function move(index: number, delta: number) {
    const target = index + delta;
    if (target < 0 || target >= sources.length) return;
    const next = [...sources];
    [next[index], next[target]] = [next[target], next[index]];
    onChange(next);
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <label className="block text-sm font-medium text-[var(--color-text)]">
          {legend}
          <span className="block text-xs font-normal text-[var(--color-text-secondary)]">
            {blurb}
          </span>
        </label>
        <button
          type="button"
          onClick={() => onChange([...sources, emptySource(sourceType)])}
          className="px-3 py-1 text-sm bg-[var(--color-accent)] text-white rounded-lg hover:bg-[var(--color-accent-hover)] transition font-medium"
        >
          {addLabel}
        </button>
      </div>

      {sources.length === 0 && (
        <p className="text-sm text-[var(--color-text-secondary)] italic mb-2">
          {emptyLabel}
        </p>
      )}

      <div className="space-y-4">
        {sources.map((source, index) => (
          <div
            key={source.uid ?? `new-${index}`}
            className="border border-[var(--color-border)] rounded-lg p-4 bg-[var(--color-bg)] space-y-3"
          >
            <div className="flex items-center justify-between gap-2">
              <span className="text-sm font-medium text-[var(--color-text-secondary)]">
                <span className="font-mono">[{numberOffset + index + 1}]</span>{' '}
                {legend.replace(/s$/, '')}
              </span>
              <div className="flex items-center gap-1">
                <button
                  type="button"
                  onClick={() => move(index, -1)}
                  disabled={index === 0}
                  aria-label="Move source up"
                  className="px-2 py-1 text-sm rounded-lg border border-[var(--color-border)] text-[var(--color-text-secondary)] hover:text-[var(--color-text)] disabled:opacity-40 disabled:cursor-not-allowed transition"
                >
                  &uarr;
                </button>
                <button
                  type="button"
                  onClick={() => move(index, 1)}
                  disabled={index === sources.length - 1}
                  aria-label="Move source down"
                  className="px-2 py-1 text-sm rounded-lg border border-[var(--color-border)] text-[var(--color-text-secondary)] hover:text-[var(--color-text)] disabled:opacity-40 disabled:cursor-not-allowed transition"
                >
                  &darr;
                </button>
                <button
                  type="button"
                  onClick={() => onChange(sources.filter((_, i) => i !== index))}
                  className="px-3 py-1 text-sm bg-[var(--color-danger)] text-white rounded-lg hover:bg-[var(--color-danger-hover)] transition font-medium"
                >
                  Remove
                </button>
              </div>
            </div>

            <Field label="Title">
              <input
                type="text"
                placeholder="e.g. H.R. 1234 as introduced"
                value={source.title}
                onChange={(e) => update(index, 'title', e.target.value)}
                className={inputClass}
              />
            </Field>

            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="URL">
                <input
                  type="url"
                  placeholder="https://..."
                  value={source.url}
                  onChange={(e) => update(index, 'url', e.target.value)}
                  className={inputClass}
                />
              </Field>
              <Field label="Media type" hint="Controls how the source is embedded">
                <select
                  value={source.media_type}
                  onChange={(e) =>
                    update(index, 'media_type', e.target.value as SourceInput['media_type'])
                  }
                  className={inputClass}
                >
                  {MEDIA_TYPES.map((type) => (
                    <option key={type} value={type}>
                      {MEDIA_TYPE_LABELS[type]}
                    </option>
                  ))}
                </select>
              </Field>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="Publisher" hint="e.g. Congress.gov, C-SPAN, FEC">
                <input
                  type="text"
                  value={source.publisher}
                  onChange={(e) => update(index, 'publisher', e.target.value)}
                  className={inputClass}
                />
              </Field>
              <Field label="Published date">
                <input
                  type="date"
                  value={source.published_date}
                  onChange={(e) => update(index, 'published_date', e.target.value)}
                  className={inputClass}
                />
              </Field>
            </div>

            <AuthorsEditor
              authors={source.authors}
              onChange={(next) => update(index, 'authors', next)}
            />

            <div className="grid gap-3 sm:grid-cols-2">
              <Field
                label="Container title"
                hint="The publication the source appears in, e.g. New York Times"
              >
                <input
                  type="text"
                  value={source.container_title}
                  onChange={(e) => update(index, 'container_title', e.target.value)}
                  className={inputClass}
                />
              </Field>
              <Field label="Edition" hint="Optional, e.g. 2nd ed.">
                <input
                  type="text"
                  value={source.edition}
                  onChange={(e) => update(index, 'edition', e.target.value)}
                  className={inputClass}
                />
              </Field>
            </div>

            <Field
              label="Legislative or legal document type"
              hint="Set this only for bills, hearings and similar; it selects Chicago's public-document form"
            >
              <select
                value={source.document_type}
                onChange={(e) =>
                  update(index, 'document_type', e.target.value as SourceInput['document_type'])
                }
                className={inputClass}
              >
                <option value="">Not a public document</option>
                {DOCUMENT_TYPES.map((type) => (
                  <option key={type} value={type}>
                    {DOCUMENT_TYPE_LABELS[type]}
                  </option>
                ))}
              </select>
            </Field>

            {source.document_type && (
              <div className="grid gap-3 sm:grid-cols-2">
                <Field label="Bill or statute number" hint="e.g. H.R. 1234">
                  <input
                    type="text"
                    value={source.bill_number}
                    onChange={(e) => update(index, 'bill_number', e.target.value)}
                    className={inputClass}
                  />
                </Field>
                <Field label="Report number" hint="e.g. H.R. Rep. No. 118-123">
                  <input
                    type="text"
                    value={source.report_number}
                    onChange={(e) => update(index, 'report_number', e.target.value)}
                    className={inputClass}
                  />
                </Field>
                <Field label="Congress" hint="Number only, e.g. 118">
                  <input
                    type="number"
                    min={1}
                    max={999}
                    value={source.congress_number}
                    onChange={(e) => update(index, 'congress_number', e.target.value)}
                    className={inputClass}
                  />
                </Field>
                <Field label="Session" hint="e.g. 2nd">
                  <input
                    type="text"
                    value={source.congress_session}
                    onChange={(e) => update(index, 'congress_session', e.target.value)}
                    className={inputClass}
                  />
                </Field>
                <div className="sm:col-span-2">
                  <Field label="Committee" hint="e.g. Committee on Financial Services">
                    <input
                      type="text"
                      value={source.committee}
                      onChange={(e) => update(index, 'committee', e.target.value)}
                      className={inputClass}
                    />
                  </Field>
                </div>
              </div>
            )}

            <Field
              label="Excerpt"
              hint="The verbatim passage being relied on"
            >
              <textarea
                rows={3}
                value={source.excerpt}
                onChange={(e) => update(index, 'excerpt', e.target.value)}
                className={`${inputClass} resize-y`}
              />
            </Field>

            <Field
              label="Locator"
              hint='Where the excerpt lives: "p. 14", "sec. 203", or "01:23:45" to start a video there'
            >
              <input
                type="text"
                value={source.locator}
                onChange={(e) => update(index, 'locator', e.target.value)}
                className={inputClass}
              />
            </Field>

            <Field label="Description" hint="Optional editorial note">
              <input
                type="text"
                value={source.description}
                onChange={(e) => update(index, 'description', e.target.value)}
                className={inputClass}
              />
            </Field>

            <div className="grid gap-3 sm:grid-cols-3">
              <Field label="Archive URL" hint="Snapshot used if the original rots">
                <input
                  type="url"
                  placeholder="https://web.archive.org/..."
                  value={source.archive_url}
                  onChange={(e) => update(index, 'archive_url', e.target.value)}
                  className={inputClass}
                />
                {statementId !== undefined && source.uid && !source.archive_url && (
                  <div className="mt-2">
                    <ArchiveNowButton
                      statementId={statementId}
                      uid={source.uid}
                      onArchived={(url, archivedAt) => {
                        const next = [...sources];
                        next[index] = {
                          ...next[index],
                          archive_url: url,
                          archived_at: archivedAt,
                        };
                        onChange(next);
                      }}
                    />
                  </div>
                )}
              </Field>
              <Field label="Archived on">
                <input
                  type="date"
                  value={source.archived_at}
                  onChange={(e) => update(index, 'archived_at', e.target.value)}
                  className={inputClass}
                />
              </Field>
              <Field label="Retrieved on">
                <input
                  type="date"
                  value={source.retrieved_at}
                  onChange={(e) => update(index, 'retrieved_at', e.target.value)}
                  className={inputClass}
                />
              </Field>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
