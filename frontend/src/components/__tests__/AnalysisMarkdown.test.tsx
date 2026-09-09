import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import AnalysisMarkdown from '../AnalysisMarkdown';
import type { Source } from '../../types';

function source(overrides: Partial<Source> = {}): Source {
  return {
    id: 1,
    uid: 'uid000000001',
    source_type: 'analysis',
    title: 'H.R. 1234 as introduced',
    url: 'https://www.congress.gov/bill/hr1234',
    description: null,
    media_type: 'document',
    publisher: 'Congress.gov',
    published_date: null,
    excerpt: null,
    locator: null,
    archive_url: null,
    archived_at: null,
    retrieved_at: null,
    sort_order: 0,
    ...overrides,
  };
}

function render(analysis: string, sources: Source[]) {
  return renderToStaticMarkup(
    <AnalysisMarkdown analysis={analysis} sources={sources} />,
  );
}

describe('AnalysisMarkdown', () => {
  it('turns a citation marker into a link to the matching source card', () => {
    const html = render('They voted for it.[^1]', [source()]);
    expect(html).toContain('href="#source-uid000000001"');
    expect(html).toContain('[1]');
  });

  it('numbers markers by source order, not by primary key', () => {
    const html = render('First.[^1] Second.[^2]', [
      source({ id: 9, uid: 'uidAAAAAAAAA' }),
      source({ id: 2, uid: 'uidBBBBBBBBB' }),
    ]);
    expect(html).toContain('href="#source-uidAAAAAAAAA"');
    expect(html).toContain('href="#source-uidBBBBBBBBB"');
  });

  it('suppresses the generated footnote list, which the source cards replace', () => {
    const html = render('Claim.[^1]', [source()]);
    expect(html).not.toContain('data-footnotes');
    expect(html).not.toContain('Back to content');
  });

  it('leaves a marker with no matching source as literal text', () => {
    // Only definitions generated from the source list exist, so a marker
    // numbered beyond it is never parsed as a footnote. It stays visible in the
    // body, which signals the authoring mistake rather than hiding it.
    const html = render('Unsupported claim.[^3]', [source()]);
    expect(html).not.toContain('#source-');
    expect(html).toContain('[^3]');
  });

  it('renders an author-defined footnote label as plain text, not a broken link', () => {
    const html = render('Claim.[^note]\n\n[^note]: An aside.', [source()]);
    expect(html).not.toContain('#source-');
    expect(html).not.toContain('#user-content-fn-');
    expect(html).toContain('[note]');
  });

  it('leaves ordinary markdown links intact and external', () => {
    const html = render('See [the bill](https://example.test/bill).', []);
    expect(html).toContain('href="https://example.test/bill"');
    expect(html).toContain('rel="noopener noreferrer"');
    expect(html).toContain('target="_blank"');
  });

  it('renders analysis with no citations unchanged', () => {
    const html = render('Just prose, no markers.', [source()]);
    expect(html).toContain('Just prose, no markers.');
    expect(html).not.toContain('#source-');
  });

  it('still renders ordinary markdown formatting', () => {
    const html = render('**bold** and *italic*', []);
    expect(html).toContain('<strong>bold</strong>');
    expect(html).toContain('<em>italic</em>');
  });

  it('escapes HTML in the analysis body', () => {
    const html = render('<img src=x onerror="alert(1)">', []);
    expect(html).not.toContain('<img src=x');
  });
});
