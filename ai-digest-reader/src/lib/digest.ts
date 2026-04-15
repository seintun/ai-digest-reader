import type { Story, Digest } from '../types';

interface DigestResponse {
  v: 1;
  d: string;
  g: string;
  r: Story[];
  h: Story[];
}

let cachedDigest: DigestResponse | null = null;
let loadingPromise: Promise<DigestResponse> | null = null;

export async function fetchDigest(): Promise<DigestResponse> {
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
    .then((data: DigestResponse) => {
      if (data.v !== 1) {
        throw new Error(`Unsupported digest version: ${data.v}`);
      }
      cachedDigest = data;
      loadingPromise = null;
      return data;
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
