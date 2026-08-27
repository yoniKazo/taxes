import { useMutation } from '@tanstack/react-query';
import { Award, Briefcase, Calculator, FileText, PiggyBank } from 'lucide-react';
import { useState } from 'react';

import { calculateTax } from '../api/client.js';
import CreditPointsForm from '../components/calc/CreditPointsForm.jsx';
import DeductionsForm from '../components/calc/DeductionsForm.jsx';
import ExplanationPanel from '../components/calc/ExplanationPanel.jsx';
import JobsForm from '../components/calc/JobsForm.jsx';
import ResultsPanel from '../components/calc/ResultsPanel.jsx';
import ErrorBanner from '../components/ui/ErrorBanner.jsx';
import Panel from '../components/ui/Panel.jsx';
import PanelPicker from '../components/ui/PanelPicker.jsx';
import ProcessExplainer from '../components/ui/ProcessExplainer.jsx';
import { CALCULATOR_EXPLAINERS } from '../constants/calculatorExplainers.js';
import { usePanelPrefs } from '../hooks/usePanelPrefs.js';

const PANELS = [
  { id: 'jobs', title: 'עבודות', icon: Briefcase },
  { id: 'credits', title: 'נקודות זיכוי', icon: Award },
  { id: 'deductions', title: 'הפרשות ותרומות', icon: PiggyBank },
  { id: 'results', title: 'תוצאות', icon: Calculator },
  { id: 'explanation', title: 'הסבר מילולי', icon: FileText, cost: 'עולה קריאה' },
];

let nextJobId = 1;
const makeJob = () => ({ id: nextJobId++, gross_salary: '', label: '' });

let nextChildId = 1;
const makeChild = () => ({ id: nextChildId++, age: '' });

const INITIAL_CREDIT_FIELDS = {
  gender: 'male',
  children: [],
  is_single_parent: false,
  lives_in_eligible_zone: false,
  discharged_service_enabled: false,
  discharged_service: {
    service_type: 'military',
    months_since_discharge: '',
    service_length_months: '',
  },
  new_immigrant_enabled: false,
  new_immigrant: { months_since_aliyah: '' },
  academic_degree_enabled: false,
  academic_degree: { graduation_year: '', program_years: '' },
  extra_credit_points: 0,
};

const INITIAL_DEDUCTION_FIELDS = {
  pension_employee_pct: 0,
  keren_hishtalmut_annual: 0,
  annual_donation: 0,
};

function buildPayload(jobs, creditFields, deductionFields, includeExplanation) {
  return {
    jobs: jobs.map((job) => ({
      gross_salary: Number(job.gross_salary) || 0,
      label: job.label,
    })),
    gender: creditFields.gender,
    children: creditFields.children
      .filter((child) => child.age !== '')
      .map((child) => ({ age: Number(child.age) || 0 })),
    is_single_parent: creditFields.is_single_parent,
    lives_in_eligible_zone: creditFields.lives_in_eligible_zone,
    discharged_service: creditFields.discharged_service_enabled
      ? {
          service_type: creditFields.discharged_service.service_type,
          months_since_discharge: Number(creditFields.discharged_service.months_since_discharge) || 0,
          service_length_months: Number(creditFields.discharged_service.service_length_months) || 0,
        }
      : null,
    new_immigrant: creditFields.new_immigrant_enabled
      ? { months_since_aliyah: Number(creditFields.new_immigrant.months_since_aliyah) || 0 }
      : null,
    academic_degree: creditFields.academic_degree_enabled
      ? {
          graduation_year: Number(creditFields.academic_degree.graduation_year) || 0,
          program_years: Number(creditFields.academic_degree.program_years) || 0,
        }
      : null,
    extra_credit_points: Number(creditFields.extra_credit_points) || 0,
    // השדה מוצג באחוזים (0-100); calculate() מצפה לשבר (0-1).
    pension_employee_pct: (Number(deductionFields.pension_employee_pct) || 0) / 100,
    keren_hishtalmut_annual: Number(deductionFields.keren_hishtalmut_annual) || 0,
    annual_donation: Number(deductionFields.annual_donation) || 0,
    include_explanation: includeExplanation,
  };
}

