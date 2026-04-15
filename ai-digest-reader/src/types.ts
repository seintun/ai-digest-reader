export interface Story {
  i: string;
  t: string;
  u: string;
  s: number;
  c: number;
  a: string;
}

export interface MustReadItem {
  id: string;
  t: string;
  url: string;
  reason: string;
}

export interface DigestSummary {
  simple: string;
  structured: {
    themes: string[];
    breaking: string;
    mustRead: MustReadItem[];
  };
  fullBrief: string;
}

export interface Digest {
  v: 1 | 2;
  d: string;
  g: string;
  r: Story[];
  h: Story[];
  summary?: DigestSummary;
}

export type ViewMode = 'cards' | 'list' | 'glance';
export type Source = 'reddit' | 'hn' | 'all';

export interface FilterState {
  source: Source;
  searchQuery: string;
  minScore: number;
}

export interface StoryWithMeta extends Story {
  source: 'reddit' | 'hn';
  domain: string;
}
