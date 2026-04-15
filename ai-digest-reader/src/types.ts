export interface Story {
  i: string;
  t: string;
  u: string;
  s: number;
  c: number;
  a: string;
}

export interface Digest {
  v: 1;
  d: string;
  g: string;
  r: Story[];
  h: Story[];
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
