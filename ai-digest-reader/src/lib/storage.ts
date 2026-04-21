const BOOKMARKS_KEY = 'bookmarks';
const THEME_KEY = 'theme';

export function loadBookmarks(): Set<string> {
  try {
    const raw = localStorage.getItem(BOOKMARKS_KEY);
    return new Set(raw ? (JSON.parse(raw) as string[]) : []);
  } catch {
    return new Set();
  }
}

export function saveBookmarks(bookmarks: Set<string>): void {
  localStorage.setItem(BOOKMARKS_KEY, JSON.stringify([...bookmarks]));
}

export function loadTheme(): 'dark' | 'light' | null {
  const val = localStorage.getItem(THEME_KEY);
  if (val === 'dark' || val === 'light') return val;
  return null;
}

export function saveTheme(theme: 'dark' | 'light'): void {
  localStorage.setItem(THEME_KEY, theme);
}
