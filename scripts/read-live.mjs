// Read only: never creates accounts, signatures, deployments or writes.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import {createClient,abi} from 'genlayer-js';
import {studionet} from 'genlayer-js/chains';
import {TransactionHashVariant} from 'genlayer-js/types';
const root=path.resolve(import.meta.dirname,'..');
const evidence=JSON.parse(fs.readFileSync(path.join(root,'evidence/studionet.json')));
const client=createClient({chain:studionet});
assert.equal(Number(await client.getChainId()),61999);
const source=fs.readFileSync(path.join(root,'contracts/purpose_bind.py'),'utf8');
assert.equal(await client.getContractCode(evidence.address),source);
assert.equal(crypto.createHash('sha256').update(source).digest('hex'),evidence.sourceSha256);
const record=JSON.parse(await client.readContract({address:evidence.address,functionName:'get_record',args:[evidence.owner,'library-demo'],transactionHashVariant:TransactionHashVariant.LATEST_FINAL}));
assert.deepEqual(record,evidence.record);
assert.equal(record.status,'CLAIMED');
assert.deepEqual(record.selected,['city_weekly_totals']);
for(const [name,step] of Object.entries(evidence.steps)){
 const r=await client.getTransaction({hash:step.hash});
 assert.equal(r.statusName,'FINALIZED');
 assert.equal(r.resultName||r.result_name,'MAJORITY_AGREE');
 const leader=r.consensus_data?.leader_receipt?.find(x=>x.mode==='leader');
 const execution=r.txExecutionResultName||leader?.execution_result;
 assert.equal(execution,name==='reject_excess'?'ERROR':'SUCCESS');
 assert.equal(r.from_address.toLowerCase(),(name==='claim'||name==='reject_excess'?evidence.recipient:evidence.owner).toLowerCase());
 assert.equal(r.to_address.toLowerCase(),evidence.address.toLowerCase());
 assert.equal(r.leader_only,false);
 if(name==='deploy') assert.equal(Buffer.from(r.data.contract_code,'base64').toString(),source);
 else {
  const decoded=abi.calldata.decode(Buffer.from(r.data.calldata.base64,'base64'));
  const methods={register:'register',assess:'assess',reject_excess:'claim',claim:'claim'};
  const args={register:['library-demo',evidence.recipient,fs.readFileSync(path.join(root,'examples/library.json'),'utf8')],
    assess:[evidence.owner,'library-demo'],
    reject_excess:[evidence.owner,'library-demo',record.grant_digest,JSON.stringify(['city_weekly_totals','visitor_emails'])],
    claim:[evidence.owner,'library-demo',record.grant_digest,JSON.stringify(['city_weekly_totals'])]};
  assert.equal(decoded.get('method'),methods[name]);
  assert.deepEqual(decoded.get('args'),args[name]);
  if(name==='reject_excess') assert.ok(JSON.stringify(leader.result).includes('NOT_MINIMUM_COVER'));
 }
 console.log(name,step.hash,r.statusName,execution);
}
console.log('Source, full-consensus receipts, signer/target and finalized state: VERIFIED');
