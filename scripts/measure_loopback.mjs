/** Calibrate UDP socket lifecycle against a deterministic IPv4 loopback DNS fixture. */
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import dgram from 'node:dgram';
import { once } from 'node:events';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { performance } from 'node:perf_hooks';
import { fileURLToPath } from 'node:url';
import { makeQuery, parseResponse, seededRng, shuffle } from './dns_client.mjs';

const address = '127.0.0.1';
const name = 'latency.example';
const repetitions = 400;
const warmups = 20;
const seed = 20261122;
const output = process.argv[2];
if (!output || process.argv.length !== 3) {
  throw new Error('Usage: node scripts/measure_loopback.mjs OUTPUT_DIRECTORY');
}
fs.mkdirSync(output);
const raw = path.join(output, 'loopback_raw.jsonl');
const metadata = {
  address, name, answer: '192.0.2.42', repetitions, warmups, seed,
  started_utc: new Date().toISOString(), node: process.version,
  os: os.release(), architecture: os.arch(),
  script_sha256: createHash('sha256').update(fs.readFileSync(fileURLToPath(import.meta.url))).digest('hex'),
  client_sha256: createHash('sha256').update(fs.readFileSync(new URL('./dns_client.mjs', import.meta.url))).digest('hex'),
};
const responseHeader = Buffer.from('000081800001000100000000', 'hex');
const answer = Buffer.from('c00c000100010000003c0004c000022a', 'hex');
const clientQuery = makeQuery(name, 0);
const responder = dgram.createSocket('udp4');
responder.on('message', (query, peer) => {
  if (!query.subarray(2).equals(clientQuery.subarray(2))) return;
  const reply = Buffer.concat([query.subarray(0, 2), responseHeader.subarray(2), query.subarray(12), answer]);
  responder.send(reply, peer.port, peer.address);
});

async function bind(socket, bindAddress) {
  const ready = once(socket, 'listening');
  socket.bind(0, bindAddress);
  await ready;
}

function exchange(socket, query, serverPort) {
  return new Promise((resolve, reject) => {
    const finish = (error, value) => {
      clearTimeout(timeout);
      socket.off('message', receive);
      socket.off('error', finish);
      if (error) reject(error);
      else resolve(value);
    };
    const receive = (reply, peer) => {
      if (peer.address !== address || peer.port !== serverPort) return;
      try {
        assert.deepEqual(parseResponse(reply, query).addresses, [metadata.answer]);
        finish(null, reply);
      } catch (error) {
        finish(error);
      }
    };
    const timeout = setTimeout(() => finish(new Error('Loopback DNS timeout')), 1500);
    socket.on('message', receive);
    socket.once('error', finish);
    socket.send(query, serverPort, address, error => {
      if (error) finish(error);
    });
  });
}

const reusable = dgram.createSocket('udp4');
let failed = 0;
try {
  await bind(responder, address);
  await bind(reusable, '0.0.0.0');
  const serverPort = responder.address().port;
  const rng = seededRng(seed);
  for (let rep = 0; rep < warmups + repetitions; rep++) {
    const treatments = shuffle(['fresh', 'prebound'], rng);
    for (const [order, treatment] of treatments.entries()) {
      const query = makeQuery(name, 2 * rep + order);
      const record = { rep, order: order + 1, phase: rep < warmups ? 'warmup' : 'measure',
        treatment, query_base64: query.toString('base64') };
      const start = performance.now();
      let socket;
      let closed = false;
      try {
        socket = treatment === 'fresh' ? dgram.createSocket('udp4') : reusable;
        if (treatment === 'fresh') await bind(socket, '0.0.0.0');
        const ready = performance.now();
        const reply = await exchange(socket, query, serverPort);
        const validated = performance.now();
        record.port = socket.address().port;
        if (treatment === 'fresh') {
          socket.close();
          closed = true;
        }
        record.whole_ms = performance.now() - start;
        record.ready_ms = ready - start;
        record.query_ms = validated - ready;
        record.valid = true;
        record.response_base64 = reply.toString('base64');
      } catch (error) {
        record.valid = false;
        record.error = error.message;
        failed++;
      } finally {
        if (treatment === 'fresh' && socket && !closed) {
          try { socket.close(); } catch {}
        }
        fs.appendFileSync(raw, JSON.stringify(record) + '\n');
      }
    }
  }
  metadata.status = 'complete';
} finally {
  for (const socket of [reusable, responder]) {
    try { socket.close(); } catch {}
  }
  metadata.finished_utc = new Date().toISOString();
  metadata.failed = failed;
  fs.writeFileSync(path.join(output, 'loopback_environment.json'), JSON.stringify(metadata, null, 2) + '\n');
}
