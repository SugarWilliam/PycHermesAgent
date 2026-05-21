const test = require('node:test')
const assert = require('node:assert/strict')
const { EventEmitter } = require('node:events')
const fs = require('node:fs')
const os = require('node:os')
const { join } = require('node:path')

const {
  DEFAULT_SIDECAR_URL,
  attachFirstStartup,
  buildManagedExitStatus,
  buildSidecarStatus,
  probeSidecarHealth,
  runtimeTargetsDiffer,
  splitCommandLine,
  resolveSidecarRuntimeConfig,
} = require('./sidecarRuntime')

test('splitCommandLine preserves quoted args', () => {
  assert.deepEqual(
    splitCommandLine('pyc-hermes-sidecar "--host=127.0.0.1" --port 8765'),
    ['pyc-hermes-sidecar', '--host=127.0.0.1', '--port', '8765']
  )
})

test('resolveSidecarRuntimeConfig prefers env over file and config', () => {
  const userDataDir = fs.mkdtempSync(join(os.tmpdir(), 'pyc-hermes-sidecar-'))
  fs.writeFileSync(
    join(userDataDir, 'sidecar-config.json'),
    JSON.stringify({
      sidecar_url: 'http://persisted:9000',
      sidecar_command: 'pyc-hermes-sidecar',
      sidecar_args: ['--port', '9000'],
    }),
    'utf8'
  )
  fs.writeFileSync(join(userDataDir, 'sidecar_url.txt'), 'http://file:9100\n', 'utf8')

  const runtime = resolveSidecarRuntimeConfig({
    env: {
      PYC_HERMES_SIDECAR_URL: 'http://env:9200',
      PYC_HERMES_SIDECAR_CMD: 'pyc-hermes-sidecar --port 9200',
    },
    userDataDir,
  })

  assert.equal(runtime.resolved_url, 'http://env:9200')
  assert.equal(runtime.resolved_url_source, 'env')
  assert.equal(runtime.launch_command, 'pyc-hermes-sidecar')
  assert.deepEqual(runtime.launch_args, ['--port', '9200'])
  assert.equal(runtime.launch_command_source, 'env')
})

test('resolveSidecarRuntimeConfig falls back from file to config to default', () => {
  const userDataDir = fs.mkdtempSync(join(os.tmpdir(), 'pyc-hermes-sidecar-'))
  fs.writeFileSync(
    join(userDataDir, 'sidecar-config.json'),
    JSON.stringify({ sidecar_url: 'http://persisted:9000', sidecar_command: '', sidecar_args: [] }),
    'utf8'
  )
  fs.writeFileSync(join(userDataDir, 'sidecar_url.txt'), 'http://file:9100\n', 'utf8')

  const fileRuntime = resolveSidecarRuntimeConfig({ env: {}, userDataDir })
  assert.equal(fileRuntime.resolved_url, 'http://file:9100')
  assert.equal(fileRuntime.resolved_url_source, 'file')

  fs.unlinkSync(join(userDataDir, 'sidecar_url.txt'))
  const configRuntime = resolveSidecarRuntimeConfig({ env: {}, userDataDir })
  assert.equal(configRuntime.resolved_url, 'http://persisted:9000')
  assert.equal(configRuntime.resolved_url_source, 'desktop_config')

  fs.unlinkSync(join(userDataDir, 'sidecar-config.json'))
  const defaultRuntime = resolveSidecarRuntimeConfig({ env: {}, userDataDir })
  assert.equal(defaultRuntime.resolved_url, DEFAULT_SIDECAR_URL)
  assert.equal(defaultRuntime.resolved_url_source, 'default')
})

test('resolveSidecarRuntimeConfig ignores invalid persisted config JSON', () => {
  const userDataDir = fs.mkdtempSync(join(os.tmpdir(), 'pyc-hermes-sidecar-'))
  fs.writeFileSync(join(userDataDir, 'sidecar-config.json'), '{invalid json', 'utf8')

  const runtime = resolveSidecarRuntimeConfig({ env: {}, userDataDir })

  assert.equal(runtime.resolved_url, DEFAULT_SIDECAR_URL)
  assert.equal(runtime.resolved_url_source, 'default')
  assert.equal(runtime.launch_configured, false)
})

