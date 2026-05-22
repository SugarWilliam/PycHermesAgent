import { useEffect } from 'react'
import AppLayout from './components/layout/AppLayout'
import useSettingsStore from './store/settingsStore'
import { useSidecarStatusStore } from './store/sidecarStatusStore'
import useTheme from './hooks/useTheme'

export default function App() {
  useEffect(() => {
    useSettingsStore.getState().loadSettings()
  }, [])

  useEffect(() => {
    useSidecarStatusStore.getState().startPolling()
    return () => useSidecarStatusStore.getState().stopPolling()
  }, [])

  useTheme()

  return <AppLayout />
}
