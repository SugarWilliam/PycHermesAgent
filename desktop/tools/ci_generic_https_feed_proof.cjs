/**
 * CI / dev proof: HTTPS loopback publishes `latest-linux.yml` and verifies
 * `electron-updater` GenericProvider parses it (same code path production uses for generic feeds).
 *
 * Security: disables TLS verification for the ephemeral self-signed cert only (NODE_TLS_REJECT_UNAUTHORIZED).
 * Never point this at arbitrary hosts — localhost only.
 */
'use strict'

const fs = require('fs')
const path = require('path')
const os = require('os')
const https = require('https')
const http = require('http')
const { execFileSync } = require('child_process')

process.env.NODE_TLS_REJECT_UNAUTHORIZED = '0'

const { GenericProvider } = require('electron-updater/out/providers/GenericProvider')
const { HttpExecutor } = require('builder-util-runtime')

class MiniExecutor extends HttpExecutor {
  createRequest(options, callback) {
    const mod = options.protocol === 'http:' ? http : https
    return mod.request(options, callback)
  }
}

async function main() {
  try {
    execFileSync('openssl', ['version'], { stdio: 'pipe' })
  } catch {
    console.error('ci_generic_https_feed_proof: openssl is required')
    process.exit(1)
  }

  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'pyc-hermes-feed-'))
  const keyPath = path.join(tmp, 'key.pem')
  const certPath = path.join(tmp, 'cert.pem')
  execFileSync(
    'openssl',
    [
      'req',
      '-x509',
      '-newkey',
      'rsa:2048',
      '-keyout',
      keyPath,
      '-out',
      certPath,
      '-days',
      '1',
      '-nodes',
      '-subj',
      '/CN=127.0.0.1',
    ],
    { stdio: 'pipe' },
  )

  const proofVersion = `99.0.0-ci-proof+${Date.now()}`
  const yml =
    `version: "${proofVersion}"\n` +
    'files:\n' +
    '  - url: stub.AppImage\n' +
    '    sha512: dGVzdA==\n'

  const server = https.createServer(
    { key: fs.readFileSync(keyPath), cert: fs.readFileSync(certPath) },
    (req, res) => {
      const pathname = (req.url || '').split('?')[0]
      if (pathname.endsWith('/latest-linux.yml')) {
        res.writeHead(200, { 'Content-Type': 'text/yaml' })
        res.end(yml)
        return
      }
      res.writeHead(404)
      res.end()
    },
  )

  await new Promise((resolve, reject) => {
    server.once('error', reject)
    server.listen(0, '127.0.0.1', resolve)
  })

  try {
    const { port } = server.address()
    const baseUrl = `https://127.0.0.1:${port}/release/`
    const mockUpdater = { channel: undefined, isAddNoCacheQuery: false }
    const provider = new GenericProvider({ url: baseUrl }, mockUpdater, {
      platform: 'linux',
      executor: new MiniExecutor(),
    })
    const info = await provider.getLatestVersion()
    if (info.version !== proofVersion) {
      console.error(`expected version ${proofVersion}, got ${info.version}`)
      process.exit(1)
    }
    const resolved = provider.resolveFiles(info)
    if (!Array.isArray(resolved) || resolved.length < 1) {
      console.error('resolveFiles returned unexpected shape', resolved)
      process.exit(1)
    }
    console.log('ci_generic_https_feed_proof: OK', proofVersion)
  } finally {
    server.close()
  }
}

main().catch((err) => {
  console.error(err)
  process.exit(1)
})
