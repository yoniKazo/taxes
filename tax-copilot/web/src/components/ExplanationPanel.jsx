export default function ExplanationPanel({ loading, explanation, explanationError }) {
  if (loading) {
    return (
      <div className="card explanation-panel">
        <h2>הסבר</h2>
        <div className="skeleton-line" style={{ width: '100%' }} />
        <div className="skeleton-line" style={{ width: '90%' }} />
        <div className="skeleton-line" style={{ width: '75%' }} />
      </div>
    );
  }

  if (explanationError) {
    return (
      <div className="card explanation-panel">
        <h2>הסבר</h2>
        <p className="explanation-error">לא ניתן היה להפיק הסבר כרגע: {explanationError}</p>
      </div>
    );
  }

  if (!explanation) {
    return null;
  }

  return (
    <div className="card explanation-panel">
      <h2>הסבר</h2>
      <p>{explanation}</p>
    </div>
  );
}
