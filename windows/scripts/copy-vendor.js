#!/usr/bin/env node
/**
 * Copies the vendored runtime libraries (hls.js) into the renderer folder so
 * the packaged app does not depend on node_modules at runtime.
 */
'use strict';

const fs = require('fs');
const path = require('path');

const root = path.join(__dirname, '..');
const copies = [
  ['node_modules/hls.js/dist/hls.min.js', 'renderer/hls.min.js'],
];

let failed = false;
for (const [from, to] of copies) {
  const src = path.join(root, from);
  const dst = path.join(root, to);
  try {
    fs.mkdirSync(path.dirname(dst), { recursive: true });
    fs.copyFileSync(src, dst);
    console.log(`copied ${from} -> ${to} (${fs.statSync(dst).size} bytes)`);
  } catch (err) {
    console.error(`could not copy ${from}: ${err.message}`);
    failed = true;
  }
}
process.exit(failed ? 1 : 0);
