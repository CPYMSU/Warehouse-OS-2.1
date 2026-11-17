"""Synthetic streaming-only gateway tests, no real runtime/network."""
import asyncio
import httpx
import pytest
from fastapi import HTTPException
from fastapi.exception_handlers import http_exception_handler
from starlette.requests import Request
from app.api import hosted_runtime_gateway as g

class Stream(httpx.AsyncByteStream):
    def __init__(self): self.closed=False
    async def __aiter__(self):
        yield b'abc';yield b'def'
    async def aclose(self):self.closed=True

def request(method,path,body=b'',headers=(),private=True):
    async def receive():return {'type':'http.request','body':body,'more_body':False}
    state={'pages_hostname_route':{'tenant_slug':'acme','workspace_key':'mk7-workspace'}} if private else {}
    return Request({'type':'http','method':method,'scheme':'https','server':('mk7-workspace.bonfirework.org',443),'path':'/'+path,'query_string':b'',
                    'state':state,'headers':[(b'host',b'mk7-workspace.bonfirework.org'),*headers]},receive)

def proxy(req,path):return g._proxy_response({'internal_url':'http://runtime:8080','deployment_id':'fixture'},path,req,'acme','mk7-workspace')

def install(monkeypatch,handler):
    client=httpx.AsyncClient
    monkeypatch.setattr(g.httpx,'AsyncClient',lambda **kwargs:client(transport=httpx.MockTransport(handler),**kwargs))


def test_range_download_streams_and_closes(monkeypatch):
    stream=Stream();seen=[]
    async def handler(req):
        seen.append(req);return httpx.Response(206,headers={'Content-Length':'6','Content-Range':'bytes 0-5/10','Content-Type':'application/pdf','X-Evil':'drop'},stream=stream)
    install(monkeypatch,handler);path='api/v1/uhv/documents/'+'a'*64+'/file';req=request('GET',path,headers=[(b'range',b'bytes=0-5')])
    async def run():
        response=await proxy(req,path)
        assert not stream.closed and response.status_code==206 and response.headers['content-range']=='bytes 0-5/10'
        assert response.headers['content-length']=='6' and 'x-evil' not in response.headers
        assert b''.join([part async for part in response.body_iterator])==b'abcdef'
    asyncio.run(run());assert stream.closed and seen[0].headers['range']=='bytes=0-5' and seen[0].headers['host']=='mk7-workspace.bonfirework.org'


def test_head_and_upload_length_and_stream_close(monkeypatch):
    streams=[];received=[]
    async def handler(req):
        if req.method=='PUT':received.append(await req.aread())
        stream=Stream();streams.append(stream);return httpx.Response(200,headers={'Content-Length':'6'},stream=stream)
    install(monkeypatch,handler);download='api/v1/uhv/documents/'+'a'*64+'/file';upload='api/v1/uhv-intake/sessions/00000000-0000-4000-8000-000000000001/parts/0'
    async def run():
        head=await proxy(request('HEAD',download),download);assert head.body==b'' and head.headers['content-length']=='6' and streams[-1].closed
        response=await proxy(request('PUT',upload,b'xyz',[(b'content-length',b'3')]),upload)
        assert b''.join([x async for x in response.body_iterator])==b'abcdef' and streams[-1].closed
    asyncio.run(run());assert received==[b'xyz']


def test_untrusted_host_and_large_request_are_denied_before_read(monkeypatch):
    monkeypatch.setattr(g, 'resolve_pages_site_key', lambda _key: {'tenant_slug':'acme','workspace_key':'mk7-workspace'})
    path='api/v1/uhv-publish/prepare'
    async def run():
        with pytest.raises(HTTPException) as e:await proxy(request('POST',path,b'',private=False),path)
        assert e.value.status_code==403
        with pytest.raises(HTTPException) as e:await proxy(request('POST',path,b'',[(b'content-length',b'5000')]),path)
        assert e.value.status_code==413
    asyncio.run(run())


@pytest.mark.parametrize('method,path', [
    ('POST', 'api/v1/uhv-publish/prepare'),
    ('PUT', 'api/v1/uhv-intake/sessions/00000000-0000-4000-8000-000000000001/parts/0'),
])
def test_conflicting_raw_body_framing_is_rejected_before_read(method, path, monkeypatch):
    async def receive():
        raise AssertionError('ambiguous request body was consumed')
    req = request(method, path, headers=[(b'content-length', b'3'), (b'transfer-encoding', b'chunked')])
    req._receive = receive
    async def run():
        with pytest.raises(HTTPException) as exc:
            await proxy(req, path)
        assert exc.value.status_code == 400
        assert exc.value.detail == 'ambiguous_request_framing'
    asyncio.run(run())


def test_cancelled_download_closes_upstream(monkeypatch):
    stream=Stream()
    async def handler(req):return httpx.Response(200,stream=stream)
    install(monkeypatch,handler);path='api/v1/uhv/documents/'+'b'*64+'/file'
    async def run():
        response=await proxy(request('GET',path),path)
        iterator=response.body_iterator
        assert await anext(iterator)==b'abc'
        await iterator.aclose()
    asyncio.run(run());assert stream.closed


def test_upstream_auth_denial_preserved_and_never_replayed(monkeypatch):
    seen=[]
    async def handler(req):
        seen.append(req)
        return httpx.Response(401,headers={'Content-Type':'application/json','WWW-Authenticate':'Bearer'},stream=Stream())
    install(monkeypatch,handler);path='api/v1/uhv/documents/'+'c'*64+'/file'
    async def run():
        response=await proxy(request('GET',path),path)
        assert response.status_code==401 and response.headers['cache-control'].startswith('private, no-store')
        assert b''.join([x async for x in response.body_iterator])==b'abcdef'
    asyncio.run(run());assert len(seen)==1


