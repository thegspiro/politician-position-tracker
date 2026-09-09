import { useState } from 'react';
import type { CitationForm } from '../types';

/**
 * Render a citation's spans as elements.
 *
 * The server sends structured runs rather than HTML, so italics survive
 * without the page ever inserting markup it did not build itself.
 */
export function CitationText({ form }: { form: CitationForm }) {
  return (
    <span>
      {form.spans.map((span, index) =>
        span.italic ? <em key={index}>{span.text}</em> : <span key={index}>{span.text}</span>,
      )}
    </span>
  );
}

export function CopyButton({
  value,
  label = 'Copy',
}: {
  value: string;
  label?: string;
}) {
  const [copied, setCopied] = useState(false);
  const [failed, setFailed] = useState(false);

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      setFailed(false);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard access is refused in some browsers and over plain HTTP.
      setFailed(true);
      setTimeout(() => setFailed(false), 3000);
    }
  }

  return (
    <button
      type="button"
      onClick={handleCopy}
      className="text-xs px-2 py-1 rounded border border-[var(--color-border)] text-[var(--color-text-secondary)] hover:text-[var(--color-text)] hover:border-[var(--color-accent)] transition whitespace-nowrap"
      aria-label={`${label} citation`}
    >
      {copied ? 'Copied' : failed ? 'Press Ctrl+C' : label}
    </button>
  );
}
