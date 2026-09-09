import { useEffect, useState } from 'react';
import { citationExportUrls, fetchStatementCitations } from '../api';
import type { CitationStyle, StatementCitations } from '../types';
import { CITATION_STYLE_LABELS } from '../types';
import { CitationText, CopyButton } from './CitationText';
import { referenceForm } from '../lib/citations';

const STYLE_STORAGE_KEY = 'citation_style';

function storedStyle(): CitationStyle | null {
  try {
    const value = localStorage.getItem(STYLE_STORAGE_KEY);
    return value === 'author-date' || value === 'notes-bibliography' ? value : null;
  } catch {
    // Storage can be unavailable (private windows, blocked site data).
    return null;
  }
}

function rememberStyle(style: CitationStyle) {
  try {
    localStorage.setItem(STYLE_STORAGE_KEY, style);
  } catch {
    // A remembered preference is a convenience, not a requirement.
  }
}

function StyleToggle({
  style,
  onChange,
}: {
  style: CitationStyle;
  onChange: (next: CitationStyle) => void;
}) {
  return (
    <div className="flex items-center gap-1" role="group" aria-label="Citation style">
      {(Object.keys(CITATION_STYLE_LABELS) as CitationStyle[]).map((option) => (
        <button
          key={option}
          type="button"
          onClick={() => onChange(option)}
          aria-pressed={style === option}
          className={`text-xs px-2 py-1 rounded border transition ${
            style === option
              ? 'bg-[var(--color-accent)] text-white border-[var(--color-accent)]'
              : 'border-[var(--color-border)] text-[var(--color-text-secondary)] hover:text-[var(--color-text)]'
          }`}
        >
          {CITATION_STYLE_LABELS[option]}
        </button>
      ))}
    </div>
  );
}

export default function BibliographySection({
  statementId,
  style,
  onStyleChange,
}: {
  statementId: number;
  /** Null until a default is known, so the parent can follow this component. */
  style: CitationStyle | null;
  onStyleChange: (style: CitationStyle) => void;
}) {
  const [data, setData] = useState<StatementCitations | null>(null);

  useEffect(() => {
    let active = true;
    fetchStatementCitations(statementId)
      .then((result) => {
        if (!active) return;
        setData(result);
        // A remembered reader preference wins over the site default.
        onStyleChange(storedStyle() ?? result.default_style);
      })
      .catch(() => {
        // Citations enrich the page; failing to load them must not break it.
        if (active) setData(null);
      });
    return () => {
      active = false;
    };
  }, [statementId, onStyleChange]);

  if (!data) return null;

  const activeStyle: CitationStyle = style ?? data.default_style;

  function chooseStyle(next: CitationStyle) {
    onStyleChange(next);
    rememberStyle(next);
  }

  const heading = activeStyle === 'author-date' ? 'References' : 'Bibliography';
  const exports = citationExportUrls(statementId);
  const entries = [
    ...data.sources.map((source) => ({
      key: source.uid,
      form: referenceForm(source, activeStyle),
    })),
    { key: 'post', form: referenceForm(data.post, activeStyle) },
  ];

  return (
    <div className="mb-8 border-t border-[var(--color-border)] pt-6">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
        <h2 className="text-xl font-semibold text-[var(--color-text)]">{heading}</h2>
        <StyleToggle style={activeStyle} onChange={chooseStyle} />
      </div>

      <p className="text-sm text-[var(--color-text-secondary)] mb-4">
        Chicago Manual of Style, 18th edition.
      </p>

      <ol className="space-y-3 mb-6">
        {entries.map(({ key, form }) => (
          <li
            key={key}
            className="flex items-start justify-between gap-3 text-sm text-[var(--color-text)] leading-relaxed"
          >
            {/* A hanging indent, as a reference list is conventionally set. */}
            <span style={{ paddingLeft: '1.5em', textIndent: '-1.5em' }}>
              <CitationText form={form} />
            </span>
            <CopyButton value={form.text} />
          </li>
        ))}
      </ol>

      <div className="bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-lg p-4">
        <h3 className="text-sm font-semibold text-[var(--color-text)] mb-2">
          Cite this page
        </h3>
        <div className="flex items-start justify-between gap-3">
          <p className="text-sm text-[var(--color-text)] leading-relaxed">
            <CitationText form={referenceForm(data.page, activeStyle)} />
          </p>
          <CopyButton value={referenceForm(data.page, activeStyle).text} />
        </div>

        <div className="flex flex-wrap items-center gap-3 mt-4 pt-3 border-t border-[var(--color-border)]">
          <span className="text-xs text-[var(--color-text-secondary)]">
            Export all:
          </span>
          <a
            href={exports.bibtex}
            className="text-xs px-2 py-1 rounded border border-[var(--color-border)] text-[var(--color-accent)] hover:border-[var(--color-accent)] transition"
          >
            BibTeX
          </a>
          <a
            href={exports.cslJson}
            className="text-xs px-2 py-1 rounded border border-[var(--color-border)] text-[var(--color-accent)] hover:border-[var(--color-accent)] transition"
          >
            CSL-JSON
          </a>
        </div>
      </div>
    </div>
  );
}
