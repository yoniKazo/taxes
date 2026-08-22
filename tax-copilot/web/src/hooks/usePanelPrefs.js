import { useCallback, useMemo } from 'react';

import { useLocalStorage } from './useLocalStorage.js';

/**
 * Which panels a page shows, and which are folded shut. Persisted per page.
 *
 * Stored as an override map rather than a list of visible ids, so a panel added
 * in a later version appears for existing users instead of being silently
 * hidden by a saved list that predates it.
 */
export function usePanelPrefs(pageId, panels) {
  const [prefs, setPrefs] = useLocalStorage(`panel-prefs:${pageId}`, {
    hidden: [],
    collapsed: [],
  });

  const hidden = useMemo(() => new Set(prefs.hidden ?? []), [prefs.hidden]);
  const collapsed = useMemo(() => new Set(prefs.collapsed ?? []), [prefs.collapsed]);

  const defaultHidden = useMemo(
    () => new Set(panels.filter((p) => p.defaultVisible === false).map((p) => p.id)),
    [panels],
  );

  // Boolean(), not the raw expression: `prefs.shown?.includes(id)` is undefined
  // until the user first toggles something, and a checkbox given checked={undefined}
  // is an UNCONTROLLED input. It then flipped to controlled on the first toggle,
  // which React warns about and which makes the picker's own checkboxes behave
  // inconsistently on their first click.
  const isVisible = useCallback(
    (id) => Boolean(hidden.has(id) ? false : !defaultHidden.has(id) || prefs.shown?.includes(id)),
    [hidden, defaultHidden, prefs.shown],
  );

  const toggleVisible = useCallback(
    (id) => {
      setPrefs((current) => {
        const nextHidden = new Set(current.hidden ?? []);
        const nextShown = new Set(current.shown ?? []);
        const visible = nextHidden.has(id)
          ? false
          : !defaultHidden.has(id) || nextShown.has(id);
        if (visible) {
          nextShown.delete(id);
          nextHidden.add(id);
        } else {
          nextHidden.delete(id);
          nextShown.add(id);
        }
        return { ...current, hidden: [...nextHidden], shown: [...nextShown] };
      });
    },
    [setPrefs, defaultHidden],
  );

  const toggleCollapsed = useCallback(
    (id) => {
      setPrefs((current) => {
        const next = new Set(current.collapsed ?? []);
        if (next.has(id)) next.delete(id);
        else next.add(id);
        return { ...current, collapsed: [...next] };
      });
    },
    [setPrefs],
  );

  const reset = useCallback(() => setPrefs({ hidden: [], collapsed: [], shown: [] }), [setPrefs]);

  const visiblePanels = useMemo(
    () => panels.filter((panel) => isVisible(panel.id)),
    [panels, isVisible],
  );

  return {
    isVisible,
    isCollapsed: useCallback((id) => collapsed.has(id), [collapsed]),
    toggleVisible,
    toggleCollapsed,
    reset,
    visiblePanels,
    visibleCount: visiblePanels.length,
  };
}
