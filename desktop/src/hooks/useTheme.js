import { useEffect } from 'react'
import useSettingsStore from '../store/settingsStore'

export default function useTheme() {
  const theme = useSettingsStore((s) => s.theme)

  useEffect(() => {
    const root = document.documentElement

    if (theme === 'system') {
      const mq = window.matchMedia('(prefers-color-scheme: dark)')
      const apply = () => {
        root.classList.toggle('dark', mq.matches)
      }
      apply()
      mq.addEventListener('change', apply)
      return () => mq.removeEventListener('change', apply)
    }

    root.classList.toggle('dark', theme === 'dark')
  }, [theme])
}
