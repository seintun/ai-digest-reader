import type { Story, Digest, DigestSummary } from '../types';
import { z } from 'zod';

// --- Zod schema mirrors the Python TypedDict contract in schema.py ---

const MustReadItemSchema = z.object({
  id: z.string(),
  title: z.string(),
  url: z.string(),
  reason: z.string(),
});

const FullBriefSectionSchema = z.object({
  heading: z.string(),
  body: z.string(),
});

const FullBriefSchema = z.object({
  intro: z.string(),
  sections: z.array(FullBriefSectionSchema).min(1),
  closing: z.string(),
});

const DigestSummarySchema = z.object({
  schema_version: z.literal('2'),
  simple: z.string(),
  structured: z.object({
    themes: z.array(z.string()).length(3),
    breaking: z.string(),
    mustRead: z.array(MustReadItemSchema).length(3),
  }),
  fullBrief: FullBriefSchema,
});

const StorySchema = z.object({
  i: z.string(),
  t: z.string(),
  u: z.string(),
  p: z.string().optional(),
  b: z.string().optional(),
  s: z.number(),
  c: z.number(),
  a: z.string(),
});

const DigestSchema = z.object({
  v: z.union([z.literal(1), z.literal(2)]),
  d: z.string(),
  g: z.string(),
  r: z.array(StorySchema),
  h: z.array(StorySchema),
  summary: DigestSummarySchema.optional(),
});

export function validateSummary(data: unknown): DigestSummary | undefined {
  const result = DigestSummarySchema.safeParse(data);
  if (!result.success) {
    console.warn('DigestSummary schema validation failed:', result.error.issues);
    return undefined;
  }
  return result.data as DigestSummary;
}

let cachedDigest: Digest | null = null;
let loadingPromise: Promise<Digest> | null = null;

export async function fetchDigest(): Promise<Digest> {
  if (cachedDigest) {
    return cachedDigest;
  }

  if (loadingPromise) {
    return loadingPromise;
  }

  loadingPromise = fetch('/data/digest.json')
    .then((response) => {
      if (!response.ok) {
        throw new Error(`Failed to fetch digest: ${response.status} ${response.statusText}`);
      }
      return response.json();
    })
    .then((data: unknown) => {
      const result = DigestSchema.safeParse(data);
      if (!result.success) {
        throw new Error(`Digest schema validation failed: ${result.error.issues[0]?.message ?? 'unknown error'}`);
      }

      const digest = result.data as Digest;
      // Validate summary if present — degrade gracefully on schema mismatch
      if (digest.summary !== undefined) {
        digest.summary = validateSummary(digest.summary);
      }
      cachedDigest = digest;
      loadingPromise = null;
      return digest;
    })
    .catch((error) => {
      loadingPromise = null;
      throw error;
    });

  return loadingPromise;
}

export function getAllStories(): Story[] {
  if (!cachedDigest) {
    return [];
  }
  return [...cachedDigest.r, ...cachedDigest.h];
}

export function getRedditStories(): Story[] {
  if (!cachedDigest) {
    return [];
  }
  return [...cachedDigest.r];
}

export function getHNStories(): Story[] {
  if (!cachedDigest) {
    return [];
  }
  return [...cachedDigest.h];
}

export function getStoryById(id: string): Story | undefined {
  if (!cachedDigest) {
    return undefined;
  }

  const [prefix] = id.split('-');

  if (prefix === 'rd') {
    return cachedDigest.r.find((story) => story.i === id);
  }
  if (prefix === 'hn') {
    return cachedDigest.h.find((story) => story.i === id);
  }

  return cachedDigest.r.find((story) => story.i === id)
    ?? cachedDigest.h.find((story) => story.i === id);
}

export function getDigestDate(): string | null {
  return cachedDigest?.d ?? null;
}

export function getDigestGenerated(): string | null {
  return cachedDigest?.g ?? null;
}

export function clearCache(): void {
  cachedDigest = null;
  loadingPromise = null;
}
