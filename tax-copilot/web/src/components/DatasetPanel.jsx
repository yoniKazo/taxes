import { useState } from 'react';
import { addTestQuestion, deleteTestQuestion } from '../api/client.js';

const DATASET_NAME = 'tax_qa_v1';

export default function DatasetPanel({ questions, loading, error, onRefresh }) {
  const [newQuestion, setNewQuestion] = useState('');
  const [newCategory, setNewCategory] = useState('');
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState(null);

  async function handleAdd(event) {
    event.preventDefault();
    if (!newQuestion.trim()) {
      return;
    }
    setBusy(true);
    setActionError(null);
    try {
      await addTestQuestion({
        dataset_name: DATASET_NAME,
        category: newCategory,
        question_text: newQuestion,
      });
      setNewQuestion('');
      setNewCategory('');
      onRefresh?.();
    } catch (err) {
      setActionError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete(id) {
    setBusy(true);
    setActionError(null);
    try {
      await deleteTestQuestion(id);
      onRefresh?.();
    } catch (err) {
      setActionError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card dataset-panel">
      <h2>דאטהסט שאלות</h2>
      {error && <p className="explanation-error">שגיאה בטעינת השאלות: {error}</p>}
      {actionError && <p className="explanation-error">{actionError}</p>}

      {loading ? (
        <p>טוען...</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>שאלה</th>
              <th>קטגוריה</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {questions.map((question) => (
              <tr key={question.id}>
                <td>{question.question_text}</td>
                <td>{question.category}</td>
                <td>
                  <button type="button" onClick={() => handleDelete(question.id)} disabled={busy}>
                    מחק
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <form className="form-actions" onSubmit={handleAdd}>
        <input
          type="text"
          placeholder="קטגוריה"
          value={newCategory}
          onChange={(event) => setNewCategory(event.target.value)}
          style={{ maxWidth: '160px' }}
        />
        <input
          type="text"
          placeholder="שאלה חדשה"
          value={newQuestion}
          onChange={(event) => setNewQuestion(event.target.value)}
          style={{ flex: 1 }}
        />
        <button type="submit" className="primary" disabled={busy}>
          הוסף שאלה
        </button>
      </form>
    </div>
  );
}
