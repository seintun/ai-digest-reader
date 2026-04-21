import type { Story } from '../types';

/** Escape HTML entities to prevent XSS in innerHTML strings. */
export function escapeHtml(input: string): string {
  return input
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

/** Validate and return a safe external URL, or '#' if invalid. */
export function safeExternalUrl(input: string | undefined): string {
  if (!input) return '#';
  try {
    const parsed = new URL(input, window.location.origin);
    if (parsed.protocol === 'http:' || parsed.protocol === 'https:') return parsed.href;
    return '#';
  } catch {
    return '#';
  }
}

/** Get the discussion/comments URL for a story. */
export function getDiscussionUrl(story: Story): string {
  if (story.p) return story.p;
  if (story.i.startsWith('hn-')) return '';
  return story.u;
}

/** Format a number: 1234 → "1.2k" */
export function formatCount(n: number): string {
  return n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(n);
}

/** Estimate reading time in minutes from a body excerpt. */
export function readingTime(body: string | undefined): number | null {
  if (!body) return null;
  const words = body.trim().split(/\s+/).length;
  return Math.max(1, Math.ceil(words / 200));
}

function hostToPublication(hostname: string): string {
  const host = hostname.toLowerCase().replace(/^www\./, '');
  const known: Record<string, string> = {
    'bbc.com': 'BBC',
    'bbc.co.uk': 'BBC',
    'news.mit.edu': 'MIT',
    'mit.edu': 'MIT',
    'technologyreview.com': 'MIT Tech Review',
    'news.ycombinator.com': 'Hacker News',
    'reddit.com': 'Reddit',
  };
  if (known[host]) return known[host];

  const parts = host.split('.').filter(Boolean);
  if (parts.length === 0) return 'Unknown source';
  if (parts.length === 1) return parts[0].toUpperCase();

  const secondLevelDomains = new Set(['co', 'com', 'org', 'net', 'gov', 'ac']);
  const penultimate = parts[parts.length - 2];
  const root = secondLevelDomains.has(penultimate) && parts.length >= 3
    ? parts[parts.length - 3]
    : penultimate;
  const cleaned = root.replace(/[-_]+/g, ' ').trim();
  if (!cleaned) return host;
  if (cleaned.length <= 4) return cleaned.toUpperCase();
  return cleaned
    .split(' ')
    .map(token => token.charAt(0).toUpperCase() + token.slice(1))
    .join(' ');
}

/** Get publication/source label for attribution (e.g. BBC, MIT, Reddit). */
export function getStoryAttribution(story: Story): string {
  if (story.sn && story.sn.trim()) return story.sn.trim();

  if (story.i.startsWith('rd-')) return 'Reddit';
  if (story.i.startsWith('hn-')) return 'Hacker News';

  try {
    const url = new URL(story.u);
    return hostToPublication(url.hostname);
  } catch {
    return 'RSS';
  }
}

export interface SourceCounts {
  reddit: number;
  hn: number;
  rss: number;
  total: number;
}

/** Count stories by source prefix. */
export function getSourceCounts(stories: Story[]): SourceCounts {
  return {
    reddit: stories.filter(s => s.i.startsWith('rd-')).length,
    hn: stories.filter(s => s.i.startsWith('hn-')).length,
    rss: stories.filter(s => s.i.startsWith('rs-')).length,
    total: stories.length,
  };
}
