import test from 'node:test';
import assert from 'node:assert/strict';
import { NulangWebClient, ApiError } from './client.mjs';

const contract = { openapi:'3.1.0', paths: {
  '/v1/items/{item}': { get: { operationId:'read_item', parameters:[
    {name:'item', in:'path', required:true}, {name:'tag', in:'query'}, {name:'x-tenant-id', in:'header', required:true}
  ]}},
  '/v1/jobs': {post: {operationId:'create_job', requestBody: {required:true, content:{'application/x-www-form-urlencoded':{}}}}}
}};

test('encodes paths/query; forwards auth, headers, W3C trace context', async () => {
  let target, options;
  const fetchImpl = async (url, init) => { target=url; options=init; return new Response('ok', {status:200}); };
  const traceparent='00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01';
  const client=new NulangWebClient({baseUrl:'https://example.com/api', contract, token:'secret', fetchImpl});
  await client.call('read_item', {path:{item:'a/b'}, query:{tag:['A B', 'é']}, headers:{'x-tenant-id':'acme'}, traceparent});
  assert.equal(target, 'https://example.com/api/v1/items/a%2Fb?tag=A+B&tag=%C3%A9');
  assert.equal(options.headers.Authorization,'Bearer secret');
  assert.equal(options.headers['x-tenant-id'],'acme');
  assert.equal(options.headers.traceparent,traceparent);
  assert.equal(options.method,'GET');
});

test('form POST uses declared content type and encoding', async () => {
  const fetchImpl=async (_,init)=>{assert.equal(init.method,'POST');assert.equal(init.headers['Content-Type'],'application/x-www-form-urlencoded'); assert.equal(init.body,'name=ma%C3%B1ana');return new Response('',{status:201});};
  const r=await new NulangWebClient({baseUrl:'https://example.com',contract,fetchImpl}).call('create_job',{body:{name:'mañana'}});
  assert.equal(r.status,201);
});

test('does not swallow HTTP failures', async () => {
  const fetchImpl=async()=>new Response('bad',{status:503});
  await assert.rejects(()=>new NulangWebClient({baseUrl:'https://example.com',contract,fetchImpl}).call('read_item',{path:{item:'missing'}, headers:{'x-tenant-id':'acme'}}),e=>e instanceof ApiError && e.status===503);
});

test('rejects undeclared data, invalid operations and invalid contract', async () => {
  const client=new NulangWebClient({baseUrl:'https://example.com',contract,fetchImpl:async()=>{throw Error('must not fetch')}});
  await assert.rejects(()=>client.call('read_item',{path:{item:'x'}}),/x-tenant-id/);
  await assert.rejects(()=>client.call('read_item',{path:{item:'x'},headers:{'x-tenant-id':'a'},query:{secret:'x'}}),/secret/);
  await assert.rejects(()=>client.call('read_item',{path:{item:'..'},headers:{'x-tenant-id':'a'}}),/path/);
  await assert.rejects(()=>client.call('missing'),/Unknown/);
  assert.throws(()=>new NulangWebClient({baseUrl:'https://example.com',contract:{openapi:'3.1.0',paths:{'//evil/x':{get:{operationId:'unsafe'}}}}}),/path/);
});

test('form arrays serialize as repeated fields and bearer token cannot conflict', async () => {
  let request;
  const fetchImpl=async (_,init)=>{request=init;return new Response('',{status:201});};
  const client=new NulangWebClient({baseUrl:'https://example.com',contract,fetchImpl,token:'secret'});
  await client.call('create_job',{body:{tag:['a','b']}});
  assert.equal(request.body,'tag=a&tag=b');
  await assert.rejects(()=>client.call('read_item',{path:{item:'x'},headers:{'x-tenant-id':'acme',Authorization:'override'}}),/Authorization/);
});
