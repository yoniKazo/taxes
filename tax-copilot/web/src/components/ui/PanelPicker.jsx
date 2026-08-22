import { SlidersHorizontal } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';

/** Choose which panels this page shows. Selection persists per page. */
export default function PanelPicker({ panels, prefs }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    if (!open) return undefined;
    const onPointerDown = (event) => {
      if (ref.current && !ref.current.contains(event.target)) setOpen(false);
    };
    const onKeyDown = (event) => {
      if (event.key === 'Escape') setOpen(false);
    };
    document.addEventListener('pointerdown', onPointerDown);
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('pointerdown', onPointerDown);
      document.removeEventListener('keydown', onKeyDown);
    };
  }, [open]);

  return (
    <div className="picker" ref={ref}>
      <button type="button" onClick={() => setOpen((v) => !v)} aria-expanded={open}>
        <SlidersHorizontal size={15} aria-hidden />
        פאנלים ({prefs.visibleCount}/{panels.length})
      </button>

      {open ? (
        <div className="picker-menu" role="menu">
          <div className="picker-menu-title">מה להציג במסך</div>
          {panels.map((panel) => (
            <label key={panel.id} className="picker-item">
              <input
                type="checkbox"
                checked={prefs.isVisible(panel.id)}
                onChange={() => prefs.toggleVisible(panel.id)}
              />
              <span className="grow">{panel.title}</span>
              {panel.cost ? <span className="cost-hint">{panel.cost}</span> : null}
            </label>
          ))}
          <div className="divider" style={{ margin: 'var(--space-2) 0' }} />
          <button type="button" className="ghost" onClick={prefs.reset} style={{ width: '100%' }}>
            אפס לברירת המחדל
          </button>
        </div>
      ) : null}
    </div>
  );
}
