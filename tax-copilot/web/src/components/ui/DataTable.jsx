import { ArrowDown, ArrowUp, Search } from 'lucide-react';
import { useMemo, useState } from 'react';

import EmptyState from './EmptyState.jsx';

/**
 * Sortable, searchable table with a sticky header and its own horizontal scroll.
 *
 * The scroll container matters: several of these tables are 7+ columns inside a
 * page that also has to fit on a laptop, and without it the whole document
 * scrolls sideways instead of the table.
 *
 * columns: [{ key, label, render?, sortValue?, numeric?, width? }]
 */
export default function DataTable({
  columns,
  rows,
  rowKey = (row, i) => row.id ?? i,
  onRowClick,
  selectedKey,
  searchable = false,
  searchPlaceholder = 'חיפוש…',
  searchFields,
  initialSort,
  toolbar,
  emptyMessage = 'אין שורות להצגה.',
  maxHeight,
}) {
  const [query, setQuery] = useState('');
  const [sort, setSort] = useState(initialSort ?? null);

  const filtered = useMemo(() => {
    if (!query.trim()) return rows;
    const needle = query.trim().toLowerCase();
    const fields = searchFields ?? columns.map((c) => c.key);
    return rows.filter((row) =>
      fields.some((field) => String(row[field] ?? '').toLowerCase().includes(needle)),
    );
  }, [rows, query, searchFields, columns]);

  const sorted = useMemo(() => {
    if (!sort) return filtered;
    const column = columns.find((c) => c.key === sort.key);
    if (!column) return filtered;
    const value = column.sortValue ?? ((row) => row[column.key]);
    const direction = sort.direction === 'asc' ? 1 : -1;
    return [...filtered].sort((a, b) => {
      const [x, y] = [value(a), value(b)];
      if (x == null && y == null) return 0;
      if (x == null) return 1;
      if (y == null) return -1;
      if (typeof x === 'number' && typeof y === 'number') return (x - y) * direction;
      return String(x).localeCompare(String(y), 'he') * direction;
    });
  }, [filtered, sort, columns]);

  const toggleSort = (key) =>
    setSort((current) =>
      current?.key === key
        ? { key, direction: current.direction === 'asc' ? 'desc' : 'asc' }
        : { key, direction: 'asc' },
    );

  return (
    <div>
      {searchable || toolbar ? (
        <div className="toolbar">
          {searchable ? (
            <div className="row grow" style={{ maxWidth: 300 }}>
              <Search size={15} aria-hidden style={{ color: 'var(--text-muted)' }} />
              <input
                type="search"
                className="search-input grow"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder={searchPlaceholder}
                aria-label={searchPlaceholder}
              />
            </div>
          ) : null}
          {toolbar}
          <span className="muted nowrap" style={{ marginInlineStart: 'auto' }}>
            {sorted.length === rows.length
              ? `${rows.length} שורות`
              : `${sorted.length} מתוך ${rows.length}`}
          </span>
        </div>
      ) : null}

      {sorted.length === 0 ? (
        <EmptyState message={emptyMessage} />
      ) : (
        <div className="table-scroll" style={maxHeight ? { maxHeight, overflowY: 'auto' } : undefined}>
          <table>
            <thead>
              <tr>
                {columns.map((column) => (
                  <th
                    key={column.key}
                    className={[column.numeric ? 'num' : '', column.sortable === false ? '' : 'sortable']
                      .filter(Boolean)
                      .join(' ')}
                    style={column.width ? { width: column.width } : undefined}
                    onClick={column.sortable === false ? undefined : () => toggleSort(column.key)}
                    aria-sort={
                      sort?.key === column.key
                        ? sort.direction === 'asc'
                          ? 'ascending'
                          : 'descending'
                        : undefined
                    }
                  >
                    <span className="row" style={{ gap: 4, flexWrap: 'nowrap' }}>
                      {column.label}
                      {sort?.key === column.key
                        ? sort.direction === 'asc'
                          ? <ArrowUp size={12} />
                          : <ArrowDown size={12} />
                        : null}
                    </span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sorted.map((row, index) => {
                const key = rowKey(row, index);
                return (
                  <tr
                    key={key}
                    className={[
                      onRowClick ? 'clickable' : '',
                      selectedKey != null && selectedKey === key ? 'selected-row' : '',
                    ].filter(Boolean).join(' ')}
                    onClick={onRowClick ? () => onRowClick(row) : undefined}
                    // Clickable rows were mouse-only before -- a <tr> with an
                    // onClick and no role or key handler is invisible to the
                    // keyboard.
                    role={onRowClick ? 'button' : undefined}
                    tabIndex={onRowClick ? 0 : undefined}
                    onKeyDown={
                      onRowClick
                        ? (event) => {
                            if (event.key === 'Enter' || event.key === ' ') {
                              event.preventDefault();
                              onRowClick(row);
                            }
                          }
                        : undefined
                    }
                  >
                    {columns.map((column) => (
                      <td key={column.key} className={column.numeric ? 'num' : undefined}>
                        {column.render ? column.render(row) : row[column.key]}
                      </td>
                    ))}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
