import { useSidecarBanner, useSidecarStatusStore } from '../../store/sidecarStatusStore'
import useUiStore from '../../store/uiStore'

const tierClasses = {
  error: 'bg-red-600/95 text-white border-b border-red-700',
  warn: 'bg-amber-500/95 text-gray-950 border-b border-amber-600',
  info: 'bg-sky-600/95 text-white border-b border-sky-700',
}

export default function SidecarStatusBanner() {
  const banner = useSidecarBanner()
  const fetchState = useSidecarStatusStore((s) => s.fetchState)
  const refresh = useSidecarStatusStore((s) => s.refresh)
  const restart = useSidecarStatusStore((s) => s.restart)
  const requestSettingsPanel = useUiStore((s) => s.requestSettingsPanel)

  if (!banner.visible) {
    return null
  }

  const barClass =
    tierClasses[banner.tier] ||
    tierClasses.info

  return (
    <div
      role="status"
      className={`shrink-0 px-4 py-2 text-xs flex flex-wrap items-center gap-x-4 gap-y-2 ${barClass}`}
    >
      <div className="font-medium">{banner.title}</div>
      {banner.detail ? <div className="opacity-90 flex-1 min-w-[12rem]">{banner.detail}</div> : null}
      <div className="flex items-center gap-2 ml-auto">
        {fetchState === 'refreshing' ? (
          <span className="opacity-80">刷新中…</span>
        ) : null}
        <button
          type="button"
          onClick={() => refresh()}
          className="px-2 py-1 rounded bg-white/15 hover:bg-white/25 transition"
        >
          刷新状态
        </button>
        {banner.tier === 'error' && banner.showRestart ? (
          <button
            type="button"
            onClick={() => requestSettingsPanel()}
            className="px-2 py-1 rounded bg-white/15 hover:bg-white/25 transition"
            title="在设置中核对侧车 URL / 启动命令（见 README Sidecar Startup）"
          >
            连接设置
          </button>
        ) : null}
        {banner.showRestart ? (
          <button
            type="button"
            onClick={() => restart()}
            className="px-2 py-1 rounded bg-white/90 text-gray-900 hover:bg-white font-medium"
          >
            重启侧车
          </button>
        ) : null}
      </div>
    </div>
  )
}