export default function CalculatorPage() {
  const prefs = usePanelPrefs('calculator', PANELS);
  const [jobs, setJobs] = useState(() => [makeJob()]);
  const [creditFields, setCreditFields] = useState(INITIAL_CREDIT_FIELDS);
  const [deductionFields, setDeductionFields] = useState(INITIAL_DEDUCTION_FIELDS);

  const wantsExplanation = prefs.isVisible('explanation');

  const calculate = useMutation({
    mutationFn: () =>
      calculateTax(buildPayload(jobs, creditFields, deductionFields, wantsExplanation)),
  });

  const panelProps = (id) => ({
    collapsed: prefs.isCollapsed(id),
    onToggleCollapsed: () => prefs.toggleCollapsed(id),
    onHide: () => prefs.toggleVisible(id),
  });

  const result = calculate.data;

  return (
    <div className="app-main narrow">
      <div className="row between" style={{ marginBlockEnd: 'var(--space-4)' }}>
        <div>
          <h1>מחשבון החזר מס</h1>
          <p className="muted" style={{ margin: 0 }}>שכירים · שנת מס 2026</p>
        </div>
        <PanelPicker panels={PANELS} prefs={prefs} />
      </div>

      <ErrorBanner message={calculate.error?.message} onRetry={() => calculate.mutate()} />

      <form
        onSubmit={(event) => {
          event.preventDefault();
          calculate.mutate();
        }}
      >
        {prefs.isVisible('jobs') ? (
          <Panel title="עבודות" icon={Briefcase} {...panelProps('jobs')}>
            <ProcessExplainer id="jobs" {...CALCULATOR_EXPLAINERS.jobs} />
            <JobsForm jobs={jobs} onChange={setJobs} makeJob={makeJob} />
          </Panel>
        ) : null}

        {prefs.isVisible('credits') ? (
          <Panel title="נקודות זיכוי" icon={Award} {...panelProps('credits')}>
            <ProcessExplainer id="credits" {...CALCULATOR_EXPLAINERS.credits} />
            <CreditPointsForm values={creditFields} onChange={setCreditFields} makeChild={makeChild} />
          </Panel>
        ) : null}

        {prefs.isVisible('deductions') ? (
          <Panel title="הפרשות ותרומות" icon={PiggyBank} {...panelProps('deductions')}>
            <ProcessExplainer id="deductions" {...CALCULATOR_EXPLAINERS.deductions} />
            <DeductionsForm values={deductionFields} onChange={setDeductionFields} />
          </Panel>
        ) : null}

        <ProcessExplainer id="submit" {...CALCULATOR_EXPLAINERS.submit} />
        <div className="row" style={{ marginBlockEnd: 'var(--space-4)' }}>
          <button type="submit" className="primary" disabled={calculate.isPending}>
            <Calculator size={15} aria-hidden />
            {calculate.isPending ? 'מחשב…' : 'חשב מס'}
          </button>
          {wantsExplanation ? <span className="cost-hint">כולל הסבר · קריאה 1</span> : null}
        </div>
      </form>

      {prefs.isVisible('results') && (result || calculate.isPending) ? (
        <Panel
          title="תוצאות"
          icon={Calculator}
          {...panelProps('results')}
          loading={calculate.isPending}
          skeletonRows={4}
        >
          <ProcessExplainer id="results" {...CALCULATOR_EXPLAINERS.results} />
          <ResultsPanel result={result} />
        </Panel>
      ) : null}

      {wantsExplanation && (result || calculate.isPending) ? (
        <Panel title="הסבר מילולי" icon={FileText} {...panelProps('explanation')}>
          <ProcessExplainer id="explanation" {...CALCULATOR_EXPLAINERS.explanation} />
          <ExplanationPanel
            loading={calculate.isPending}
            explanation={result?.explanation}
            explanationError={result?.explanation_error}
          />
        </Panel>
      ) : null}
    </div>
  );
}
