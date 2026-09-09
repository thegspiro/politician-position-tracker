import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { Source } from '../types';

/**
 * Renders the analysis body, turning "[^1]" markers into links to the matching
 * source card.
 *
 * GitHub-flavoured footnotes only render a marker when a matching definition
 * exists, so definitions are generated from the ordered source list and
 * appended before parsing. The generated footnote section at the bottom is then
 * suppressed, because the source cards already show that content in full; the
 * markers are rewritten to point at those cards instead.
 */
function buildFootnoteDefinitions(sources: Source[]): string {
  if (sources.length === 0) return '';
  const definitions = sources
    .map((source, index) => `[^${index + 1}]: ${source.title}`)
    .join('\n\n');
  return `\n\n${definitions}\n`;
}

/** Extract the footnote label from a generated href like "#user-content-fn-2". */
function footnoteLabel(href: string): string | null {
  const match = /#user-content-fn-(.+)$/.exec(href);
  return match ? decodeURIComponent(match[1]) : null;
}

export default function AnalysisMarkdown({
  analysis,
  sources,
}: {
  analysis: string;
  sources: Source[];
}) {
  const markdown = analysis + buildFootnoteDefinitions(sources);

  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        // The generated footnote list duplicates the source cards below it.
        section: ({ node, children, ...props }) => {
          const isFootnotes =
            (node?.properties?.dataFootnotes as unknown) !== undefined;
          if (isFootnotes) return null;
          return <section {...props}>{children}</section>;
        },
        a: ({ href, title, children }) => {
          const label = href ? footnoteLabel(href) : null;
          if (label) {
            const position = Number(label);
            const source = Number.isFinite(position)
              ? sources[position - 1]
              : undefined;
            if (!source) {
              // A marker with no matching source: render the number plainly
              // rather than a link that goes nowhere.
              return <span className="text-[var(--color-text-secondary)]">[{label}]</span>;
            }
            return (
              <a
                href={`#source-${source.uid}`}
                title={source.title}
                className="text-[var(--color-accent)] hover:text-[var(--color-accent-hover)] no-underline font-medium"
              >
                [{label}]
              </a>
            );
          }
          // Back-references from the suppressed footnote section.
          if (href?.startsWith('#user-content-fnref-')) return null;
          return (
            <a href={href} title={title} target="_blank" rel="noopener noreferrer">
              {children}
            </a>
          );
        },
      }}
    >
      {markdown}
    </ReactMarkdown>
  );
}
