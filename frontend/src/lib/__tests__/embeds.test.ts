import { describe, expect, it } from 'vitest';
import {
  getYouTubeVideoId,
  hostLabel,
  looksLikeAudioFile,
  looksLikePdf,
  parseTimestampSeconds,
} from '../embeds';

describe('getYouTubeVideoId', () => {
  it('reads the id from a watch URL', () => {
    expect(getYouTubeVideoId('https://www.youtube.com/watch?v=abc123')).toBe('abc123');
  });

  it('reads the id from a youtu.be URL', () => {
    expect(getYouTubeVideoId('https://youtu.be/abc123')).toBe('abc123');
  });

  it('reads the id from a nocookie URL', () => {
    expect(getYouTubeVideoId('https://www.youtube-nocookie.com/watch?v=abc123')).toBe(
      'abc123',
    );
  });

  it('returns null for a non-YouTube URL', () => {
    expect(getYouTubeVideoId('https://example.test/video')).toBeNull();
  });

  it('returns null for a malformed URL', () => {
    expect(getYouTubeVideoId('not a url')).toBeNull();
  });
});

describe('parseTimestampSeconds', () => {
  it.each([
    ['1:23', 83],
    ['01:23', 83],
    ['01:23:45', 5025],
    ['1:00:00', 3600],
    ['90s', 90],
    ['90', 90],
  ])('parses %s', (locator, expected) => {
    expect(parseTimestampSeconds(locator)).toBe(expected);
  });

  it.each([['p. 14'], ['sec. 203(b)'], [''], ['12:60:60:60']])(
    'returns null for the non-timestamp locator %s',
    (locator) => {
      expect(parseTimestampSeconds(locator)).toBeNull();
    },
  );

  it('returns null when there is no locator', () => {
    expect(parseTimestampSeconds(null)).toBeNull();
  });
});

describe('looksLikePdf', () => {
  it('detects a PDF path', () => {
    expect(looksLikePdf('https://example.test/bill.pdf')).toBe(true);
  });

  it('ignores the query string', () => {
    expect(looksLikePdf('https://example.test/bill.pdf?download=1')).toBe(true);
  });

  it('is false for a regular page', () => {
    expect(looksLikePdf('https://example.test/bill')).toBe(false);
  });

  it('is false for a malformed URL', () => {
    expect(looksLikePdf('bill.pdf')).toBe(false);
  });
});

describe('looksLikeAudioFile', () => {
  it.each([['https://e.test/a.mp3'], ['https://e.test/a.M4A'], ['https://e.test/a.wav']])(
    'detects %s',
    (url) => {
      expect(looksLikeAudioFile(url)).toBe(true);
    },
  );

  it('is false for a page URL', () => {
    expect(looksLikeAudioFile('https://e.test/episode/12')).toBe(false);
  });
});

describe('hostLabel', () => {
  it('strips the www prefix', () => {
    expect(hostLabel('https://www.congress.gov/bill/1')).toBe('congress.gov');
  });

  it('keeps other subdomains', () => {
    expect(hostLabel('https://web.archive.org/web/x')).toBe('web.archive.org');
  });

  it('returns null for a malformed URL', () => {
    expect(hostLabel('congress.gov')).toBeNull();
  });
});
