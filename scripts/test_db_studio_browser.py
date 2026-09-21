"""Browser smoke test with synthetic local fixtures and mocked API only.
Requires playwright and a Chromium executable; never reads production records.
"""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
url = 'https://db-studio.test/db-studio.html'
checks=[]
def check(name, condition):
    assert condition, name
    checks.append(name)

try:
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'),headless=True,args=['--no-sandbox'])
        page=browser.new_page(viewport={'width':1440,'height':1100})
        errors=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        # Render local bytes without navigating or making any network request.
        html=(ROOT/'frontend/v2/db-studio.html').read_text().replace('<link rel="stylesheet" href="db-studio.css">','').replace('<script defer src="db-studio.js"></script>','')
        page.set_content(html)
        page.evaluate("""() => {
          const values=new Map();
          Object.defineProperty(window,'localStorage',{value:{getItem:k=>values.get(k)||null,setItem:(k,v)=>values.set(k,String(v))}});
        }""")
        page.add_style_tag(content=(ROOT/'frontend/v2/db-studio.css').read_text())
        page.add_script_tag(content=(ROOT/'frontend/v2/db-studio.js').read_text())
        records=[{'id':i+1,'title':f'SYNTHETIC fixture {i+1}','amount':0,'active':False,'note':None,'status':'review','extra':{'x':1},'owner':'tester','hidden':'PRIVATE_VALUE','html':'<img src=x onerror="window.pwned=true">'} for i in range(110)]
        page.locator('#paste').click()
        page.locator('#json-input').fill(json.dumps(records))
        page.locator('#apply-json').click()
        check('local table pagination',page.locator('#canvas tbody tr').count()==50)
        check('detail standard eight fields',page.locator('#canvas thead th').count()==9)
        fontsize=page.locator('#canvas tbody td').first.evaluate('(e)=>getComputedStyle(e).fontSize')
        page.locator('#density').fill('100');page.locator('#density').dispatch_event('input')
        check('density preserves font size',fontsize==page.locator('#canvas tbody td').first.evaluate('(e)=>getComputedStyle(e).fontSize'))
        page.select_option('#detail','1');check('summary three fields',page.locator('#canvas thead th').count()==4)
        page.select_option('#detail','3');check('full selected fields',page.locator('#canvas thead th').count()==11)
        check('XSS data never executes',page.evaluate('!window.pwned && !document.querySelector("#canvas img")'))
        page.get_by_role('button',name='下移 id',exact=True).click()
        check('column reorder',page.locator('#canvas th').nth(1).inner_text()=='title')
        page.get_by_role('checkbox',name='显示 owner',exact=True).uncheck()
        check('column visibility',page.locator('#canvas th').count()==10)
        page.locator('#next').click();check('next page',page.locator('#canvas tbody tr').first.inner_text().startswith('#51'))
        page.select_option('#view','cards');check('card renderer',page.locator('.record-card').count()==50)
        page.select_option('#view','json');check('JSON renderer',page.locator('#canvas details').count()>0)
        page.select_option('#view','schema');check('sample field structure',page.locator('#canvas tbody tr').count()==10)
        page.select_option('#view','table')
        page.locator('#preset-name').fill('Compact test');page.locator('#save').click()
        check('named view saved',page.locator('#presets option').count()==2)
        with page.expect_download() as info:page.locator('#export').click()
        exported=json.loads(Path(info.value.path()).read_text())
        check('style export excludes data and credentials','PRIVATE_VALUE' not in json.dumps(exported) and set(exported)=={'version','view','density','detail','columns'})
        # Actual production is not accessed. Verify authorization headers and response handling with mocks.
        page.evaluate("""() => {
          window.mockCalls=[];
          window.fetch=async (url,options) => {
            window.mockCalls.push({url,method:options.method,headers:options.headers});
            const body=url.endsWith('/auth/me')?{user:{id:'test-user',username:'tester'}}:{profile:{name:'CONFIDENTIAL_REMOTE',id:7}};
            return new Response(JSON.stringify(body),{status:200,headers:{'Content-Type':'application/json'}});
          };
        }""")
        page.evaluate("localStorage.setItem('warehouse_auth_token','test-token');localStorage.setItem('warehouse_current_tenant','tenant-a')")
        page.select_option('#source','profile');page.locator('#load').click()
        page.wait_for_function("document.getElementById('canvas').textContent.includes('CONFIDENTIAL_REMOTE')")
        check('mocked API uses same identity',page.evaluate("mockCalls.length===2 && mockCalls.every(c=>c.method==='GET' && c.headers.Authorization==='Bearer test-token' && c.headers['X-Tenant-Slug']==='tenant-a')"))
        # Rejected local import must retain remote-session guard.
        page.locator('#paste').click();page.locator('#json-input').fill('"invalid root"');page.locator('#apply-json').click()
        check('invalid JSON shape rejected',bool(page.locator('#paste-error').inner_text()))
        page.locator('[data-close="paste-dialog"]').click()
        page.locator('#canvas .record-button').first.click()
        page.wait_for_function("document.getElementById('record-content').textContent.includes('CONFIDENTIAL_REMOTE')")
        page.evaluate("localStorage.setItem('warehouse_current_tenant','tenant-b');window.dispatchEvent(new Event('focus'))")
        check('identity switch clears table and inspector',page.evaluate("!document.getElementById('record-dialog').open && !document.getElementById('record-content').textContent && !document.getElementById('canvas').textContent.includes('CONFIDENTIAL_REMOTE')"))
        page.evaluate("window.fetch=async ()=>new Response('{}',{status:403,headers:{'Content-Type':'application/json'}})")
        page.locator('#load').click();page.wait_for_function("document.getElementById('message').textContent.includes('没有读取')")
        check('403 yields explicit error without fake data',page.locator('#canvas tbody tr').count()==0)
        page.evaluate("window.fetch=async ()=>new Response('<h1>login</h1>',{status:200,headers:{'Content-Type':'text/html'}})")
        page.locator('#load').click();page.wait_for_function("document.getElementById('message').textContent.includes('没有收到 JSON')")
        check('HTML login response rejected',page.locator('#canvas tbody tr').count()==0)
        # Exercise small-screen layout with synthetic data only.
        page.select_option('#source','local');page.locator('#paste').click();page.locator('#json-input').fill(json.dumps(records[:8]));page.locator('#apply-json').click()
        page.set_viewport_size({'width':390,'height':844})
        check('mobile document does not horizontally overflow',page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
        page.set_viewport_size({'width':1440,'height':1100})
        page.locator('#message').evaluate("e=>e.textContent='测试画面 · 所有记录均为自动化测试虚构数据，非用户数据库'")
        preview=ROOT/'db-studio-preview.png';page.screenshot(path=str(preview),full_page=True)
        check('no browser runtime exceptions',not errors)
        browser.close()
finally:
    pass
report={'passed':len(checks),'checks':checks,'scope':'local synthetic fixtures and mocked API, not production integration'}
(ROOT/'browser-test-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
