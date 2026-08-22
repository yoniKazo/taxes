import { useEffect, useState } from 'react';

/**
 * Two-step destructive action: the button becomes "בטוח?" and only the second
 * click fires. Deleting a dataset question used to be one unconfirmed click with
 * no undo.
 */
export default function ConfirmButton({
  onConfirm,
  children,
  confirmLabel = 'בטוח?',
  className = 'ghost',
  title,
  disabled,
}) {
  const [armed, setArmed] = useState(false);

  useEffect(() => {
    if (!armed) return undefined;
    const timer = setTimeout(() => setArmed(false), 4000);
    return () => clearTimeout(timer);
  }, [armed]);

  return (
    <button
      type="button"
      className={armed ? 'danger' : className}
      title={title}
      disabled={disabled}
      onClick={() => {
        if (armed) {
          setArmed(false);
          onConfirm();
        } else {
          setArmed(true);
        }
      }}
    >
      {armed ? confirmLabel : children}
    </button>
  );
}
