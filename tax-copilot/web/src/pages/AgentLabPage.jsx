import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Bot, ClipboardList, FlaskConical, Gauge, ListChecks, Play, Wrench,
} from 'lucide-react';
import { useCallback } from 'react';
import { toast } from 'sonner';

import {
  addAgentLabConfig, deleteAgentLabConfig, getAgentLabAnnotatedTraces, getAgentLabConfigs,
  getAgentLabCost, getAgentLabExperiments, getAgentLabMatrix, getAgentLabTasks, getAgentLabTools,
  runAgentLab,
} from '../api/client.js';
import AnnotatedTracesPanel from '../components/agentlab/AnnotatedTracesPanel.jsx';
import ConfigsPanel from '../components/agentlab/ConfigsPanel.jsx';
import MatrixPanel from '../components/agentlab/MatrixPanel.jsx';
import PlaygroundPanel from '../components/agentlab/PlaygroundPanel.jsx';
import TaskSetPanel from '../components/agentlab/TaskSetPanel.jsx';
import ToolsPanel from '../components/agentlab/ToolsPanel.jsx';
import Panel from '../components/ui/Panel.jsx';
import PanelPicker from '../components/ui/PanelPicker.jsx';
import ProcessExplainer from '../components/ui/ProcessExplainer.jsx';
import { AGENT_LAB_EXPLAINERS } from '../constants/agentLabExplainers.js';
import { usePanelPrefs } from '../hooks/usePanelPrefs.js';

const PANELS = [
  { id: 'playground', title: 'מגרש משחקים', icon: Play, cost: 'עולה קריאות LLM' },
  { id: 'tools', title: 'ה-Tools', icon: Wrench },
  { id: 'tasks', title: 'מערך המשימות', icon: ListChecks },
  { id: 'matrix', title: 'Task 5 — Agent מול RAG', icon: Gauge },
  { id: 'configs', title: 'קונפיגורציות Agent + Task 6', icon: FlaskConical },
  { id: 'annotated', title: '3 traces מוערים', icon: ClipboardList, defaultVisible: false },
];

