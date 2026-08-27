export default function ToolsPanel({ tools }) {
  return (
    <div className="checklist">
      {tools.map((tool) => (
        <div key={tool.name} style={{ marginBlockEnd: 'var(--space-4)' }}>
          <strong>{tool.name}</strong>
          <p style={{ whiteSpace: 'pre-wrap', marginBlockStart: 'var(--space-1)' }}>{tool.description}</p>
          <table style={{ width: '100%', fontSize: '0.9em' }}>
            <thead>
              <tr><th style={{ textAlign: 'right' }}>ארגומנט</th><th style={{ textAlign: 'right' }}>סוג</th><th style={{ textAlign: 'right' }}>חובה</th></tr>
            </thead>
            <tbody>
              {Object.entries(tool.properties).map(([name, schema]) => (
                <tr key={name}>
                  <td>{name}</td>
                  <td>{schema.type}{schema.default !== undefined ? ` (ברירת מחדל: ${schema.default})` : ''}</td>
                  <td>{tool.required.includes(name) ? 'כן' : 'לא'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
    </div>
  );
}
