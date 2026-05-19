import { useState, useEffect } from 'react'
import useSettingsStore from '../../store/settingsStore'

export default function SettingsPanel({ open, onClose }) {
  const settings = useSettingsStore()
  const [form, setForm] = useState({})

  useEffect(() => {
    if (open) {
      setForm({
        sidecarUrl: settings.sidecarUrl,
        defaultModel: settings.defaultModel,
        defaultAnalysisMode: settings.defaultAnalysisMode,
        theme: settings.theme
      })
    }
  }, [open])

  if (!open) return null

  const update = (key, value) => setForm((f) => ({ ...f, [key]: value }))

  const handleSave = () => {
    settings.saveSettings(form)
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 flex">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />

      {/* Panel */}
      <div className="relative w-80 h-full bg-white dark:bg-gray-900 shadow-xl flex flex-col animate-slide-in">
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Settings</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200">✕</button>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-5">
          {/* Sidecar URL */}
          <Field label="Sidecar URL">
            <input
              type="text"
              value={form.sidecarUrl || ''}
              onChange={(e) => update('sidecarUrl', e.target.value)}
              className="input-field"
            />
          </Field>

          {/* Default Model */}
          <Field label="Default Model">
            <input
              type="text"
              value={form.defaultModel || ''}
              onChange={(e) => update('defaultModel', e.target.value)}
              placeholder="gpt-4o, claude-sonnet-4-20250514"
              className="input-field"
            />
          </Field>

          {/* Analysis Mode */}
          <Field label="Default Analysis Mode">
            <select
              value={form.defaultAnalysisMode || 'casual'}
              onChange={(e) => update('defaultAnalysisMode', e.target.value)}
              className="input-field"
            >
              <option value="casual">Casual</option>
              <option value="structured">Structured</option>
              <option value="formal">Formal</option>
            </select>
          </Field>

          {/* Theme */}
          <Field label="Theme">
            <select
              value={form.theme || 'dark'}
              onChange={(e) => update('theme', e.target.value)}
              className="input-field"
            >
              <option value="light">Light</option>
              <option value="dark">Dark</option>
              <option value="system">System</option>
            </select>
          </Field>
        </div>

        <div className="p-4 border-t border-gray-200 dark:border-gray-700">
          <button
            onClick={handleSave}
            className="w-full px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium"
          >
            Save
          </button>
        </div>
      </div>
    </div>
  )
}

function Field({ label, children }) {
  return (
    <label className="block">
      <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{label}</span>
      <div className="mt-1">{children}</div>
    </label>
  )
}
