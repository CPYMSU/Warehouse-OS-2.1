'use strict';

const fs = require('fs');
const path = require('path');
const ci = require('miniprogram-ci');

const ROOT = path.resolve(__dirname, '..');
const configPath = path.join(ROOT, 'project.config.json');
const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
const appid = String(process.env.WX_UPLOAD_APP_ID || config.appid || '').trim();
const privateKeyPath = path.resolve(String(process.env.WX_UPLOAD_PRIVATE_KEY || '').trim());
const version = String(process.env.WX_UPLOAD_VERSION || '').trim();
const desc = String(process.env.WX_UPLOAD_DESC || 'Unified member and booking app').trim();

if (!/^wx[a-zA-Z0-9]{16}$/.test(appid)) {
  throw new Error('WX_UPLOAD_APP_ID/project.config.json does not contain a formal AppID');
}
if (!process.env.WX_UPLOAD_PRIVATE_KEY || !fs.existsSync(privateKeyPath)) {
  throw new Error('WX_UPLOAD_PRIVATE_KEY must point to the WeChat upload private key');
}
if (!/^[0-9A-Za-z][0-9A-Za-z._-]{0,31}$/.test(version)) {
  throw new Error('WX_UPLOAD_VERSION must be a visible 1-32 character release version');
}

const project = new ci.Project({
  appid,
  type: 'miniProgram',
  projectPath: ROOT,
  privateKeyPath,
  ignores: [
    'node_modules/**/*',
    'tests/**/*',
    'scripts/**/*',
    'README.md',
    'package*.json',
  ],
});

ci.upload({
  project,
  version,
  desc: desc.slice(0, 32),
  setting: {
    es6: true,
    es7: true,
    minify: true,
    minifyJS: true,
    minifyWXML: true,
    minifyWXSS: true,
    autoPrefixWXSS: true,
    codeProtect: false,
  },
  onProgressUpdate: (progress) => {
    const message = progress && (progress.message || progress._msg);
    if (message) process.stdout.write(`[wechat-upload] ${message}\n`);
  },
}).then((result) => {
  process.stdout.write(`${JSON.stringify({
    ok: true,
    appid,
    version,
    result: result || null,
  })}\n`);
}).catch((error) => {
  process.stderr.write(`[wechat-upload] ${error && (error.stack || error.message) || error}\n`);
  process.exitCode = 1;
});