test('buildSidecarStatus publishes snake_case startup contract fields', () => {
  const status = buildSidecarStatus({
    resolved_url: 'http://127.0.0.1:8765',
    resolved_url_source: 'desktop_config',
    launch_configured: true,
    launch_command_source: 'desktop_config',
  })

  assert.equal(status.resolved_url, 'http://127.0.0.1:8765')
  assert.equal(status.resolved_url_source, 'desktop_config')
  assert.equal(status.launch_configured, true)
  assert.equal(status.launch_command_source, 'desktop_config')
  assert.equal('resolvedUrl' in status, false)
})

test('runtimeTargetsDiffer ignores non-effective config changes', () => {
  assert.equal(
    runtimeTargetsDiffer(
      {
        resolved_url: 'http://127.0.0.1:8765',
        launch_configured: true,
        launch_command: 'pyc-hermes-sidecar',
        launch_args: ['--port', '8765'],
      },
      {
        resolved_url: 'http://127.0.0.1:8765',
        launch_configured: true,
        launch_command: 'pyc-hermes-sidecar',
        launch_args: ['--port', '8765'],
      }
    ),
    false
  )
})

test('runtimeTargetsDiffer detects managed sidecar target changes', () => {
  assert.equal(
    runtimeTargetsDiffer(
      {
        resolved_url: 'http://127.0.0.1:8765',
        launch_configured: true,
        launch_command: 'pyc-hermes-sidecar',
        launch_args: ['--port', '8765'],
      },
      {
        resolved_url: 'http://127.0.0.1:9999',
        launch_configured: false,
        launch_command: '',
        launch_args: [],
      }
    ),
    true
  )
})

test('buildManagedExitStatus marks launched managed sidecar as unavailable', () => {
  const status = buildManagedExitStatus(
    {
      resolved_url: 'http://127.0.0.1:8765',
      resolved_url_source: 'desktop_config',
      launch_configured: true,
      launch_command_source: 'desktop_config',
    },
    {
      startup_state: 'launched',
      resolved_url: 'http://127.0.0.1:8765',
      resolved_url_source: 'desktop_config',
      launch_configured: true,
      launch_command_source: 'desktop_config',
      managed_process: true,
      last_probe: { ok: true, status: 200 },
      last_error: null,
    },
    { code: 1, signal: null }
  )

  assert.equal(status.startup_state, 'unavailable')
  assert.equal(status.managed_process, false)
  assert.equal(status.last_probe.ok, true)
  assert.equal(status.last_error.code, 'managed_process_exited')
  assert.equal(status.last_error.stage, 'runtime')
})

test('probeSidecarHealth returns invalid_url for malformed URLs', async () => {
  const probe = await probeSidecarHealth('not a url')

  assert.equal(probe.ok, false)
  assert.equal(probe.error, 'invalid_url')
})

test('probeSidecarHealth reports unsupported protocol instead of throwing', async () => {
  const probe = await probeSidecarHealth('https://127.0.0.1:8765')

  assert.equal(probe.ok, false)
  assert.equal(probe.error, 'unsupported_protocol')
})

test('attachFirstStartup attaches without spawning when probe succeeds', async () => {
  const runtime = {
    resolved_url: 'http://127.0.0.1:8765',
    resolved_url_source: 'default',
    launch_configured: true,
    launch_command: 'pyc-hermes-sidecar',
    launch_args: ['--port', '8765'],
    launch_command_source: 'desktop_config',
  }

  const result = await attachFirstStartup(runtime, {
    probeImpl: async () => ({ ok: true, status: 200, url: runtime.resolved_url, payload: { status_label: 'ready' } }),
    spawnImpl: () => { throw new Error('spawn should not run') },
    sleep: async () => {},
  })

  assert.equal(result.status.startup_state, 'attached')
  assert.equal(result.status.managed_process, false)
})

