import { useState, useEffect } from 'react'
import useSettingsStore from '../../store/settingsStore'
import { useSidecarStatusStore } from '../../store/sidecarStatusStore'

export default function SettingsPanel({ open, onClose }) {
  const settings = useSettingsStore()
  const [form, setForm] = useState({})

  useEffect(() => {
    if (!open) return

    let cancelled = false

    async function loadForm() {
      const runtimeConfig = await window.sidecar?.getRuntimeConfig?.()
      const runtimeStatus = await window.sidecar?.getStatus?.()
      if (cancelled) return

      setForm({
        defaultModel: settings.defaultModel,
        defaultAnalysisMode: settings.defaultAnalysisMode,
        theme: settings.theme,
        sidecar_url: runtimeConfig?.persisted_config?.sidecar_url || '',
        sidecar_command: runtimeConfig?.persisted_config?.sidecar_command || '',
        sidecar_args_text: (runtimeConfig?.persisted_config?.sidecar_args || []).join('\n'),
        resolved_url: runtimeConfig?.resolved_url || '',
        resolved_url_source: runtimeConfig?.resolved_url_source || 'default',
        launch_command_source: runtimeConfig?.launch_command_source || 'none',
        startup_state: runtimeStatus?.startup_state || 'checking'
      })
    }

    loadForm()
    return () => {
      cancelled = true
    }
  }, [open, settings.defaultModel, settings.defaultAnalysisMode, settings.theme])

  if (!open) return null

  const update = (key, value) => setForm((current) => ({ ...current, [key]: value }))

  const handleSave = async () => {
    settings.saveSettings({
      defaultModel: form.defaultModel,
      defaultAnalysisMode: form.defaultAnalysisMode,
      theme: form.theme
    })

    await window.sidecar?.setRuntimeConfig?.({
      sidecar_url: form.sidecar_url,
      sidecar_command: form.sidecar_command,
      sidecar_args: String(form.sidecar_args_text || '').split(/\r?\n/).map((line) => line.trim()).filter(Boolean)
    })

    useSidecarStatusStore.getState().refresh()

    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 flex">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />

      <div className="relative w-96 h-full bg-white dark:bg-gray-900 shadow-xl flex flex-col animate-slide-in">
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Settings</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200">✕</button>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-5">
          <div className="rounded-lg border border-gray-200 dark:border-gray-700 p-3 text-xs text-gray-600 dark:text-gray-300 space-y-1">
            <div><strong>Resolved URL:</strong> {form.resolved_url || 'Not resolved yet'}</div>
            <div><strong>URL Source:</strong> {form.resolved_url_source}</div>
            <div><strong>Launch Source:</strong> {form.launch_command_source}</div>
            <div><strong>Startup State:</strong> {form.startup_state}</div>
          </div>

          <Field label="Sidecar URL">
            <input
              type="text"
              value={form.sidecar_url || ''}
              onChange={(e) => update('sidecar_url', e.target.value)}
              className="input-field"
            />
          </Field>

          <Field label="Sidecar Launch Command">
            <input
              type="text"
              value={form.sidecar_command || ''}
              onChange={(e) => update('sidecar_command', e.target.value)}
              className="input-field"
            />
          </Field>

          <Field label="Sidecar Launch Args (one per line)">
            <textarea
              value={form.sidecar_args_text || ''}
              onChange={(e) => update('sidecar_args_text', e.target.value)}
              className="input-field min-h-28"
            />
          </Field>

          <Field label="Default Model">
            <input
              type="text"
              value={form.defaultModel || ''}
              onChange={(e) => update('defaultModel', e.target.value)}
              placeholder="gpt-4o, claude-sonnet-4-20250514"
              className="input-field"
            />
          </Field>

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
