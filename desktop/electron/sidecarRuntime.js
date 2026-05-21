const { spawn } = require('node:child_process')
const fs = require('node:fs')
const http = require('node:http')
const { join } = require('node:path')

const DEFAULT_SIDECAR_URL = 'http://127.0.0.1:8765'
const DEFAULT_ATTACH_TIMEOUT_MS = 3000
const DEFAULT_LAUNCH_RETRIES = 10
const DEFAULT_LAUNCH_RETRY_DELAY_MS = 500

function emptyPersistedSidecarConfig() {
  return { sidecar_url: '', sidecar_command: '', sidecar_args: [] }
}

function sidecarConfigPath(userDataDir) {
  return join(userDataDir, 'sidecar-config.json')
}

function sidecarUrlOverridePath(userDataDir) {
  return join(userDataDir, 'sidecar_url.txt')
}

function splitCommandLine(raw) {
  const value = String(raw || '').trim()
  const tokens = []
  let current = ''
  let quote = null

  for (const char of value) {
    if (quote) {
      if (char === quote) {
        quote = null
      } else {
        current += char
      }
      continue
    }

    if (char === '"' || char === "'") {
      quote = char
      continue
    }

    if (/\s/.test(char)) {
      if (current) {
        tokens.push(current)
        current = ''
      }
      continue
    }

    current += char
  }

  if (current) {
    tokens.push(current)
  }

  return tokens
}

function loadPersistedSidecarConfig(userDataDir, fsImpl = fs) {
  const filePath = sidecarConfigPath(userDataDir)
  if (!fsImpl.existsSync(filePath)) {
    return emptyPersistedSidecarConfig()
  }

  try {
    const raw = JSON.parse(fsImpl.readFileSync(filePath, 'utf8'))
    return {
      sidecar_url: typeof raw.sidecar_url === 'string' ? raw.sidecar_url.trim() : '',
      sidecar_command: typeof raw.sidecar_command === 'string' ? raw.sidecar_command.trim() : '',
      sidecar_args: Array.isArray(raw.sidecar_args)
        ? raw.sidecar_args.map((item) => String(item).trim()).filter(Boolean)
        : [],
    }
  } catch {
    return emptyPersistedSidecarConfig()
  }
}

function savePersistedSidecarConfig(userDataDir, nextConfig, fsImpl = fs) {
  const sanitized = {
    sidecar_url: typeof nextConfig.sidecar_url === 'string' ? nextConfig.sidecar_url.trim() : '',
    sidecar_command: typeof nextConfig.sidecar_command === 'string' ? nextConfig.sidecar_command.trim() : '',
    sidecar_args: Array.isArray(nextConfig.sidecar_args)
      ? nextConfig.sidecar_args.map((item) => String(item).trim()).filter(Boolean)
      : [],
  }

  fsImpl.mkdirSync(userDataDir, { recursive: true })
  fsImpl.writeFileSync(sidecarConfigPath(userDataDir), JSON.stringify(sanitized, null, 2), 'utf8')
  return sanitized
}

function readSidecarUrlOverride(userDataDir, fsImpl = fs) {
  const filePath = sidecarUrlOverridePath(userDataDir)
  if (!fsImpl.existsSync(filePath)) {
    return ''
  }
  return fsImpl.readFileSync(filePath, 'utf8').trim()
}

function resolveSidecarRuntimeConfig({ env = process.env, userDataDir, fsImpl = fs } = {}) {
  const persisted = loadPersistedSidecarConfig(userDataDir, fsImpl)
  const fileUrl = readSidecarUrlOverride(userDataDir, fsImpl)
  const envUrl = String(env.PYC_HERMES_SIDECAR_URL || '').trim()
  const envCommandRaw = String(env.PYC_HERMES_SIDECAR_CMD || '').trim()
  const envCommand = splitCommandLine(envCommandRaw)

  const resolvedUrl = envUrl || fileUrl || persisted.sidecar_url || DEFAULT_SIDECAR_URL
  const resolvedUrlSource = envUrl ? 'env' : fileUrl ? 'file' : persisted.sidecar_url ? 'desktop_config' : 'default'
  const launchCommand = envCommand[0] || persisted.sidecar_command || ''
  const launchArgs = envCommand.length ? envCommand.slice(1) : persisted.sidecar_args
  const launchCommandSource = envCommand.length ? 'env' : persisted.sidecar_command ? 'desktop_config' : 'none'

  return {
    resolved_url: resolvedUrl,
    resolved_url_source: resolvedUrlSource,
    launch_configured: Boolean(launchCommand),
    launch_command: launchCommand,
    launch_args: launchArgs,
    launch_command_source: launchCommandSource,
    persisted_config: persisted,
  }
}

function buildSidecarStatus(runtime) {
  return {
    startup_state: 'checking',
    resolved_url: runtime.resolved_url,
    resolved_url_source: runtime.resolved_url_source,
    launch_configured: runtime.launch_configured,
    launch_command_source: runtime.launch_command_source,
    managed_process: Boolean(runtime.managed_process),
    last_probe: null,
    last_error: null,
  }
}

function runtimeTargetsDiffer(current = {}, next = {}) {
  const currentArgs = Array.isArray(current.launch_args) ? current.launch_args : []
  const nextArgs = Array.isArray(next.launch_args) ? next.launch_args : []
  return current.resolved_url !== next.resolved_url
    || Boolean(current.launch_configured) !== Boolean(next.launch_configured)
    || (current.launch_command || '') !== (next.launch_command || '')
    || JSON.stringify(currentArgs) !== JSON.stringify(nextArgs)
}