test('attachFirstStartup launches after attach failure and reaches launched', async () => {
  let attempts = 0
  let spawnCalls = 0
  const child = new EventEmitter()
  child.pid = 4321
  child.kill = () => {}

  const result = await attachFirstStartup(
    {
      resolved_url: 'http://127.0.0.1:8765',
      resolved_url_source: 'desktop_config',
      launch_configured: true,
      launch_command: 'pyc-hermes-sidecar',
      launch_args: ['--port', '8765'],
      launch_command_source: 'desktop_config',
    },
    {
      probeImpl: async () => {
        attempts += 1
        return attempts < 2
          ? { ok: false, status: 0, url: 'http://127.0.0.1:8765', error: 'ECONNREFUSED' }
          : { ok: true, status: 200, url: 'http://127.0.0.1:8765', payload: { status_label: 'ready' } }
      },
      spawnImpl: () => {
        spawnCalls += 1
        return child
      },
      sleep: async () => {},
      launchRetries: 2,
      launchRetryDelayMs: 0,
    }
  )

  assert.equal(spawnCalls, 1)
  assert.equal(result.status.startup_state, 'launched')
  assert.equal(result.status.managed_process, true)
})

test('attachFirstStartup reports launch_spawn_failed when spawn throws', async () => {
  const result = await attachFirstStartup(
    {
      resolved_url: 'http://127.0.0.1:8765',
      resolved_url_source: 'desktop_config',
      launch_configured: true,
      launch_command: 'pyc-hermes-sidecar',
      launch_args: ['--port', '8765'],
      launch_command_source: 'desktop_config',
    },
    {
      probeImpl: async () => ({ ok: false, status: 0, url: 'http://127.0.0.1:8765', error: 'ECONNREFUSED' }),
      spawnImpl: () => { throw new Error('missing executable') },
      sleep: async () => {},
    }
  )

  assert.equal(result.status.startup_state, 'launch_failed')
  assert.equal(result.status.last_error.code, 'launch_spawn_failed')
})

test('attachFirstStartup reports launch_spawn_failed when child emits error', async () => {
  const child = new EventEmitter()
  child.pid = 1234
  child.kill = () => {}

  const resultPromise = attachFirstStartup(
    {
      resolved_url: 'http://127.0.0.1:8765',
      resolved_url_source: 'desktop_config',
      launch_configured: true,
      launch_command: 'pyc-hermes-sidecar',
      launch_args: ['--port', '8765'],
      launch_command_source: 'desktop_config',
    },
    {
      probeImpl: async () => ({ ok: false, status: 0, url: 'http://127.0.0.1:8765', error: 'ECONNREFUSED' }),
      spawnImpl: () => {
        queueMicrotask(() => {
          child.emit('error', new Error('missing executable'))
        })
        return child
      },
      sleep: async () => {},
      launchRetries: 2,
      launchRetryDelayMs: 0,
    }
  )

  const result = await resultPromise

  assert.equal(result.status.startup_state, 'launch_failed')
  assert.equal(result.status.last_error.code, 'launch_spawn_failed')
  assert.equal(result.status.managed_process, false)
})

test('attachFirstStartup keeps timed-out child managed for cleanup', async () => {
  const child = new EventEmitter()
  child.pid = 9999
  let killCalls = 0
  child.kill = () => {
    killCalls += 1
  }

  const result = await attachFirstStartup(
    {
      resolved_url: 'http://127.0.0.1:8765',
      resolved_url_source: 'desktop_config',
      launch_configured: true,
      launch_command: 'pyc-hermes-sidecar',
      launch_args: ['--port', '8765'],
      launch_command_source: 'desktop_config',
    },
    {
      probeImpl: async () => ({ ok: false, status: 0, url: 'http://127.0.0.1:8765', error: 'ECONNREFUSED' }),
      spawnImpl: () => child,
      sleep: async () => {},
      launchRetries: 2,
      launchRetryDelayMs: 0,
    }
  )

  assert.equal(result.status.startup_state, 'launch_failed')
  assert.equal(result.status.last_error.code, 'launch_probe_timeout')
  assert.equal(result.status.managed_process, true)
  assert.equal(result.child, child)
  assert.equal(killCalls, 0)
})
