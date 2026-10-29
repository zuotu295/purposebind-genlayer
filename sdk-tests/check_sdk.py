"""Real pinned SDK storage/calldata with mocked LLM. Run in its own interpreter."""
import json
from pathlib import Path
from gltest.direct import VMContext, deploy_contract
root=Path(__file__).resolve().parents[1]
data=json.loads((root/'examples/library.json').read_text())
owner='0x'+'1'*40
recipient='0x'+'2'*40
cells=[]
for i,f in enumerate(data['fields']):
    for j,r in enumerate(data['requirements']):
        cells.append({'field':f['id'],'requirement':j,'coverage':'YES' if i==0 else 'NO',
            'field_quote':f['description'][:300],'requirement_quote':r,
            'reason':'This field explicitly contains the required aggregate information.' if i==0 else 'This field explicitly omits the required aggregate information.'})
vm=VMContext()
vm.sender=owner
vm.mock_llm('^Classify',json.dumps({'cells':cells}))
vm.mock_llm('^Audit',json.dumps({'valid':True}))
with vm.activate():
    contract=deploy_contract(root/'contracts/purpose_bind.py',vm,sdk_version='v0.3.0-rc7')
    contract.register('sdk',recipient,json.dumps(data))
    record=json.loads(contract.assess(owner,'sdk'))
    assert record['options']==[['city_weekly_totals']]
    assert vm.run_validator() is True
    wrong=json.loads(json.dumps(cells)); wrong[0]['coverage']='NO'
    vm.clear_mocks()
    vm.mock_llm('^Classify',json.dumps({'cells':wrong}))
    assert vm.run_validator() is False
    with vm.prank(recipient):
        contract.claim(owner,'sdk',record['grant_digest'],'["city_weekly_totals"]')
    assert json.loads(contract.get_record(owner,'sdk'))['status']=='CLAIMED'
    assert contract.get_protocol()=='purposebind-1'
print('SDK storage, calldata, validator acceptance/rejection and claim: PASS (mocked LLM, no network)')