def test_failed_upstream_does_not_retry_or_leak(monkeypatch):
    calls=[]
    async def handler(req):
        calls.append(req);raise httpx.ConnectError('synthetic failure',request=req)
    install(monkeypatch,handler);path='api/v1/uhv/documents/'+'d'*64+'/file'
    async def run():
        with pytest.raises(HTTPException) as exc:await proxy(request('GET',path),path)
        assert exc.value.status_code==502 and 'synthetic failure' not in str(exc.value.detail)
    asyncio.run(run());assert len(calls)==1


@pytest.mark.parametrize('method',['GET','HEAD','DELETE','PATCH'])
def test_no_body_methods_never_buffer_private_payload(method):
    path='api/v1/uhv/documents'
    async def run():
        for headers in ([(b'content-length',b'10000000')], [], [(b'transfer-encoding',b'chunked')]):
            with pytest.raises(HTTPException) as exc:
                await proxy(request(method,path,b'a'*5000,headers),path)
            assert exc.value.status_code==413
    asyncio.run(run())


def test_asgi_disconnect_before_first_body_closes_stream(monkeypatch):
    stream=Stream()
    async def handler(req):return httpx.Response(200,stream=stream)
    install(monkeypatch,handler);path='api/v1/uhv/documents/'+'f'*64+'/file'
    async def run():
        req=request('GET',path);req.scope['asgi']={'spec_version':'2.4'}
        response=await proxy(req,path)
        async def send(_message):raise asyncio.CancelledError()
        with pytest.raises(asyncio.CancelledError):await response(req.scope,req.receive,send)
        assert stream.closed
    asyncio.run(run())


def test_other_workspace_same_path_is_not_blocked(monkeypatch):
    class Client:
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def request(self,method,url,**kwargs):return httpx.Response(200,content=b'ok',request=httpx.Request(method,url))
    monkeypatch.setattr(g.httpx,'AsyncClient',lambda **kwargs:Client())
    path='api/v1/uhv/documents'
    req=request('GET',path,private=False)
    response=asyncio.run(g._proxy_response({'internal_url':'http://runtime','deployment_id':'fixture'},path,req,'different-tenant','another-workspace'))
    assert response.status_code==200 and response.body==b'ok'


def test_same_workspace_name_with_missing_binding_fails_closed(monkeypatch):
    monkeypatch.setattr(g, 'resolve_pages_site_key', lambda _key: None)
    path='api/v1/uhv/documents'
    async def run():
        with pytest.raises(HTTPException) as exc:await proxy(request('GET',path,private=False),path)
        assert exc.value.status_code==503
    asyncio.run(run())


@pytest.mark.parametrize('case,expected', [
    ('ambiguous_framing', 400), ('shared_origin', 403),
    ('missing_length', 411), ('too_large', 413), ('huge_length', 413),
    ('stream_failed', 502), ('binding_missing', 503),
])
def test_gateway_generated_private_errors_are_not_cached(monkeypatch, case, expected):
    path = 'api/v1/uhv-publish/prepare'
    headers = []
    method = 'POST'
    private = True
    if case == 'ambiguous_framing':
        headers = [(b'content-length', b'3'), (b'transfer-encoding', b'chunked')]
    elif case == 'shared_origin':
        private = False
        monkeypatch.setattr(g, 'resolve_pages_site_key', lambda _key: {'tenant_slug':'acme','workspace_key':'mk7-workspace'})
    elif case == 'too_large':
        headers = [(b'content-length', b'4097')]
    elif case == 'huge_length':
        headers = [(b'content-length', b'9' * 5000)]
    elif case == 'stream_failed':
        path = 'api/v1/uhv/documents/' + 'd' * 64 + '/file'
        method = 'GET'
        async def handler(req):
            raise httpx.ConnectError('synthetic failure', request=req)
        install(monkeypatch, handler)
    elif case == 'binding_missing':
        private = False
        monkeypatch.setattr(g, 'resolve_pages_site_key', lambda _key: None)
    req = request(method, path, headers=headers, private=private)
    async def run():
        with pytest.raises(HTTPException) as exc:
            await proxy(req, path)
        assert exc.value.status_code == expected
        response = await http_exception_handler(req, exc.value)
        assert 'no-store' in response.headers['cache-control']
        assert response.headers['x-content-type-options'] == 'nosniff'
    asyncio.run(run())


@pytest.mark.parametrize('private', [True, False])
def test_no_upstream_cache_policy_is_scoped_to_private_workspace(private):
    path = 'api/v1/uhv/documents'
    req = request('GET', path, private=private)
    workspace = 'mk7-workspace' if private else 'another-workspace'
    async def run():
        with pytest.raises(HTTPException) as exc:
            await g._proxy_response({'internal_urls': [], 'deployment_id': 'fixture'}, path, req, 'acme', workspace)
        assert exc.value.status_code == 502
        if private:
            assert 'no-store' in exc.value.headers['Cache-Control']
        else:
            assert exc.value.headers is None
    asyncio.run(run())


def test_nonstream_upstream_failure_is_not_cached(monkeypatch):
    async def handler(req):
        raise httpx.ConnectError('synthetic failure', request=req)
    install(monkeypatch, handler)
    path = 'api/v1/uhv/documents'
    req = request('GET', path)
    async def run():
        with pytest.raises(HTTPException) as exc:
            await proxy(req, path)
        assert exc.value.status_code == 502
        response = await http_exception_handler(req, exc.value)
        assert 'no-store' in response.headers['cache-control']
    asyncio.run(run())
