import { describe, expect, it } from 'vitest';
import { inTextForm, referenceForm } from '../citations';
import type { CitationSet } from '../../types';

const form = (text: string) => ({ text, spans: [{ text, italic: false }] });

const citations: CitationSet = {
  note: form('note form'),
  bibliography: form('bibliography form'),
  author_date_citation: form('(Doe 2026)'),
  author_date_reference: form('reference form'),
};

describe('referenceForm', () => {
  it('uses the bibliography entry for notes-bibliography', () => {
    expect(referenceForm(citations, 'notes-bibliography').text).toBe('bibliography form');
  });

  it('uses the reference entry for author-date', () => {
    expect(referenceForm(citations, 'author-date').text).toBe('reference form');
  });
});

describe('inTextForm', () => {
  it('uses the note for notes-bibliography', () => {
    expect(inTextForm(citations, 'notes-bibliography').text).toBe('note form');
  });

  it('uses the parenthetical for author-date', () => {
    expect(inTextForm(citations, 'author-date').text).toBe('(Doe 2026)');
  });
});
