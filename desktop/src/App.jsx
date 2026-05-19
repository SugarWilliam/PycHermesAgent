import { useEffect } from 'react'
import AppLayout from './components/layout/AppLayout'
import useSettingsStore from './store/settingsStore'
import useTheme from './hooks/useTheme'

export default function App() {
  useEffect(() => {
    useSettingsStore.getState().loadSettings()
  }, [])

  useTheme()

  return <AppLayout />
}
