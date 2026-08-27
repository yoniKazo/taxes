import { ChevronDown, ChevronUp, Info } from 'lucide-react';

import { useLocalStorage } from '../../hooks/useLocalStorage.js';

/**
 * Plain-language "what happens on this screen" box for non-technical users:
 * what runs, what costs LLM tokens, and what's free and how. Collapse state
 * is remembered per panel (independent of the panel's own collapse state),
 * open by default so first-time visitors see it.
 */
export default function ProcessExplainer({ id, process, cost, free }) {
  const [collapsed, setCollapsed] = useLocalStorage(`explainer-collapsed:${id}`, false);

  return (
    <div className="panel-note info explainer">
      <button
        type="button"
        className="explainer-toggle"
        onClick={() => setCollapsed((current) => !current)}
        aria-expanded={!collapsed}
      >
        <Info size={14} aria-hidden />
        <span className="grow">איך זה עובד</span>
        {collapsed ? <ChevronDown size={14} aria-hidden /> : <ChevronUp size={14} aria-hidden />}
      </button>
      {collapsed ? null : (
        <dl className="explainer-body">
          <dt>מה קורה כאן</dt>
          <dd>{process}</dd>
          <dt>מה עולה טוקנים</dt>
          <dd>{cost}</dd>
          <dt>מה בחינם</dt>
          <dd>{free}</dd>
        </dl>
      )}
    </div>
  );
}
