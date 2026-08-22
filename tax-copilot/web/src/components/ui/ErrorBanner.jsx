import { AlertCircle } from 'lucide-react';

/**
 * The single error surface for the whole app.
 *
 * Before this there were three: this banner (calculator only), a bare red
 * paragraph (everywhere else), and two window.alert() calls. Errors that look
 * different depending on which panel raised them teach the user nothing.
 */
export default function ErrorBanner({ message, onRetry }) {
  if (!message) return null;
  return (
    <div className="error-banner" role="alert">
      <AlertCircle size={17} aria-hidden style={{ flexShrink: 0, marginBlockStart: 2 }} />
      <span className="grow">{message}</span>
      {onRetry ? (
        <button type="button" onClick={onRetry}>
          נסה שוב
        </button>
      ) : null}
    </div>
  );
}
