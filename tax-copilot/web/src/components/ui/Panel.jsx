import { ChevronDown, ChevronUp, X } from 'lucide-react';

import EmptyState from './EmptyState.jsx';
import ErrorBanner from './ErrorBanner.jsx';
import Skeleton from './Skeleton.jsx';

/**
 * The card every page is built from: a titled section that can be folded shut
 * or removed from the page entirely.
 *
 * It also owns the loading/error/empty rendering, so those look the same
 * everywhere instead of each panel inventing its own "טוען..." paragraph.
 */
export default function Panel({
  title,
  subtitle,
  icon: Icon,
  actions,
  children,
  collapsed = false,
  onToggleCollapsed,
  onHide,
  loading = false,
  error = null,
  isEmpty = false,
  emptyMessage = 'אין נתונים להצגה.',
  flush = false,
  skeletonRows = 3,
}) {
  return (
    <section className={collapsed ? 'panel collapsed' : 'panel'}>
      <header className="panel-header">
        <h2 className="panel-title">
          {Icon ? <Icon size={17} aria-hidden /> : null}
          <span className="grow">{title}</span>
          {subtitle ? <span className="panel-subtitle">{subtitle}</span> : null}
        </h2>
        {actions && !collapsed ? <div className="panel-actions">{actions}</div> : null}
        {onToggleCollapsed ? (
          <button
            type="button"
            className="panel-toggle"
            onClick={onToggleCollapsed}
            aria-expanded={!collapsed}
            title={collapsed ? 'פתח' : 'מזער'}
          >
            {collapsed ? <ChevronDown size={16} /> : <ChevronUp size={16} />}
          </button>
        ) : null}
        {onHide ? (
          <button type="button" className="panel-toggle" onClick={onHide} title="הסתר פאנל">
            <X size={16} />
          </button>
        ) : null}
      </header>

      {collapsed ? null : (
        <div className={flush ? 'panel-body flush' : 'panel-body'}>
          {error ? <ErrorBanner message={error} /> : null}
          {loading ? <Skeleton rows={skeletonRows} /> : null}
          {!loading && !error && isEmpty ? <EmptyState message={emptyMessage} /> : null}
          {!loading && !error && !isEmpty ? children : null}
        </div>
      )}
    </section>
  );
}
