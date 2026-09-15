#!/usr/bin/env python3
"""Recover the exact approved rescue-media release using an isolated checkout."""
from __future__ import annotations
import argparse
import concurrent.futures
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import signal
import subprocess
import sys
import time
import urllib.request

SOURCE = 'f9ad48fc918666b7bb88de481a5ae29a77a203fe'
REF = 'chatgpt/mk7-rescue-media-repair-release'
UNIT = 'transmission-rope-rescue/units/high-angle-rescue-practice'
KEYS = Path('/Users/peiyuan/Server/bonfirework/secrets/digital-asset-workspace-keys.json')
SSH_KEY = KEYS.with_name('registry-readonly-ed25519-v2')
ROOT = Path(os.environ['RUNNER_TEMP']) / ('rescue-recovery-' + os.environ['GITHUB_RUN_ID'])
SOURCE_DIR = ROOT / 'registry'
EVIDENCE = ROOT / 'evidence'
BASES = ('https://mk7-workspace.bonfirework.org/', 'https://bonfirework.org/assets/bonfire/mk7-workspace/')


def git(args: list[str], *, timeout: int = 180, capture: bool = True) -> str:
    env = {**os.environ, 'GIT_TERMINAL_PROMPT':'0', 'GIT_CONFIG_COUNT':'0'}
    ssh = ['/usr/bin/ssh','-i',str(SSH_KEY),'-o','Hostname=ssh.github.com','-p','443',
           '-o','BatchMode=yes','-o','IdentitiesOnly=yes','-o','ConnectTimeout=15',
           '-o','ServerAliveInterval=15','-o','ServerAliveCountMax=3',
           '-o','StrictHostKeyChecking=accept-new',
           '-o','ProxyCommand=/usr/bin/nc -X connect -x 127.0.0.1:7897 %h %p']
    env['GIT_SSH_COMMAND'] = shlex.join(ssh)
    process = subprocess.Popen(['git','-C',str(SOURCE_DIR),*args], env=env, text=True,
        stdout=subprocess.PIPE if capture else None, stderr=None, start_new_session=True)
    try:
        stdout, _ = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGTERM)
        try: process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL); process.communicate()
        raise RuntimeError('Isolated source checkout timed out; no production changes made')
    if process.returncode:
        raise RuntimeError('Git source operation failed: ' + args[0])
    return stdout or ''


def prepare() -> None:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    SOURCE_DIR.mkdir(parents=True, exist_ok=False)
    if not SSH_KEY.is_file() or SSH_KEY.stat().st_mode & 0o777 != 0o600:
        raise RuntimeError('Existing authorized read-only repository key is unavailable')
    git(['init'],timeout=30)
    git(['remote','add','origin','git@github.com:CPYMSU/registry.git'],timeout=30)
    git(['config','remote.origin.promisor','true'],timeout=30)
    git(['config','remote.origin.partialclonefilter','blob:none'],timeout=30)
    git(['sparse-checkout','init','--cone'],timeout=30)
    git(['sparse-checkout','set','assets/mk7'],timeout=30)
    git(['fetch','--filter=blob:none','--depth=1','--no-tags','--no-recurse-submodules',
         'origin',f'refs/heads/{REF}'],timeout=240,capture=False)
    if git(['rev-parse','FETCH_HEAD'],timeout=30).strip() != SOURCE:
        raise RuntimeError('Frozen source branch changed; release stopped')
    git(['checkout','--detach',SOURCE],timeout=240,capture=False)
    git(['diff','--exit-code','HEAD','--','assets/mk7'],timeout=30)
    subprocess.run([sys.executable,str(SOURCE_DIR/'assets/mk7/tools/restore_rescue_media.py'),
        '--report',str(EVIDENCE/'source-media-check.json')],check=True,timeout=120)
    (EVIDENCE/'media-bundle.json').write_bytes((SOURCE_DIR/'assets/mk7/RESCUE_MEDIA_BUNDLE.json').read_bytes())
    print('ISOLATED_RESCUE_SOURCE_READY='+SOURCE,flush=True)


