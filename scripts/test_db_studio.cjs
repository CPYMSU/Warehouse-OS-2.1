'use strict';
const assert = require('node:assert/strict');
const { test } = require('node:test');
const M = require('../frontend/v2/db-studio.js');
test('unwraps authorized API projections without inventing records', () => {
  assert.deepEqual(M.normalize({tasks:[{id:1}]}).rows, [{id:1}]);
  assert.deepEqual(M.normalize({profile:{name:'A'}}).fields, ['name']);
  assert.deepEqual(M.normalize([]), {rows:[],fields:[]});
  assert.throws(() => M.normalize({available:false,tasks:[{id:1}]}));
});
test('preserves false, zero, null and primitive array entries', () => {
  assert.deepEqual(M.normalize([0,false,null]).rows, [{value:0},{value:false},{value:null}]);
  assert.equal(M.text(0),'0'); assert.equal(M.text(false),'false'); assert.equal(M.text(null),'null');
  assert.throws(() => M.normalize('not rows'));
});
test('limits bytes, rows, fields and nesting before rendering', () => {
  assert.throws(() => M.parse('"' + 'x'.repeat(M.MAX_BYTES) + '"'));
  assert.throws(() => M.normalize(Array(5001).fill({id:1})));
  assert.throws(() => M.normalize(Object.fromEntries(Array.from({length:201},(_,i)=>['c'+i,i]))));
  assert.throws(() => M.parse('['.repeat(34)+'0'+']'.repeat(34)));
  assert.throws(() => M.parse('{invalid'));
});
test('detail is independent of spacing density', () => {
  const c=M.defaults(Array.from({length:12},(_,i)=>'f'+i));
  c.density=100; assert.equal(M.visible(c).length,8);
  c.detail=1; assert.equal(M.visible(c).length,3);
  c.detail=3; assert.equal(M.visible(c).length,12);
  c.columns[0].visible=false; assert.equal(M.visible(c).length,11);
});
test('style whitelist strips records, credentials and unknown fields', () => {
  const raw={version:1,view:'bad',density:999,detail:-4,token:'SECRET',rows:[{secret:'VALUE'}],columns:[
    {field:'name',label:'Title',visible:false,width:1,format:'script',value:'PRIVATE'},
    {field:'name',label:'duplicate'},{field:'unknown',width:500}]};
  const result=M.validate(raw,['id','name']);
  assert.equal(result.density,100); assert.equal(result.detail,1); assert.equal(result.view,'table');
  assert.equal(result.columns.length,2); assert.equal(result.columns[0].width,90);
  assert.equal(result.columns[0].format,'auto'); assert.equal(result.columns[1].field,'id');
  assert.ok(!JSON.stringify(result).includes('SECRET')); assert.ok(!JSON.stringify(result).includes('PRIVATE'));
  assert.throws(()=>M.validate({version:2,columns:[]},[]));
});
test('literal prototype-like keys remain data, never executable properties', () => {
  const row=M.parse('{"__proto__":{"polluted":true},"constructor":"literal","id":1}');
  const result=M.project(row,M.defaults(Object.keys(row)).columns);
  assert.equal(Object.getPrototypeOf(result),Object.prototype);
  assert.equal(result.__proto__.polluted,true); assert.equal({}.polluted,undefined);
});
test('view save round trip does not mutate config or rows', () => {
  const {rows,fields}=M.normalize([{id:1,n:'private'}]); const c=M.defaults(fields);
  const saved=M.validate(JSON.parse(JSON.stringify(c)),fields);
  saved.columns[0].label='new'; assert.equal(c.columns[0].label,'id'); assert.equal(rows[0].n,'private');
});