export default function AgentLabPage() {
  const prefs = usePanelPrefs('agent-lab', PANELS);
  const queryClient = useQueryClient();

  const tools = useQuery({ queryKey: ['agent-lab-tools'], queryFn: getAgentLabTools });
  const tasks = useQuery({ queryKey: ['agent-lab-tasks'], queryFn: getAgentLabTasks });
  const configs = useQuery({ queryKey: ['agent-lab-configs'], queryFn: getAgentLabConfigs });
  const matrix = useQuery({
    queryKey: ['agent-lab-matrix'], queryFn: getAgentLabMatrix, enabled: prefs.isVisible('matrix'),
  });
  const experiments = useQuery({
    queryKey: ['agent-lab-experiments'], queryFn: getAgentLabExperiments, enabled: prefs.isVisible('configs'),
  });
  const annotated = useQuery({
    queryKey: ['agent-lab-annotated'], queryFn: getAgentLabAnnotatedTraces, enabled: prefs.isVisible('annotated'),
  });
  const cost = useQuery({ queryKey: ['agent-lab-cost'], queryFn: getAgentLabCost, staleTime: 0 });

  const runMutation = useMutation({
    mutationFn: (payload) => runAgentLab(payload),
    onSuccess: () => cost.refetch(),
    onError: (error) => toast.error(error.message),
  });

  const addConfigMutation = useMutation({
    mutationFn: (payload) => addAgentLabConfig(payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['agent-lab-configs'] }),
    onError: (error) => toast.error(error.message),
  });

  const deleteConfigMutation = useMutation({
    mutationFn: (id) => deleteAgentLabConfig(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['agent-lab-configs'] }),
    onError: (error) => toast.error(error.message),
  });

  const useTaskInPlayground = useCallback(() => {
    document.getElementById('panel-playground')?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  const panelProps = (id) => ({
    collapsed: prefs.isCollapsed(id),
    onToggleCollapsed: () => prefs.toggleCollapsed(id),
    onHide: () => prefs.toggleVisible(id),
  });

  const costData = cost.data;

  return (
    <div className="app-main">
      <div className="row between" style={{ marginBlockEnd: 'var(--space-4)' }}>
        <div>
          <h1>מעבדת Agent</h1>
          <p className="muted" style={{ margin: 0 }}>
            מטלה 4 — ReAct agent עם 3 tools, evaluator-optimizer, ו-RAG מול Agent
          </p>
        </div>
        <div className="row">
          {costData ? (
            <span className="quota-chip" title="עלות Anthropic מצטברת בסשן הזה (Agent בלבד; שיפוט evaluator-optimizer לא נספר כרגע)">
              עלות סשן: ${costData.total_usd.toFixed(4)}
            </span>
          ) : null}
          <PanelPicker panels={PANELS} prefs={prefs} />
        </div>
      </div>

      {prefs.isVisible('playground') ? (
        <div id="panel-playground">
          <Panel
            title="מגרש משחקים" icon={Play} {...panelProps('playground')}
            loading={tools.isPending || tasks.isPending || configs.isPending}
            error={tools.error?.message ?? tasks.error?.message ?? configs.error?.message}
          >
            <ProcessExplainer id="agent-lab-playground" {...AGENT_LAB_EXPLAINERS.playground} />
            <PlaygroundPanel
              tasks={tasks.data?.tasks ?? []}
              tools={tools.data?.tools ?? []}
              configs={configs.data?.configs ?? []}
              onRun={runMutation.mutate}
              isPending={runMutation.isPending}
              error={runMutation.error?.message}
              result={runMutation.data}
            />
          </Panel>
        </div>
      ) : null}

      {prefs.isVisible('tools') ? (
        <Panel title="ה-Tools" subtitle="Task 2" icon={Wrench} {...panelProps('tools')}
               loading={tools.isPending} error={tools.error?.message}>
          <ProcessExplainer id="agent-lab-tools" {...AGENT_LAB_EXPLAINERS.tools} />
          <ToolsPanel tools={tools.data?.tools ?? []} />
        </Panel>
      ) : null}

      {prefs.isVisible('tasks') ? (
        <Panel title="מערך המשימות" subtitle="Task 1" icon={ListChecks} {...panelProps('tasks')}
               loading={tasks.isPending} error={tasks.error?.message}>
          <ProcessExplainer id="agent-lab-tasks" {...AGENT_LAB_EXPLAINERS.tasks} />
          <TaskSetPanel tasks={tasks.data?.tasks ?? []} onUseTask={useTaskInPlayground} />
        </Panel>
      ) : null}

      {prefs.isVisible('matrix') ? (
        <Panel title="Task 5 — Agent מול RAG" icon={Gauge} {...panelProps('matrix')}
               loading={matrix.isPending} error={matrix.error?.message}>
          <ProcessExplainer id="agent-lab-matrix" {...AGENT_LAB_EXPLAINERS.matrix} />
          <MatrixPanel data={matrix.data ?? { available: false }} />
        </Panel>
      ) : null}

      {prefs.isVisible('configs') ? (
        <Panel title="קונפיגורציות Agent + Task 6" icon={FlaskConical} {...panelProps('configs')}
               loading={configs.isPending} error={configs.error?.message}>
          <ProcessExplainer id="agent-lab-configs" {...AGENT_LAB_EXPLAINERS.configs} />
          <ConfigsPanel
            configs={configs.data?.configs ?? []}
            onAdd={addConfigMutation.mutate}
            onDelete={deleteConfigMutation.mutate}
            experiments={experiments.data ?? { available: false, experiments: [] }}
          />
        </Panel>
      ) : null}

      {prefs.isVisible('annotated') ? (
        <Panel title="3 traces מוערים" icon={Bot} {...panelProps('annotated')}
               loading={annotated.isPending} error={annotated.error?.message}>
          <ProcessExplainer id="agent-lab-annotated" {...AGENT_LAB_EXPLAINERS.annotated} />
          <AnnotatedTracesPanel data={annotated.data ?? { available: false, traces: [] }} />
        </Panel>
      ) : null}
    </div>
  );
}
