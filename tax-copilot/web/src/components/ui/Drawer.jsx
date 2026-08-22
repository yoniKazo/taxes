import { X } from 'lucide-react';
import { useEffect } from 'react';

/** Side panel for row detail -- keeps long prose out of table cells. */
export default function Drawer({ open, title, onClose, children }) {
  useEffect(() => {
    if (!open) return undefined;
    const onKeyDown = (event) => {
      if (event.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', onKeyDown);
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKeyDown);
      document.body.style.overflow = '';
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="drawer-backdrop"
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <aside className="drawer" role="dialog" aria-modal="true" aria-label={title}>
        <header className="drawer-header">
          <h2 className="grow">{title}</h2>
          <button type="button" className="icon-button" onClick={onClose} title="סגור">
            <X size={18} />
          </button>
        </header>
        <div className="drawer-body">{children}</div>
      </aside>
    </div>
  );
}

export function DrawerSection({ title, children }) {
  return (
    <section className="drawer-section">
      <h3 className="drawer-section-title">{title}</h3>
      {children}
    </section>
  );
}
