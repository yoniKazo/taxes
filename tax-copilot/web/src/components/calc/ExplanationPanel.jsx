import { Check, Copy } from 'lucide-react';
import { useState } from 'react';

import Skeleton from '../ui/Skeleton.jsx';

export default function ExplanationPanel({ loading, explanation, explanationError }) {
  const [copied, setCopied] = useState(false);

  if (loading) return <Skeleton rows={3} />;

  if (explanationError) {
    return (
      <p style={{ color: 'var(--danger-fg)' }}>
        לא ניתן היה להפיק הסבר כרגע: {explanationError}
      </p>
    );
  }

  if (!explanation) return null;

  return (
    <>
      {/* pre-wrap, not a bare <p>: the model returns paragraph breaks and they
          were being collapsed into one wall of text. */}
      <p style={{ whiteSpace: 'pre-wrap', lineHeight: 1.8 }}>{explanation}</p>

      <button
        type="button"
        className="ghost"
        onClick={() => {
          navigator.clipboard.writeText(explanation);
          setCopied(true);
          setTimeout(() => setCopied(false), 1800);
        }}
      >
        {copied ? <Check size={14} aria-hidden /> : <Copy size={14} aria-hidden />}
        {copied ? 'הועתק' : 'העתק'}
      </button>
    </>
  );
}
