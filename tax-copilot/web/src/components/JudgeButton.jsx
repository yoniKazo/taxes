import { useState } from 'react';
import { runJudge } from '../api/client.js';

export default function JudgeButton({ testRunId, onJudged }) {
  const [running, setRunning] = useState(false);
  const [error, setError] = useState(null);

  async function handleClick() {
    setRunning(true);
    setError(null);
    try {
      await runJudge(testRunId);
      onJudged?.();
    } catch (err) {
      setError(err.message);
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="judge-button">
      <button type="button" className="primary" onClick={handleClick} disabled={running || !testRunId}>
        {running ? 'שופט...' : 'הפעל judge'}
      </button>
      {error && <p className="explanation-error">{error}</p>}
    </div>
  );
}
