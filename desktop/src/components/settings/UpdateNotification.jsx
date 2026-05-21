import { useState, useEffect } from 'react'

export default function UpdateNotification() {
  const [update, setUpdate] = useState({ state: 'none' })

  useEffect(() => {
    if (!window.updater) return
    window.updater.onStatus((data) => setUpdate(data))
  }, [])

  if (update.state === 'none' || update.state === 'checking' || update.state === 'error') {
    return null
  }

  return (
    <div className="flex items-center justify-between px-4 py-2 bg-blue-600 text-white text-sm">
      {update.state === 'available' && (
        <>
          <span>Update v{update.version} available</span>
          <button
            onClick={() => window.updater.download()}
            className="ml-4 px-3 py-1 bg-white text-blue-600 rounded text-xs font-medium"
          >
            Download
          </button>
        </>
      )}
      {update.state === 'downloading' && (
        <span>Downloading update... {update.percent}%</span>
      )}
      {update.state === 'ready' && (
        <>
          <span>Update v{update.version} ready to install</span>
          <button
            onClick={() => window.updater.install()}
            className="ml-4 px-3 py-1 bg-white text-blue-600 rounded text-xs font-medium"
          >
            Restart &amp; Install
          </button>
        </>
      )}
      <button
        onClick={() => setUpdate({ state: 'none' })}
        className="ml-4 text-white/70 hover:text-white"
      >
        &times;
      </button>
    </div>
  )
}
