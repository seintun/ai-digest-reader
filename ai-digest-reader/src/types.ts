/**
 * DailyDigest TypeScript Types — v3 Schema
 *
 * Story ID prefixes:
 *   rd- = Reddit
 *   hn- = Hacker News
 *   rs- = RSS feeds
 *
 * Source types map to digest.json keys:
 *   reddit → digest.r[]
 *   hn     → digest.h[]
 *   rss    → digest.rs[]  (v3+, optional)
 */

export interface Story {
  i: string;       // id: rd-N, hn-N, rs-N
  t: string;       // title
  u: string;       // article URL
  p?: string;      // discussion permalink
  b?: string;      // body excerpt (max 280 chars)
  s: number;       // score (0 for RSS)
  c: number;       // comment count (0 for RSS)
  a: string;       // author
  cat?: string;    // category: "AI & ML" | "Tech" | "Security" | "Science" | "World News" | "Business" | "Futurology" | "Startups"
}

export type StorySource = 'reddit' | 'hn' | 'rss';

export function getStorySource(story: Story): StorySource {
  if (story.i.startsWith('rd-')) return 'reddit';
  if (story.i.startsWith('hn-')) return 'hn';
  return 'rss';
}

export interface MustReadItem {
  id: string;
  title: string;
  url: string;
  reason: string;
}

export interface FullBriefSection {
  heading: string;
  body: string;
}

export interface FullBrief {
  intro: string;
  sections: FullBriefSection[];
  closing: string;
}

export interface DigestSummary {
  schema_version: string;
  simple: string;
  structured: {
    themes: string[];
    breaking: string;
    mustRead: MustReadItem[];
  };
  fullBrief: FullBrief;
}

export interface Digest {
  v: 2 | 3;
  d: string;
  g: string;
  r: Story[];      // Reddit stories
  h: Story[];      // HackerNews stories
  rs?: Story[];    // RSS stories (v3+)
  summary?: DigestSummary;
}

export type ViewMode = 'cards' | 'list' | 'glance';
export type Source = 'all' | 'reddit' | 'hn' | 'rss';
export type Category = 'all' | 'AI & ML' | 'Tech' | 'Security' | 'Science' | 'World News' | 'Business' | 'Futurology' | 'Startups';

export const CATEGORIES: Category[] = ['all', 'AI & ML', 'Tech', 'Security', 'Science', 'World News', 'Business', 'Futurology', 'Startups'];
