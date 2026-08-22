import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, Trash2 } from 'lucide-react';
import { useState } from 'react';
import { toast } from 'sonner';

import { addTestQuestion, deleteTestQuestion } from '../../api/client.js';
import ConfirmButton from '../ui/ConfirmButton.jsx';
import DataTable from '../ui/DataTable.jsx';

const DATASET_NAME = 'tax_qa_v1';

export default function DatasetPanel({ questions }) {
  const queryClient = useQueryClient();
  const [text, setText] = useState('');
  const [category, setCategory] = useState('');

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['test-questions'] });

  const add = useMutation({
    mutationFn: () =>
      addTestQuestion({
        dataset_name: DATASET_NAME,
        category: category.trim() || null,
        question_text: text.trim(),
      }),
    onSuccess: () => {
      toast.success('השאלה נוספה.');
      setText('');
      invalidate();
    },
    onError: (error) => toast.error(error.message),
  });

  const remove = useMutation({
    mutationFn: deleteTestQuestion,
    onSuccess: () => {
      toast.success('השאלה הוסרה.');
      invalidate();
    },
    onError: (error) => toast.error(error.message),
  });

  const columns = [
    { key: 'question_text', label: 'שאלה' },
    { key: 'category', label: 'קטגוריה', render: (row) => row.category || <span className="muted">—</span> },
    {
      key: 'actions',
      label: '',
      sortable: false,
      width: 90,
      render: (row) => (
        // Deleting used to be a single unconfirmed click with no undo.
        <ConfirmButton onConfirm={() => remove.mutate(row.id)} title="מחק שאלה">
          <Trash2 size={14} aria-hidden />
        </ConfirmButton>
      ),
    },
  ];

  return (
    <>
      <DataTable
        columns={columns}
        rows={questions}
        searchable
        searchPlaceholder="חיפוש בשאלות…"
        searchFields={['question_text', 'category']}
        emptyMessage="הדאטהסט ריק. הוסף שאלה למטה."
        maxHeight={380}
      />

      <form
        className="row"
        style={{ marginBlockStart: 'var(--space-4)', flexWrap: 'nowrap' }}
        onSubmit={(event) => {
          event.preventDefault();
          add.mutate();
        }}
      >
        <input
          value={category}
          onChange={(event) => setCategory(event.target.value)}
          placeholder="קטגוריה"
          style={{ maxWidth: 160 }}
          aria-label="קטגוריה"
        />
        <input
          className="grow"
          value={text}
          onChange={(event) => setText(event.target.value)}
          placeholder="שאלה חדשה…"
          aria-label="שאלה חדשה"
        />
        <button type="submit" className="primary" disabled={!text.trim() || add.isPending}>
          <Plus size={15} aria-hidden />
          הוסף
        </button>
      </form>
    </>
  );
}
