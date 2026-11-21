import { useCallback, useEffect, useRef, useState } from 'react';
import { endCampusSession, fetchCampusAcademicData, fetchCampusSession, hasCampusIntegration } from './campusApi.js';

const disconnected = { phase: 'signedOut', session: null, academic: null, dataPhase: 'idle', logoutError: false };
const checking = { ...disconnected, phase: 'checking' };

export function useCampusConnection() {
  const [state, setState] = useState(hasCampusIntegration ? checking : { ...disconnected, phase: 'preview' });
  const operation = useRef(null);

  const refresh = useCallback(async () => {
    if (!hasCampusIntegration) return;
    operation.current?.abort();
    const controller = new AbortController();
    operation.current = controller;
    const { signal } = controller;
    setState(checking);

    try {
      const session = await fetchCampusSession(signal);
      if (signal.aborted) return;
      if (!session) {
        setState(disconnected);
        return;
      }
      const connected = { ...disconnected, phase: 'connected', session };
      setState({ ...connected, dataPhase: 'loading' });
      try {
        const academic = await fetchCampusAcademicData(signal);
        if (!signal.aborted) setState({ ...connected, academic, dataPhase: 'ready' });
      } catch (error) {
        if (signal.aborted) return;
        if (error.status === 401) setState(disconnected);
        else setState({ ...connected, dataPhase: error.status === 403 ? 'denied' : 'error' });
      }
    } catch {
      if (!signal.aborted) setState({ ...disconnected, phase: 'error' });
    }
  }, []);

  useEffect(() => {
    void refresh();
    return () => operation.current?.abort();
  }, [refresh]);

  async function logout() {
    operation.current?.abort();
    const controller = new AbortController();
    operation.current = controller;
    setState((previous) => ({ ...previous, phase: 'loggingOut', logoutError: false }));
    try {
      await endCampusSession(controller.signal);
      if (!controller.signal.aborted) setState(disconnected);
    } catch {
      if (!controller.signal.aborted) setState((previous) => ({
        ...previous, phase: 'connected', dataPhase: previous.dataPhase === 'loading' ? 'error' : previous.dataPhase, logoutError: true,
      }));
    }
  }

  return { ...state, refresh, logout };
}
