// Opt-in zero-value Stable Studionet verification. Existing hashes are always resumed.
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import crypto from 'node:crypto';
import {createClient} from 'genlayer-js';
import {studionet} from 'genlayer-js/chains';
import {TransactionHashVariant} from 'genlayer-js/types';
import {privateKeyToAccount,generatePrivateKey} from 'viem/accounts';
const root=path.resolve(import.meta.dirname,'..');
const stateFile=process.env.PURPOSEBIND_STATE || path.join(os.homedir(),'.purposebind-studionet.json');
const encode=x=>JSON.stringify(x,(_,v)=>typeof v==='bigint'?v.toString():v,2);
let state;
if(fs.existsSync(stateFile)) state=JSON.parse(fs.readFileSync(stateFile));
else {
  if(process.env.PURPOSEBIND_NEW!=='1') throw Error('Set PURPOSEBIND_NEW=1 once to create an isolated zero-value test run.');
  state={keys:[generatePrivateKey(),generatePrivateKey()],steps:{}};
  fs.writeFileSync(stateFile,encode(state),{mode:0o600});
}
const save=()=>fs.writeFileSync(stateFile,encode(state),{mode:0o600});
const accounts=state.keys.map(privateKeyToAccount);
const clients=accounts.map(account=>createClient({chain:studionet,account}));
const [owner,recipient]=accounts.map(x=>x.address);
const client=clients[0];
if(Number(await client.getChainId())!==61999) throw Error('Wrong chain');
const code=fs.readFileSync(path.join(root,'contracts/purpose_bind.py'),'utf8');
const sha=crypto.createHash('sha256').update(code).digest('hex');
if(state.sourceSha && state.sourceSha!==sha) throw Error('Source changed; inspect existing deployment before continuing.');
state.sourceSha=sha; save();
async function step(name,send,expectSuccess=true){
  let entry=state.steps[name];
  if(!entry){
    entry=state.steps[name]={intent:true}; save();
    // An unknown send outcome is deliberately never retried automatically.
    entry.hash=await send();save();console.log(name,'submitted',entry.hash);
  }
  if(!entry.hash) throw Error('Unresolved send intent: '+name);
  if(!entry.receipt || entry.receipt.statusName!=='FINALIZED'){
    for(let i=0;i<180;i++){
      const receipt=await client.getTransaction({hash:entry.hash});
      entry.receipt=receipt;save();
      if(receipt.statusName==='FINALIZED') break;
      if(['CANCELED','UNDETERMINED'].includes(receipt.statusName)) throw Error(name+' '+receipt.statusName);
      await new Promise(r=>setTimeout(r,2000));
    }
  }
  const r=entry.receipt;
  r.resultName ??= r.result_name;
  r.txExecutionResultName ??= r.consensus_data?.leader_receipt?.find(x=>x.mode==='leader')?.execution_result;
  save();
  console.log(name,r.statusName,r.resultName,r.txExecutionResultName);
  if(r.statusName!=='FINALIZED') throw Error('Pending; resume existing hash');
  if(expectSuccess && (r.resultName!=='MAJORITY_AGREE'||r.txExecutionResultName!=='SUCCESS')) throw Error(name+' failed; inspect receipt, no retry');
  if(!expectSuccess && r.txExecutionResultName==='SUCCESS') throw Error(name+' unexpectedly succeeded');
  return r;
}
const deploy=await step('deploy',()=>client.deployContract({code,args:[],leaderOnly:false}));
state.address=deploy.to_address||deploy.recipient;save();
if(!state.address) throw Error('Missing deployed address');
const address=state.address;
const deployed=await client.getContractCode(address);
if(deployed!==code) throw Error('Source mismatch');
const call=(which,functionName,args)=>clients[which].writeContract({address,functionName,args,value:0n,leaderOnly:false});
const read=async()=>JSON.parse(await client.readContract({address,functionName:'get_record',args:[owner,'library-demo'],transactionHashVariant:TransactionHashVariant.LATEST_FINAL}));
const payload=fs.readFileSync(path.join(root,'examples/library.json'),'utf8');
await step('register',()=>call(0,'register',['library-demo',recipient,payload]));
await step('assess',()=>call(0,'assess',[owner,'library-demo']));
let record=await read();
if(record.status==='READY'){
  if(encode(record.options)!==encode([['city_weekly_totals']])) throw Error('Unexpected cover');
  await step('reject_excess',()=>call(1,'claim',[owner,'library-demo',record.grant_digest,JSON.stringify(['city_weekly_totals','visitor_emails'])]),false);
  if((await read()).status!=='READY') throw Error('Rejected call changed state');
}
record=await read();
if(record.status==='READY') await step('claim',()=>call(1,'claim',[owner,'library-demo',record.grant_digest,JSON.stringify(['city_weekly_totals'])]));
record=await read();
if(record.status!=='CLAIMED'||record.selected.join(',')!=='city_weekly_totals') throw Error('Final state mismatch');
function project(r){
 return {hash:r.hash,status:r.status,statusName:r.statusName,result:r.result,resultName:r.resultName||r.result_name,
  txExecutionResultName:r.txExecutionResultName,from_address:r.from_address,to_address:r.to_address,
  leader_only:r.leader_only,execution_mode:r.execution_mode,data:{...r.data,calldata:{base64:r.data?.calldata?.base64}},
  consensus_data:{votes:r.consensus_data?.votes,leader_receipt:r.consensus_data?.leader_receipt?.map(l=>({mode:l.mode,execution_result:l.execution_result,result:{status:l.result?.status,payload:typeof l.result?.payload==='object'?{readable:l.result.payload?.readable}:l.result?.payload}}))}};
}
const evidence={network:{chainId:61999,rpc:'https://studio.genlayer.com/api'},address,owner,recipient,sourceSha256:sha,
  note:'Synthetic public library metadata; two test wallets controlled by one operator. No personal data or funds transferred. Receipts project verification fields; node configuration and timing logs omitted. Fetch hashes for full RPC receipts.',steps:Object.fromEntries(Object.entries(state.steps).map(([name,entry])=>[name,{hash:entry.hash,receipt:project(entry.receipt)}])),record};
fs.writeFileSync(path.join(root,'evidence/studionet.json'),encode(evidence));
console.log('VERIFIED',address,record.status);