function buildManagedExitStatus(runtime, previousStatus, exitDetails) {
  return {
    ...buildSidecarStatus(runtime),
    startup_state: 'unavailable',
    managed_process: false,
    last_probe: previousStatus?.last_probe || null,
    last_error: {
      code: 'managed_process_exited',
      message: 'Desktop-managed sidecar exited after startup completed.',
      stage: 'runtime',
      details: exitDetails,
    },
  }
}

function probeSidecarHealth(baseUrl, { httpGet = http.get, timeoutMs = DEFAULT_ATTACH_TIMEOUT_MS } = {}) {
  return new Promise((resolve) => {
    let url
    try {
      url = new URL('/health', baseUrl)
    } catch {
      resolve({ ok: false, status: 0, url: String(baseUrl || ''), error: 'invalid_url' })
      return
    }

    if (url.protocol !== 'http:') {
      resolve({ ok: false, status: 0, url: baseUrl, error: 'unsupported_protocol' })
      return
    }

    let req
    try {
      req = httpGet(url, (res) => {
        let body = ''
        res.on('data', (chunk) => {
          body += chunk
        })
        res.on('end', () => {
          try {
            const payload = JSON.parse(body)
            resolve({ ok: res.statusCode === 200, status: res.statusCode, url: baseUrl, payload })
          } catch {
            resolve({ ok: false, status: res.statusCode, url: baseUrl, rawBody: body, error: 'invalid_json' })
          }
        })
      })
    } catch (error) {
      resolve({
        ok: false,
        status: 0,
        url: baseUrl,
        error: error?.code === 'ERR_INVALID_PROTOCOL' ? 'unsupported_protocol' : error.message,
      })
      return
    }

    req.on('error', (err) => resolve({ ok: false, status: 0, url: baseUrl, error: err.message }))
    req.setTimeout(timeoutMs, () => {
      req.destroy()
      resolve({ ok: false, status: 0, url: baseUrl, error: 'timeout' })
    })
  })
}

async function attachFirstStartup(runtime, deps = {}) {
  const probeImpl = deps.probeImpl || ((baseUrl) => probeSidecarHealth(baseUrl, deps))
  const spawnImpl = deps.spawnImpl || spawn
  const sleep = deps.sleep || ((ms) => new Promise((resolve) => setTimeout(resolve, ms)))
  const launchRetries = Number.isInteger(deps.launchRetries) ? deps.launchRetries : DEFAULT_LAUNCH_RETRIES
  const launchRetryDelayMs = Number.isInteger(deps.launchRetryDelayMs) ? deps.launchRetryDelayMs : DEFAULT_LAUNCH_RETRY_DELAY_MS
  const status = buildSidecarStatus(runtime)

  const firstProbe = await probeImpl(runtime.resolved_url)
  status.last_probe = firstProbe
  if (firstProbe.ok) {
    status.startup_state = 'attached'
    return { status, child: null }
  }

  if (!runtime.launch_configured) {
    status.startup_state = 'unavailable'
    status.last_error = {
      code: 'launch_not_configured',
      message: 'Attach failed and no launch command is configured.',
      stage: 'attach',
      details: firstProbe,
    }
    return { status, child: null }
  }

  status.startup_state = 'launching'

  let child
  let earlyExit = null
  let launchError = null
  try {
    child = spawnImpl(runtime.launch_command, runtime.launch_args, { shell: false, stdio: 'ignore', windowsHide: true })
    status.managed_process = true
    if (typeof child?.once === 'function') {
      child.once('exit', (code, signal) => {
        earlyExit = { code, signal }
      })
      child.once('error', (error) => {
        launchError = error
      })
    }
  } catch (error) {
    status.startup_state = 'launch_failed'
    status.last_error = {
      code: 'launch_spawn_failed',
      message: error.message,
      stage: 'launch',
      details: { command: runtime.launch_command, args: runtime.launch_args },
    }
    return { status, child: null }
  }

  for (let attempt = 0; attempt < launchRetries; attempt += 1) {
    await sleep(launchRetryDelayMs)

    if (launchError) {
      status.startup_state = 'launch_failed'
      status.managed_process = false
      status.last_error = {
        code: 'launch_spawn_failed',
        message: launchError.message,
        stage: 'launch',
        details: { command: runtime.launch_command, args: runtime.launch_args },
      }
      return { status, child: null }
    }

    const probe = await probeImpl(runtime.resolved_url)
    status.last_probe = probe

    if (probe.ok) {
      status.startup_state = 'launched'
      return { status, child }
    }

    if (earlyExit) {
      status.startup_state = 'launch_failed'
      status.managed_process = false
      status.last_error = {
        code: 'launch_exited_early',
        message: 'Sidecar process exited before health checks passed.',
        stage: 'launch',
        details: earlyExit,
      }
      return { status, child: null }
    }
  }

  status.startup_state = 'launch_failed'
  status.last_error = {
    code: 'launch_probe_timeout',
    message: 'Sidecar did not become healthy before retry budget was exhausted.',
    stage: 'launch',
    details: { retries: launchRetries, delay_ms: launchRetryDelayMs },
  }
  return { status, child }
}

module.exports = {
  DEFAULT_SIDECAR_URL,
  DEFAULT_ATTACH_TIMEOUT_MS,
  DEFAULT_LAUNCH_RETRIES,
  DEFAULT_LAUNCH_RETRY_DELAY_MS,
  sidecarConfigPath,
  sidecarUrlOverridePath,
  splitCommandLine,
  loadPersistedSidecarConfig,
  savePersistedSidecarConfig,
  readSidecarUrlOverride,
  resolveSidecarRuntimeConfig,
  buildSidecarStatus,
  runtimeTargetsDiffer,
  buildManagedExitStatus,
  probeSidecarHealth,
  attachFirstStartup,
}
