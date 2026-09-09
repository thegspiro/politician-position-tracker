import React from 'react';
import type { SourceInput } from '../types';
import { MEDIA_TYPES, MEDIA_TYPE_LABELS } from '../types';

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
  };
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
  numberOffset,
}: {
  legend: string;
  blurb: string;
  addLabel: string;
  emptyLabel: string;
  sourceType: 'post' | 'analysis';
  sources: SourceInput[];
  onChange: (next: SourceInput[]) => void;
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