def publish() -> None:
    root=Path.cwd()/'ops/macos'
    subprocess.run([sys.executable,str(root/'normalize-digital-asset-archive.py'),
                    str(root/'publish-digital-assets.py')],check=True,timeout=30)
    path=root/'publish-content-only-mk7.py'
    text=path.read_text()
    text,n=re.subn(r'^COURSE_MARKERS\s*=.*$',
        'COURSE_MARKERS = ("高空应急救援与团队综合实操", "?v=cc8aea230d583f40", "lesson-data.json?v=6801ce1d773e5097")',
        text,count=1,flags=re.M)
    if n!=1 or text.count('500kv-spacer-habitual-violations')!=2:
        raise RuntimeError('Reviewed content publisher has changed')
    text=text.replace('500kv-spacer-habitual-violations',UNIT)
    text,n=re.subn(r'(runtime_type="auto",\n\s*)component="",',r'\1component="api",',text,count=1)
    if n!=1:raise RuntimeError('Existing managed API component call changed')
    path.write_text(text)
    spec=importlib.util.spec_from_file_location('rescued_content_publisher',path)
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    def validated_checkout(**kwargs):
        if kwargs['repository']!='CPYMSU/registry' or kwargs['ref']!=REF:
            raise RuntimeError('Unexpected release target')
        if git(['rev-parse','HEAD'],timeout=30).strip()!=SOURCE:raise RuntimeError('Unexpected source revision')
        git(['diff','--exit-code','HEAD','--','assets/mk7'],timeout=30)
        return SOURCE_DIR,SOURCE
    module.checkout_source=validated_checkout
    args=argparse.Namespace(repository='CPYMSU/registry',ref=REF,source_path='assets/mk7',
        workspace_alias='mk7',workspace_keys=KEYS,registry_ssh_key=SSH_KEY,
        cache_root=ROOT/'publisher-cache',base_url='https://bonfirework.org',timeout_seconds=1500)
    result=module.publish(args)
    if result['commit']!=SOURCE or result['release_state']!='verified':
        raise RuntimeError('Release did not reach verified state')
    (EVIDENCE/'release.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))


def verify() -> None:
    bundle=json.loads((EVIDENCE/'media-bundle.json').read_text())
    def request(task):
        base,item=task
        url=base+item['path'].removeprefix('site/')+'?v='+item['sha256'][:16]
        result={'url':url,'expected_sha256':item['sha256']}
        for attempt in range(3):
            try:
                req=urllib.request.Request(url,headers={'User-Agent':'MK7-Rescue-Image-Verification/1.1',
                    'Accept':'image/avif,image/webp,image/svg+xml,image/*,*/*;q=0.8',
                    'Sec-Fetch-Dest':'image','Sec-Fetch-Mode':'no-cors','Sec-Fetch-Site':'same-origin',
                    'Cache-Control':'no-cache','Referer':base})
                with urllib.request.urlopen(req,timeout=30) as r:
                    b=r.read(item['size_bytes']+1)
                    result.update(status=r.status,bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),
                                  content_type=r.headers.get('Content-Type',''))
                result['ok']=(result['status']==200 and result['bytes']==item['size_bytes']
                    and result['sha256']==item['sha256'] and result['content_type'].startswith('image/'))
                if result['ok']:return result
            except Exception as e:result['error']=type(e).__name__+': '+str(e)[:180]
            time.sleep(2*(attempt+1))
        result['ok']=False
        return result
    tasks=[(b,a) for b in BASES for a in bundle['assets']]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(request,tasks))
    report={'ok':all(r['ok'] for r in results),'original_images':len(bundle['assets']),
            'url_checks':len(results),'passed':sum(r['ok'] for r in results),'results':results}
    (EVIDENCE/'public-media-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print('PUBLIC_MEDIA_CHECK',json.dumps({k:v for k,v in report.items() if k!='results'}),flush=True)
    if not report['ok']:
        for r in results:
            if not r['ok']:print(json.dumps(r))
        raise RuntimeError('Public original image verification failed')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('operation',choices=['prepare','publish','verify'])
    args=parser.parse_args()
    {'prepare':prepare,'publish':publish,'verify':verify}[args.operation]()
