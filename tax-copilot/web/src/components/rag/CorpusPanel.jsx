import { ExternalLink, FileText } from 'lucide-react';

import DataTable from '../ui/DataTable.jsx';
import Badge from '../ui/Badge.jsx';
import Stat from '../ui/Stat.jsx';

/** Task 1: what is actually in the corpus, and how much of it there is. */
export default function CorpusPanel({ data, selectedDocs, onToggleDoc }) {
  const documents = data?.documents ?? [];

  const columns = [
    {
      key: 'selected',
      label: '',
      sortable: false,
      width: 36,
      render: (row) => (
        <input
          type="checkbox"
          checked={selectedDocs.includes(row.doc_name)}
          onChange={() => onToggleDoc(row.doc_name)}
          aria-label={`כלול את ${row.doc_name} באינדוקס`}
          onClick={(event) => event.stopPropagation()}
        />
      ),
    },
    {
      key: 'doc_name',
      label: 'מסמך',
      render: (row) => (
        <span className="row" style={{ gap: 6, flexWrap: 'nowrap' }}>
          <FileText size={14} aria-hidden style={{ color: 'var(--text-muted)', flexShrink: 0 }} />
          <span>{row.doc_name}</span>
        </span>
      ),
    },
    {
      key: 'format',
      label: 'פורמט',
      render: (row) => (
        <Badge tone={row.format === 'pdf' ? 'warning' : 'info'}>{row.format}</Badge>
      ),
    },
    { key: 'topic', label: 'נושא' },
    { key: 'chunk_count', label: "צ'אנקים", numeric: true },
    {
      key: 'source_url',
      label: 'מקור',
      sortable: false,
      render: (row) => (
        <a href={row.source_url} target="_blank" rel="noreferrer" title={row.source_url}>
          <ExternalLink size={14} aria-hidden />
        </a>
      ),
    },
  ];

  return (
    <>
      <div className="stat-row" style={{ marginBlockEnd: 'var(--space-4)' }}>
        <Stat label="מסמכים" value={documents.length} caption="המטלה דורשת 5–10" />
        <Stat
          label="פורמטים"
          value={(data?.formats ?? []).join(' + ')}
          caption="המטלה דורשת לפחות 2"
        />
        <Stat label="סה״כ צ'אנקים" value={data?.total_chunks ?? 0} caption="ב-1000/150" />
      </div>

      <p className="muted" style={{ marginBlockEnd: 'var(--space-3)' }}>
        סמן מסמכים כדי לכלול אותם בבניית אינדקס מותאם בפאנל <strong>קונפיגורציית אינדקס</strong>.
      </p>

      <DataTable columns={columns} rows={documents} rowKey={(row) => row.doc_name} />
    </>
  );
}
