import { Inbox } from 'lucide-react';

export default function EmptyState({ title, message, icon: Icon = Inbox, action }) {
  return (
    <div className="empty-state">
      <Icon size={32} aria-hidden />
      {title ? <div className="empty-state-title">{title}</div> : null}
      <p>{message}</p>
      {action}
    </div>
  );
}
