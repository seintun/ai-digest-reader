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
