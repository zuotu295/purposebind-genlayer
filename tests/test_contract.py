"""Protocol tests: actual contract, mocked host/model; no network consensus."""
import importlib.util
import json
import sys
import types
import unittest
from pathlib import Path

OWNER = '0x' + '1' * 40
RECIPIENT = '0x' + '2' * 40
OTHER = '0x' + '3' * 40
class Return:
    def __init__(self, value): self.calldata = value
class Public:
    write = staticmethod(lambda f: f)
    view = staticmethod(lambda f: f)
host = types.SimpleNamespace(message=types.SimpleNamespace(sender_address=OWNER), Contract=object,
    public=Public(), vm=types.SimpleNamespace(UserError=ValueError, Return=Return), nondet=types.SimpleNamespace())
sys.modules['genlayer'] = types.SimpleNamespace(gl=host, TreeMap=dict)
spec = importlib.util.spec_from_file_location('contract', Path(__file__).parents[1]/'contracts/purpose_bind.py')
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)
DATA = {'purpose':'Publish weekly city-level totals of public library visits.',
 'requirements':['Weekly visit totals for each city.', 'The city name identifying each total.'],
 'fields':[{'id':'summary','description':'Weekly visit totals for each city, including the city name identifying each total.'},
           {'id':'totals','description':'Weekly visit totals for each city, without any city name or identifier.'},
           {'id':'city','description':'The city name identifying each total, with no visit counts.'}]}

def result(labels, data=DATA):
    return {'cells':[{'field':f['id'],'requirement':j,'coverage':labels[i*len(data['requirements'])+j],
       'field_quote':f['description'],'requirement_quote':r,'reason':'The supplied metadata explicitly describes this information.'}
       for i,f in enumerate(data['fields']) for j,r in enumerate(data['requirements'])]}

class Tests(unittest.TestCase):
    def setUp(self):
        host.message.sender_address=OWNER
        self.contract=c.PurposeBind()
        self.calls=[]
        self.labels=['YES','YES','YES','NO','NO','YES']
        self.independent=None
        self.audit=True
        def llm(prompt, **kw):
            self.calls.append(prompt)
            if prompt.startswith('Audit '): return {'valid':self.audit}
            return result(self.independent if self.independent and len(self.calls)>1 else self.labels)
        host.nondet.exec_prompt=llm
        def run(leader, validator):
            value=leader()
            if not validator(Return(value)): raise ValueError('DISAGREEMENT')
            return value
        host.vm.run_nondet_unsafe=run
    def register(self):
        return json.loads(self.contract.register('demo',RECIPIENT,json.dumps(DATA)))
    def assess(self): return json.loads(self.contract.assess(OWNER,'demo'))
    def test_complete_lifecycle(self):
        self.register(); r=self.assess()
        self.assertEqual(r['options'],[['summary']]); self.assertEqual(r['status'],'READY')
        host.message.sender_address=RECIPIENT
        r=json.loads(self.contract.claim(OWNER,'demo',r['grant_digest'],'["summary"]'))
        self.assertEqual(r['status'],'CLAIMED')
        with self.assertRaisesRegex(ValueError,'NOT_READY'): self.contract.claim(OWNER,'demo',r['grant_digest'],'["summary"]')
    def test_no_owner_override(self):
        self.register(); r=self.assess()
        with self.assertRaisesRegex(ValueError,'NOT_RECIPIENT'): self.contract.claim(OWNER,'demo',r['grant_digest'],'["summary"]')
    def test_superset_rejected(self):
        self.register(); r=self.assess(); host.message.sender_address=RECIPIENT
        for fields in [['summary','city'],['totals','city'],['summary','summary'],[]]:
            with self.assertRaises(ValueError): self.contract.claim(OWNER,'demo',r['grant_digest'],json.dumps(fields))
    def test_digest_rejected(self):
        self.register(); self.assess(); host.message.sender_address=RECIPIENT
        with self.assertRaisesRegex(ValueError,'DIGEST_MISMATCH'): self.contract.claim(OWNER,'demo','0'*64,'["summary"]')
    def test_immutable(self):
        self.register()
        with self.assertRaisesRegex(ValueError,'ID_USED'): self.register()
        self.assess()
        with self.assertRaisesRegex(ValueError,'ALREADY_ASSESSED'): self.assess()
    def test_independent_disagreement_atomic(self):
        self.register(); self.independent=['NO']*6
        with self.assertRaisesRegex(ValueError,'DISAGREEMENT'): self.assess()
        self.assertEqual(json.loads(self.contract.get_record(OWNER,'demo'))['status'],'REGISTERED')
    def test_audit_not_truthy(self):
        self.register(); self.audit='true'
        with self.assertRaisesRegex(ValueError,'DISAGREEMENT'): self.assess()
    def test_irrelevant_quote_rejected(self):
        raw=result(self.labels); raw['cells'][0]['field_quote']='Not in the declared description.'
        with self.assertRaisesRegex(ValueError,'UNSUPPORTED_QUOTE'): c.matrix(raw,DATA)
    def test_unknown_can_hide_smaller_cover(self):
        self.register(); self.labels=['UNKNOWN','UNKNOWN','YES','NO','NO','YES']
        r=self.assess(); self.assertEqual(r['status'],'REVIEW'); self.assertEqual(r['options'],[])
    def test_unknown_equal_size_does_not_block_proven_cover(self):
        self.register(); self.labels=['YES','YES','UNKNOWN','NO','NO','YES']
        self.assertEqual(self.assess()['status'],'READY')
    def test_unsatisfiable(self):
        self.register(); self.labels=['NO']*6
        self.assertEqual(self.assess()['status'],'UNSATISFIABLE')
    def test_unknown_only_is_review(self):
        self.register(); self.labels=['UNKNOWN']*6
        self.assertEqual(self.assess()['status'],'REVIEW')
    def test_ties_retained(self):
        self.register(); self.labels=['YES']*6
        self.assertEqual(self.assess()['options'],[['summary'],['totals'],['city']])
    def test_unauthorized_assessment(self):
        self.register(); host.message.sender_address=OTHER
        with self.assertRaisesRegex(ValueError,'NOT_PARTICIPANT'): self.assess()
    def test_sender_namespaces(self):
        self.register(); host.message.sender_address=OTHER; self.register()
        self.assertEqual(len(self.contract.records),2)
    def test_invalid_input(self):
        for field in [[],[DATA['fields'][0]],[DATA['fields'][0]]*2]:
            data=dict(DATA,fields=field)
            with self.assertRaises(ValueError): c.parse_input(json.dumps(data))
    def test_missing_or_duplicate_cells(self):
        raw=result(self.labels); raw['cells'].pop()
        with self.assertRaises(ValueError): c.matrix(raw,DATA)
        raw=result(self.labels); raw['cells'][1]=raw['cells'][0]
        with self.assertRaises(ValueError): c.matrix(raw,DATA)
    def test_enumeration_exhaustive(self):
        # Exhaust all 2^6 binary coverage matrices; compare independent set-union oracle.
        import itertools
        for bits in itertools.product([False,True],repeat=6):
            cells=c.matrix(result(['YES' if b else 'NO' for b in bits]),DATA)
            candidates=[]
            for size in range(1,4):
                candidates=[list(sub) for sub in itertools.combinations(range(3),size)
                            if set().union(*[{j for j in range(2) if bits[i*2+j]} for i in sub])=={0,1}]
                if candidates: break
            expected={tuple(DATA['fields'][i]['id'] for i in sub) for sub in candidates}
            self.assertEqual({tuple(x) for x in c.covers(DATA,cells)},expected)

if __name__=='__main__': unittest.main()
