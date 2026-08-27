import {
  BookOpen, ClipboardCheck, Eye, Network, NotebookPen, Repeat, SearchCheck, ShieldAlert,
  ShieldCheck, Users,
} from 'lucide-react';

import Panel from '../components/ui/Panel.jsx';
import PanelPicker from '../components/ui/PanelPicker.jsx';
import { ABOUT_INTRO, ABOUT_SECTIONS, ABOUT_STATS } from '../constants/aboutContent.js';
import { usePanelPrefs } from '../hooks/usePanelPrefs.js';

const PANELS = [
  { id: 'rulebook', title: 'ספר הכללים של הפרויקט', icon: BookOpen },
  { id: 'guardrails', title: 'בלמים אוטומטיים ואישורים', icon: ShieldCheck },
  { id: 'habits', title: 'הרגלים שהפכו לכפתור', icon: Repeat },
  { id: 'reviewer', title: 'בודק איכות עצמאי', icon: Eye },
  { id: 'planFirst', title: 'קודם תכנון, אחר כך קוד', icon: ClipboardCheck },
  { id: 'lessons', title: 'יומן טעויות ולקחים', icon: NotebookPen },
  { id: 'selfSearch', title: 'העוזר מחפש במאגר בעצמו', icon: SearchCheck },
  { id: 'qualityChecks', title: 'בדיקות איכות, אבטחה ועבודה עצמאית', icon: ShieldAlert },
  { id: 'aiTeam', title: 'כמה עוזרי AI עובדים יחד', icon: Users },
  { id: 'knowledgeMap', title: 'מפת ידע של כל הפרויקט', icon: Network },
];

function SectionBody({ section }) {
  return (
    <div className="stack">
      <p style={{ margin: 0 }}>{section.lead}</p>
      <div className="stack">
        {section.points.map((point) => (
          <div key={point.title}>
            <strong>{point.title}</strong>
            <p className="muted" style={{ margin: '2px 0 0' }}>{point.text}</p>
          </div>
        ))}
      </div>
      {section.example ? (
        <div className="panel-note info">
          <strong>לדוגמה: </strong>
          {section.example}
        </div>
      ) : null}
    </div>
  );
}

export default function AboutPage() {
  const prefs = usePanelPrefs('about', PANELS);

  const panelProps = (id) => ({
    collapsed: prefs.isCollapsed(id),
    onToggleCollapsed: () => prefs.toggleCollapsed(id),
    onHide: () => prefs.toggleVisible(id),
  });

  return (
    <div className="app-main narrow">
      <div className="row between" style={{ marginBlockEnd: 'var(--space-4)' }}>
        <div>
          <h1>מאחורי הקלעים: איך הפרויקט הזה נבנה</h1>
          <p className="muted" style={{ margin: 0 }}>
            מה בוצע כדי שהעוזר שכתב את הקוד יעבוד בצורה בטוחה, מבוקרת ומשתפרת — בשפה פשוטה
          </p>
        </div>
        <PanelPicker panels={PANELS} prefs={prefs} />
      </div>

      <p style={{ marginBlockEnd: 'var(--space-4)' }}>{ABOUT_INTRO}</p>

      <div className="stat-row" style={{ marginBlockEnd: 'var(--space-4)' }}>
        {ABOUT_STATS.map((stat) => (
          <div key={stat.label} className={stat.hero ? 'stat hero' : 'stat'}>
            <div className="stat-label">{stat.label}</div>
            <div className="stat-value">{stat.value}</div>
          </div>
        ))}
      </div>

      {PANELS.map((panel) => (
        prefs.isVisible(panel.id) ? (
          <Panel key={panel.id} title={panel.title} icon={panel.icon} {...panelProps(panel.id)}>
            <SectionBody section={ABOUT_SECTIONS[panel.id]} />
          </Panel>
        ) : null
      ))}
    </div>
  );
}
