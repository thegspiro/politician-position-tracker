/** Selecting which rendered citation form a Chicago system uses. */

import type { CitationForm, CitationSet, CitationStyle } from '../types';

/** The form used in a reference list: bibliography, or author-date reference. */
export function referenceForm(
  citations: CitationSet,
  style: CitationStyle,
): CitationForm {
  return style === 'author-date'
    ? citations.author_date_reference
    : citations.bibliography;
}

/** The form used at the point of citation: a note, or a parenthetical. */
export function inTextForm(
  citations: CitationSet,
  style: CitationStyle,
): CitationForm {
  return style === 'author-date' ? citations.author_date_citation : citations.note;
}
