import type { Story } from '../types';

function minMax(values: number[]): { min: number; max: number } {
  const min = Math.min(...values);
  const max = Math.max(...values);
  return { min, max };
}

function normalize(value: number, min: number, max: number): number {
  if (max === min) {
    return 0.5;
  }
  return (value - min) / (max - min);
}

export function rankStories(stories: Story[]): Story[] {
  if (stories.length === 0) {
    return stories;
  }

  const groups = new Map<string, Story[]>();
  for (const story of stories) {
    const prefix = story.i.split('-')[0] ?? '';
    if (!groups.has(prefix)) {
      groups.set(prefix, []);
    }
    groups.get(prefix)?.push(story);
  }

  const rankMap = new Map<string, number>();

  for (const [, group] of groups) {
    const scores = group.map((story) => story.s);
    const comments = group.map((story) => story.c);
    const hasScore = scores.some((value) => value > 0);
    const hasComments = comments.some((value) => value > 0);

    const { min: sMin, max: sMax } = minMax(scores);
    const { min: cMin, max: cMax } = minMax(comments);

    let wScore = 0;
    let wComments = 0;
    let wRecency = 0.3;

    if (hasScore && hasComments) {
      wScore = 0.4;
      wComments = 0.3;
    } else if (hasScore) {
      wScore = 0.7;
    } else if (hasComments) {
      wComments = 0.7;
    } else {
      wRecency = 1;
    }

    for (const story of group) {
      const normScore = hasScore ? normalize(story.s, sMin, sMax) : 0;
      const normComments = hasComments ? normalize(story.c, cMin, cMax) : 0;
      const recency = 0.5;

      rankMap.set(story.i, wScore * normScore + wComments * normComments + wRecency * recency);
    }
  }

  return [...stories].sort((a, b) => (rankMap.get(b.i) ?? 0) - (rankMap.get(a.i) ?? 0));
}
