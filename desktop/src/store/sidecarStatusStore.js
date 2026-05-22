import { create } from 'zustand'

const POLL_INTERVAL_MS = 15000

/**
 * Normalize health probe result from main (ipc `sidecar:health`).
 */
async function probeHealthSafe() {
  if (typeof window === 'undefined' || !window.sidecar?.checkHealth) {
    return { ok: false, error: 'sidecar preload unavailable' }
  }
  try {
    return await window.sidecar.checkHealth()
  } catch (e) {
    return { ok: false, error: e?.message || String(e) }
  }
}

/**
 * Derives a single banner tier for Phase3A degraded/unavailable UX.
 */
export function deriveSidecarBanner({ runtimeStatus, health, refreshError }) {
  if (refreshError) {
    return {
      visible: true,
      tier: 'error',
      title: '状态刷新失败',
      detail: refreshError,
      showRestart: true,
    }
  }

  if (!runtimeStatus || typeof runtimeStatus !== 'object') {
    return { visible: false, tier: 'hidden', title: '', detail: '', showRestart: false }
  }

  const startup = runtimeStatus.startup_state || 'unknown'
  const lastErr = runtimeStatus.launch_error || runtimeStatus.last_error

  if (startup === 'launch_failed') {
    return {
      visible: true,
      tier: 'error',
      title: '侧车进程启动失败',
      detail: lastErr?.message || '请检查启动命令与 PATH。',
      showRestart: true,
    }
  }

  if (startup === 'launching') {
    return {
      visible: true,
      tier: 'info',
      title: '侧车正在启动…',
      detail: '',
      showRestart: false,
    }
  }

  if (startup === 'unavailable' && lastErr) {
    return {
      visible: true,
      tier: 'error',
      title: '侧车不可用',
      detail: lastErr.message || String(lastErr.code || 'attached URL unreachable'),
      showRestart: true,
    }
  }

  const pl = health && health.ok === true ? health.payload : null
  if (!pl && health && health.ok === false) {
    return {
      visible: true,
      tier: 'error',
      title: '无法连接侧车',
      detail:
        health.error ||
        (typeof health.status === 'number' && health.status !== 0
          ? `HTTP ${health.status}`
          : 'network or HTTP probe failed'),
      showRestart: true,
    }
  }

  if (pl) {
    const label = pl.status_label || pl.state
    if (label === 'unavailable' || pl.state === 'unavailable') {
      return {
        visible: true,
        tier: 'error',
        title: '侧车服务不可用',
        detail: (pl.degradation_reasons && pl.degradation_reasons[0]) || '至少一个关键组件不可用。',
        showRestart: true,
      }
    }
    if (label === 'degraded' || pl.degraded === true) {
      return {
        visible: true,
        tier: 'warn',
        title: '侧车降级运行',
        detail:
          Array.isArray(pl.degradation_reasons) && pl.degradation_reasons.length > 0
            ? pl.degradation_reasons.join(' · ')
            : '',
        showRestart: false,
      }
    }
    if (label === 'ready-with-warnings') {
      return {
        visible: true,
        tier: 'info',
        title: '侧车已就绪（有告警）',
        detail:
          Array.isArray(pl.degradation_reasons) && pl.degradation_reasons.length > 0
            ? pl.degradation_reasons.join(' · ')
            : '',
        showRestart: false,
      }
    }
  }

  return { visible: false, tier: 'hidden', title: '', detail: '', showRestart: false }
}

export const useSidecarStatusStore = create((set, get) => ({
  fetchState: 'idle',
  runtimeStatus: null,
  health: null,
  lastRefreshAt: null,
  refreshError: null,

  refresh: async () => {
    if (typeof window === 'undefined' || !window.sidecar?.getStatus) {
      return
    }

    set({ fetchState: 'refreshing', refreshError: null })
    try {
      const runtimeStatus = await window.sidecar.getStatus()
      const health = await probeHealthSafe()
      set({
        runtimeStatus,
        health,
        lastRefreshAt: Date.now(),
        fetchState: 'idle',
        refreshError: null,
      })
    } catch (e) {
      set({
        fetchState: 'idle',
        refreshError: e?.message || String(e),
      })
    }
  },

  restart: async () => {
    if (typeof window === 'undefined' || !window.sidecar?.restart) {
      return get().refresh()
    }
    set({ fetchState: 'refreshing', refreshError: null })
    try {
      const runtimeStatus = await window.sidecar.restart()
      const health = await probeHealthSafe()
      set({
        runtimeStatus,
        health,
        lastRefreshAt: Date.now(),
        fetchState: 'idle',
        refreshError: null,
      })
    } catch (e) {
      set({
        fetchState: 'idle',
        refreshError: e?.message || String(e),
      })
    }
  },

  pollingHandle: null,

  startPolling: () => {
    const { pollingHandle } = get()
    if (pollingHandle) {
      clearInterval(pollingHandle)
    }
    get().refresh()
    const handle = setInterval(() => get().refresh(), POLL_INTERVAL_MS)
    set({ pollingHandle: handle })
  },

  stopPolling: () => {
    const { pollingHandle } = get()
    if (pollingHandle) {
      clearInterval(pollingHandle)
    }
    set({ pollingHandle: null })
  },
}))

export const useSidecarBanner = () =>
  useSidecarStatusStore((s) =>
    deriveSidecarBanner({
      runtimeStatus: s.runtimeStatus,
      health: s.health,
      refreshError: s.refreshError,
    }),
  )
