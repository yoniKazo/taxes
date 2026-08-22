import { Columns2 } from 'lucide-react';

import Badge from '../ui/Badge.jsx';
import DataTable from '../ui/DataTable.jsx';

function formatDate(value) {
  try {
    return new Date(value).toLocaleString('he-IL');
  } catch {
    return '—';
  }
}

/**
 * Run history, with a second run selectable for side-by-side comparison.
 *
 * A test lab exists to compare prompts, and until now it could only display one
 * run at a time -- the comparison had to happen in the reader's head.
 */
export default function RunHistoryPanel({ runs, selectedRunId, compareWith, onSelect, onCompare }) {
  const columns = [
    { key: 'id', label: '#', numeric: true, width: 48 },
    { key: 'label', label: 'שם הניסוי', render: (row) => row.label || `ריצה #${row.id}` },
    { key: 'agent_name', label: 'Agent' },
    { key: 'model', label: 'מודל', render: (row) => <span className="muted">{row.model}</span> },
    { key: 'temperature', label: 'טמפ׳', numeric: true },
    { key: 'created_at', label: 'תאריך', render: (row) => formatDate(row.created_at) },
    {
      key: 'pass_percentage',
      label: '% עברו',
      numeric: true,
      render: (row) =>
        row.pass_percentage == null ? (
          <span className="muted">—</span>
        ) : (
          <Badge tone={row.pass_percentage >= 80 ? 'good' : row.pass_percentage >= 50 ? 'ok' : 'bad'}>
            {Math.round(row.pass_percentage)}%
          </Badge>
        ),
    },
    {
      key: 'compare',
      label: 'השווה',
      sortable: false,
      render: (row) => (
        <button
          type="button"
          className={compareWith === row.id ? 'primary' : 'ghost'}
          title="הצג את הריצה הזו לצד הנבחרת"
          disabled={row.id === selectedRunId}
          onClick={(event) => {
            event.stopPropagation();
            onCompare(compareWith === row.id ? null : row.id);
          }}
        >
          <Columns2 size={14} aria-hidden />
        </button>
      ),
    },
  ];

  return (
    <DataTable
      columns={columns}
      rows={runs}
      onRowClick={(row) => onSelect(row.id)}
      selectedKey={selectedRunId}
      searchable
      searchPlaceholder="חיפוש בריצות…"
      searchFields={['label', 'agent_name', 'model']}
      initialSort={{ key: 'id', direction: 'desc' }}
      emptyMessage="אין עדיין ריצות. התחל מהפאנל ״הרצה חדשה״."
      maxHeight={420}
    />
  );
}
