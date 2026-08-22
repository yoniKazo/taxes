import { useMutation, useQuery } from '@tanstack/react-query';
import { useCallback, useEffect, useRef, useState } from 'react';
import { toast } from 'sonner';

import { cancelRagJob, getRagJob } from '../api/client.js';

/**
 * Start a background job and poll it until it stops.
 *
 * Index builds and hit-rate sweeps take minutes; without this the UI can only
 * offer a disabled button and hope. Polling stops the moment the job reaches a
 * terminal state, so an idle tab is not hitting the server forever.
 *
 * The terminal handler runs in an effect rather than a query callback: React
 * Query v5 removed useQuery's onSuccess, and a ref latch is what keeps a
 * re-render of an already-finished job from firing the toast a second time.
 */
export function useJob({ start, onDone, successMessage, intervalMs = 700 }) {
  const [jobId, setJobId] = useState(null);
  const settledRef = useRef(null);

  const startMutation = useMutation({
    mutationFn: start,
    onSuccess: (job) => {
      settledRef.current = null;
      setJobId(job.job_id);
    },
    onError: (error) => toast.error(error.message),
  });

  const { data: job } = useQuery({
    queryKey: ['rag-job', jobId],
    queryFn: () => getRagJob(jobId),
    enabled: Boolean(jobId),
    refetchInterval: (query) =>
      ['done', 'error', 'cancelled'].includes(query.state.data?.status) ? false : intervalMs,
  });

  useEffect(() => {
    if (!job || !['done', 'error', 'cancelled'].includes(job.status)) return;
    if (settledRef.current === job.job_id) return;
    settledRef.current = job.job_id;

    if (job.status === 'done') {
      if (successMessage) toast.success(successMessage);
      onDone?.(job.result);
    } else if (job.status === 'error') {
      toast.error(job.error ?? 'המשימה נכשלה.');
    } else {
      toast('המשימה בוטלה.');
    }
  }, [job, onDone, successMessage]);

  const cancel = useCallback(() => {
    if (jobId) cancelRagJob(jobId).catch((error) => toast.error(error.message));
  }, [jobId]);

  const status = job?.status ?? (startMutation.isPending ? 'pending' : 'idle');

  return {
    job,
    status,
    running: status === 'pending' || status === 'running',
    result: job?.status === 'done' ? job.result : null,
    start: startMutation.mutate,
    cancel,
  };
}
