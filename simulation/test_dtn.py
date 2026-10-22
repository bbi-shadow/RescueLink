from dtn import Message,run
import pytest
@pytest.mark.parametrize('alg',['epidemic','spray_wait'])
def test_store_carry_forward_and_dedup(alg):
 r=run([Message('a',1,0,100,1)],[(10,1,2),(11,1,2),(20,2,0),(30,1,0)],{0},alg,budget=2)
 assert r['delivered']==1 and r['deliveries']['a']=={'delay':20,'hops':2}
 assert r['payload_transfers']==2

def test_expiry_and_hop_limit():
 assert run([Message('a',1,0,10)],[(10,1,0)],{0})['delivered']==0
 assert run([Message('a',1,0,100)],[(10,1,2),(20,2,0)],{0},hop_limit=1)['delivered']==0

def test_single_token_waits_for_gateway():
 r=run([Message('a',1,0,100)],[(10,1,2),(20,2,0),(30,1,0)],{0},'spray_wait',budget=1)
 assert r['deliveries']['a']['delay']==30 and r['payload_transfers']==1

def test_copy_budget_conserved_without_delivery():
 r=run([Message('a',1,0,100)],[(1,1,2),(2,1,3),(3,2,4),(4,2,5)],{0},'spray_wait',budget=4)
 assert sum(b.get('a',{}).get('tokens',0) for b in r['buffers'].values())==4

def test_priority_buffer_and_bandwidth():
 msgs=[Message('low',1,0,100,3),Message('high',1,1,100,1)]
 r=run(msgs,[(2,1,0)],{0},capacity=1,bandwidth=1)
 assert set(r['deliveries'])=={'high'} and r['buffer_copy_drops']==1

def test_no_delivery_metrics_do_not_divide_by_zero():
 r=run([Message('a',1,0,1)],[],{0},end=5)
 assert r['overhead_ratio'] is None and r['mean_delay_s'] is None and r['expired_copies']==1
