import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import { CitationText } from '../CitationText';

describe('CitationText', () => {
  it('renders italic runs as emphasis elements', () => {
    const html = renderToStaticMarkup(
      <CitationText
        form={{
          text: 'Doe, Jane. New York Times. 2026.',
          spans: [
            { text: 'Doe, Jane. ', italic: false },
            { text: 'New York Times', italic: true },
            { text: '. 2026.', italic: false },
          ],
        }}
      />,
    );
    expect(html).toContain('<em>New York Times</em>');
    expect(html).toContain('Doe, Jane. ');
  });

  it('escapes markup that appears in citation text', () => {
    const html = renderToStaticMarkup(
      <CitationText
        form={{
          text: '<script>alert(1)</script>',
          spans: [{ text: '<script>alert(1)</script>', italic: false }],
        }}
      />,
    );
    expect(html).not.toContain('<script>');
    expect(html).toContain('&lt;script&gt;');
  });

  it('renders an empty citation without crashing', () => {
    expect(renderToStaticMarkup(<CitationText form={{ text: '', spans: [] }} />)).toBe(
      '<span></span>',
    );
  });
});
