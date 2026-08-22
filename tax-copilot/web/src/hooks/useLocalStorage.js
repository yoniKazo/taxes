import { useCallback, useState } from 'react';

/**
 * useState backed by localStorage.
 *
 * Reads lazily and swallows storage errors: a private-mode browser or a corrupt
 * value should cost the user a preference, never a blank screen.
 */
export function useLocalStorage(key, initialValue) {
  const [value, setValue] = useState(() => {
    try {
      const stored = window.localStorage.getItem(key);
      return stored === null ? initialValue : JSON.parse(stored);
    } catch {
      return initialValue;
    }
  });

  const update = useCallback(
    (next) => {
      setValue((current) => {
        const resolved = typeof next === 'function' ? next(current) : next;
        try {
          window.localStorage.setItem(key, JSON.stringify(resolved));
        } catch {
          // out of quota or blocked -- keep the in-memory value
        }
        return resolved;
      });
    },
    [key],
  );

  return [value, update];
}
