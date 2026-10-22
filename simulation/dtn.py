"""Contact-trace DTN simulator. Abstract contacts, not a BLE/Wi-Fi radio emulator."""
from dataclasses import dataclass,asdict
import argparse,csv,json,math,random,statistics
from pathlib import Path
@dataclass(frozen=True)
class Message:
 id:str
 origin:int
 created:float
 ttl:float
 priority:int=2
@dataclass
class Copy:
 hops:int=0
 tokens:int=4

def run(messages,contacts,gateway_nodes,algorithm='epidemic',capacity=100,budget=4,hop_limit=8,bandwidth=5,end=None):
 if algorithm not in ['epidemic','spray_wait']:raise ValueError('Unknown routing')
 if min(capacity,budget,hop_limit,bandwidth)<1:raise ValueError('Positive limits required')
 if len({m.id for m in messages})!=len(messages):raise ValueError('Message IDs must be unique')
 byid={m.id:m for m in messages};buffers={};delivered={};transfers=0;drops=0;expired_copies=0
 events=[(m.created,0,m.id) for m in messages]+[(t,1,(a,b)) for t,a,b in contacts]
 events.sort(key=lambda e:(e[0],e[1],str(e[2])))
 def buffer(node):return buffers.setdefault(node,{})
 def put(node,id,copy,now):
  nonlocal drops
  buf=buffer(node)
  if id in buf:return False
  if len(buf)>=capacity:
   worst=max(buf,key=lambda x:(byid[x].priority,-byid[x].created,x))
   if (byid[id].priority,-byid[id].created,id)>=(byid[worst].priority,-byid[worst].created,worst):drops+=1;return False
   del buf[worst];drops+=1
  buf[id]=copy;return True
 for now,kind,payload in events:
  if end is not None and now>end:break
  for buf in buffers.values():
   for id in list(buf):
    if byid[id].created+byid[id].ttl<=now:del buf[id];expired_copies+=1
  if kind==0:
   m=byid[payload]
   if m.ttl<=0:continue
   if m.origin in gateway_nodes:delivered[m.id]={'delay':0,'hops':0}
   else:put(m.origin,m.id,Copy(0,budget),now)
   continue
  a,b=payload
  if a==b:continue
  # Snapshot both inventories at contact start to avoid zero-time back-propagation.
  snapshots={a:list(buffer(a)),b:list(buffer(b))}
  for src,dst in [(a,b),(b,a)]:
   candidates=sorted(snapshots[src],key=lambda id:(byid[id].priority,byid[id].created,id));sent=0
   for id in candidates:
    if sent>=bandwidth:break
    if id not in buffer(src):continue
    copy=buffer(src)[id]
    if copy.hops>=hop_limit or id in buffer(dst):continue
    if dst in gateway_nodes:
     # Server already received: no redundant payload and no new delivery count.
     if id not in delivered:
      delivered[id]={'delay':now-byid[id].created,'hops':copy.hops+1};transfers+=1;sent+=1
     continue
    if algorithm=='spray_wait' and copy.tokens<2:continue
    child_tokens=copy.tokens//2 if algorithm=='spray_wait' else budget
    if put(dst,id,Copy(copy.hops+1,child_tokens),now):
     if algorithm=='spray_wait':copy.tokens-=child_tokens
     transfers+=1;sent+=1
 finish=end if end is not None else max([t for t,_,_ in events],default=0)
 for buf in buffers.values():
  for id in list(buf):
   if byid[id].created+byid[id].ttl<=finish:del buf[id];expired_copies+=1
 delays=sorted(v['delay'] for v in delivered.values());n=len(messages);d=len(delivered)
 return {'algorithm':algorithm,'generated':n,'delivered':d,'delivery_ratio':d/n if n else 0,'mean_delay_s':statistics.mean(delays) if delays else None,'p95_delay_s':delays[max(0,math.ceil(.95*d)-1)] if delays else None,'payload_transfers':transfers,'overhead_ratio':(transfers-sum(v["hops"]>0 for v in delivered.values()))/d if d else None,'buffer_copy_drops':drops,'expired_copies':expired_copies,'mean_hops':statistics.mean(v['hops'] for v in delivered.values()) if d else None,'deliveries':delivered,'buffers':{k:{id:asdict(v) for id,v in buf.items()} for k,buf in buffers.items()}}

def generate(nodes=30,seed=42,duration=7200,count=100):
 if nodes<3:raise ValueError('At least 3 nodes')
 rng=random.Random(seed)
 messages=[Message(f'm{i}',rng.randrange(1,nodes),rng.randrange(duration//2),1800,rng.choice([1,2,2,3])) for i in range(count)]
 contacts=[]
 for t in range(0,duration,30):
  for _ in range(max(1,nodes//4)):
   a,b=rng.sample(range(nodes),2);contacts.append((float(t),a,b))
 return messages,contacts
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--nodes',type=int,default=30);p.add_argument('--seeds',type=int,default=10);p.add_argument('--out',type=Path,default=Path(__file__).parent/'results');a=p.parse_args()
 if a.seeds<1:p.error('seeds >= 1')
 a.out.mkdir(parents=True,exist_ok=True);rows=[]
 for seed in range(a.seeds):
  msgs,trace=generate(a.nodes,seed)
  for alg in ['epidemic','spray_wait']:
   r=run(msgs,trace,{0},alg,capacity=50,bandwidth=5,end=7200)
   rows.append({k:v for k,v in r.items() if k not in ['deliveries','buffers']}|{'seed':seed,'nodes':a.nodes})
 keys=list(rows[0])
 with (a.out/'runs.csv').open('w',newline='') as f:w=csv.DictWriter(f,keys);w.writeheader();w.writerows(rows)
 summary={'description':'Synthetic random contacts, gateway node 0; not a prediction of field delivery','config':{'nodes':a.nodes,'seeds':a.seeds,'duration_s':7200,'messages':100,'ttl_s':1800,'buffer':50,'bandwidth_per_direction':5,'copies':4},'algorithms':{}}
 for alg in ['epidemic','spray_wait']:
  subset=[r for r in rows if r['algorithm']==alg];summary['algorithms'][alg]={}
  for metric in ['delivery_ratio','mean_delay_s','overhead_ratio']:
   values=[r[metric] for r in subset if r[metric] is not None]
   summary['algorithms'][alg][metric]={'mean':statistics.mean(values) if values else None,'std':statistics.stdev(values) if len(values)>1 else 0,'runs':len(values)}
 (a.out/'summary.json').write_text(json.dumps(summary,indent=2))
 print(json.dumps(summary,indent=2))
