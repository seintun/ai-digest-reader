import type { Story, ViewMode, Source } from '../types';
import { rankStories } from './ranking';

interface AppState {
  viewMode: ViewMode;
  source: Source;
  stories: Story[];
  loading: boolean;
  error: string | null;
}

const STORAGE_KEY = 'ai-digest-reader-state';

const defaultState: AppState = {
  viewMode: 'cards',
  source: 'all',
  stories: [],
  loading: false,
  error: null,
};

const listeners = new Set<(state: AppState) => void>();

let state: AppState = { ...defaultState };

function loadPersistedState(): Partial<AppState> {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      const parsed = JSON.parse(stored);
      return {
        viewMode: parsed.viewMode ?? defaultState.viewMode,
        source: parsed.source ?? defaultState.source,
      };
    }
  } catch {
    // Ignore localStorage errors
  }
  return {};
}

function persistState(): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      viewMode: state.viewMode,
      source: state.source,
    }));
  } catch {
    // Ignore localStorage errors
  }
}

function notifyListeners(): void {
  listeners.forEach((listener) => listener(state));
}

function dispatchEvent(name: string, detail?: Partial<AppState>): void {
  window.dispatchEvent(new CustomEvent(name, { detail }));
}

function createStateUpdater<K extends keyof AppState>(key: K) {
  return (value: AppState[K]): void => {
    state[key] = value;
    if (key === 'viewMode' || key === 'source') {
      persistState();
    }
    notifyListeners();
    dispatchEvent(`state:${key}Changed`, { [key]: value });
  };
}

state = {
  ...defaultState,
  ...loadPersistedState(),
};

export const setViewMode: (mode: ViewMode) => void = createStateUpdater('viewMode');
export const setSource: (source: Source) => void = createStateUpdater('source');
export const setStories = createStateUpdater('stories');
export const setLoading = createStateUpdater('loading');
export const setError = createStateUpdater('error');

export function getState(): AppState {
  return state;
}

export function getFilteredStories(): Story[] {
  const { source, stories } = state;
  
  if (source === 'all') {
    return rankStories(stories);
  }
  
  return stories.filter((story) => {
    const [prefix] = story.i.split('-');
    if (source === 'reddit') {
      return prefix === 'rd';
    }
    if (source === 'hn') {
      return prefix === 'hn';
    }
    return true;
  });
}

export function subscribe(listener: (state: AppState) => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function resetState(): void {
  state = {
    ...defaultState,
    ...loadPersistedState(),
  };
  notifyListeners();
  dispatchEvent('state:reset');
}
