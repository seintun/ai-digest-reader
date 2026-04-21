// Augments the global Window interface so component scripts
// can call these hooks without casting to any.

export {};  // makes this a module

declare global {
  interface Window {
    updateSearchInfo?: (count: number, query: string) => void;
    setNavActive?: (nav: string) => void;
    updateBookmarkBadge?: (count: number) => void;
  }
}
