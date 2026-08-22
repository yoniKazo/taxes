import { useCallback, useEffect } from 'react';

import { useLocalStorage } from './useLocalStorage.js';

const MODES = ['system', 'light', 'dark'];

/**
 * Three states, not two: an explicit light/dark choice stamps data-theme on the
 * root element and wins over the OS; "system" stamps nothing and lets
 * prefers-color-scheme decide. tokens.css declares the dark values under both
 * scopes so either path resolves.
 */
export function useTheme() {
  const [mode, setMode] = useLocalStorage('theme', 'system');

  useEffect(() => {
    const root = document.documentElement;
    if (mode === 'system') root.removeAttribute('data-theme');
    else root.setAttribute('data-theme', mode);
  }, [mode]);

  const cycle = useCallback(() => {
    setMode((current) => MODES[(MODES.indexOf(current) + 1) % MODES.length]);
  }, [setMode]);

  return { mode, setMode, cycle };
}
