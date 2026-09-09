/** Helpers shared by the post embed and the source embeds. */

export function getYouTubeVideoId(url: string): string | null {
  try {
    const u = new URL(url);
    if (
      u.hostname.includes('youtube.com') ||
      u.hostname.includes('youtube-nocookie.com')
    ) {
      return u.searchParams.get('v');
    }
    if (u.hostname === 'youtu.be') {
      return u.pathname.slice(1).split('/')[0] || null;
    }
  } catch {
    // invalid URL
  }
  return null;
}

/**
 * Parse a timestamp locator into seconds.
 *
 * Accepts "1:23", "01:23:45" and "90s"/"90", the forms an editor is likely to
 * write into a locator field for a video or audio source. Returns null for
 * anything else, including page and section locators.
 */
export function parseTimestampSeconds(locator: string | null): number | null {
  if (!locator) return null;
  const value = locator.trim();

  const clock = /^(?:(\d{1,2}):)?(\d{1,2}):(\d{2})$/.exec(value);
  if (clock) {
    const [, hours, minutes, seconds] = clock;
    return (
      (hours ? Number(hours) * 3600 : 0) +
      Number(minutes) * 60 +
      Number(seconds)
    );
  }

  const plain = /^(\d+)s?$/.exec(value);
  if (plain) return Number(plain[1]);

  return null;
}

/** True when the URL points at something a browser renders as a PDF. */
export function looksLikePdf(url: string): boolean {
  try {
    return new URL(url).pathname.toLowerCase().endsWith('.pdf');
  } catch {
    return false;
  }
}

const AUDIO_EXTENSIONS = ['.mp3', '.m4a', '.ogg', '.oga', '.wav'];

/** True when the URL points directly at an audio file the browser can play. */
export function looksLikeAudioFile(url: string): boolean {
  try {
    const path = new URL(url).pathname.toLowerCase();
    return AUDIO_EXTENSIONS.some((ext) => path.endsWith(ext));
  } catch {
    return false;
  }
}

/** Hostname shown next to a link, e.g. "congress.gov". */
export function hostLabel(url: string): string | null {
  try {
    return new URL(url).hostname.replace(/^www\./, '');
  } catch {
    return null;
  }
}
