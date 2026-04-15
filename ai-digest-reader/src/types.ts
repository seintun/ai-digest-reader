export interface Story {
  i: string;
  t: string;
  u: string;
  s: number;
  c: number;
  a: string;
}

export interface MustReadItem {
  id: string;     // story reference e.g. "rd-0", "hn-2"
  title: string;  // story title (plain text)
  url: string;    // direct URL to story
  reason: string; // one sentence why it matters
}

export interface FullBriefSection {
  heading: string; // plain text section title
  body: string;    // plain text paragraph
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
    themes: string[];       // exactly 3
    breaking: string;
    mustRead: MustReadItem[]; // exactly 3
  };
  fullBrief: FullBrief;
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
