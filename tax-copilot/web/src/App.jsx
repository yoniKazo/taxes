import { useState } from 'react';
import CalculatorPage from './pages/CalculatorPage.jsx';
import TestLabPage from './pages/TestLabPage.jsx';

const TABS = [
  { id: 'calculator', label: 'מחשבון' },
  { id: 'test-lab', label: 'בדיקות AI' },
];

export default function App() {
  const [activeTab, setActiveTab] = useState('calculator');

  return (
    <div className="app-shell">
      <header className="app-header">
        <h1>Tax Copilot</h1>
        <nav className="tab-bar">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              type="button"
              className={activeTab === tab.id ? 'tab primary' : 'tab'}
              onClick={() => setActiveTab(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </header>

      <main className="app-main">
        {activeTab === 'calculator' ? <CalculatorPage /> : <TestLabPage />}
      </main>
    </div>
  );
}
