import {
  Bot, Calculator, FlaskConical, Info, Monitor, Moon, Search, Sun,
} from 'lucide-react';
import { NavLink, Navigate, Route, Routes } from 'react-router-dom';

import { useTheme } from './hooks/useTheme.js';
import AboutPage from './pages/AboutPage.jsx';
import AgentLabPage from './pages/AgentLabPage.jsx';
import CalculatorPage from './pages/CalculatorPage.jsx';
import RagLabPage from './pages/RagLabPage.jsx';
import TestLabPage from './pages/TestLabPage.jsx';

// "מעבדת Agent" (מטלה 4, ReAct tool-calling agent) היא מושג נפרד לגמרי מ-"בדיקות AI"
// (מטלה 2, קונפיגורציות LLM-writer) -- ראו plans/assignment4-plan.md.
const NAV = [
  { to: '/calculator', label: 'מחשבון', icon: Calculator },
  { to: '/lab', label: 'בדיקות AI', icon: FlaskConical },
  { to: '/rag', label: 'מעבדת RAG', icon: Search },
  { to: '/agent-lab', label: 'מעבדת Agent', icon: Bot },
  { to: '/about', label: 'מאחורי הקלעים', icon: Info },
];

const THEME_ICONS = { system: Monitor, light: Sun, dark: Moon };
const THEME_LABELS = { system: 'לפי המערכת', light: 'בהיר', dark: 'כהה' };

export default function App() {
  const theme = useTheme();
  const ThemeIcon = THEME_ICONS[theme.mode];

  return (
    <div className="app-shell">
      <header className="app-header">
        <span className="app-brand">
          <FlaskConical size={20} aria-hidden />
          Tax Copilot
        </span>

        {/* Narrow screens get tabs here; from 1200px up the sidebar takes over
            and CSS hides this copy. */}
        <nav className="tab-bar" aria-label="ניווט ראשי">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => (isActive ? 'tab active' : 'tab')}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <span className="app-header-spacer" />

        <div className="app-header-tools">
          <button
            type="button"
            className="ghost"
            onClick={theme.cycle}
            title={`ערכת נושא: ${THEME_LABELS[theme.mode]}`}
          >
            <ThemeIcon size={16} aria-hidden />
            <span className="nowrap">{THEME_LABELS[theme.mode]}</span>
          </button>
        </div>
      </header>

      <div className="app-body">
        <aside className="app-sidebar">
          <nav className="sidebar-nav" aria-label="ניווט">
            {NAV.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) => (isActive ? 'sidebar-link active' : 'sidebar-link')}
              >
                <item.icon size={16} aria-hidden />
                {item.label}
              </NavLink>
            ))}
          </nav>
        </aside>

        <main>
          <Routes>
            <Route path="/" element={<Navigate to="/calculator" replace />} />
            <Route path="/calculator" element={<CalculatorPage />} />
            <Route path="/lab" element={<TestLabPage />} />
            <Route path="/rag" element={<RagLabPage />} />
            <Route path="/agent-lab" element={<AgentLabPage />} />
            <Route path="/about" element={<AboutPage />} />
            <Route path="*" element={<Navigate to="/calculator" replace />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}
