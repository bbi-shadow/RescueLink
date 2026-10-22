"""Merge exported Android JSONL logs. Clock synchronization is required."""
import argparse,json,re,statistics
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('files',nargs='+',type=Path);p.add_argument('--out',type=Path,default=Path('field-evaluation.json'));a=p.parse_args()
created={};received={};stored=set();attempts=0;errors=[]
for file in a.files:
 for number,line in enumerate(file.read_text(encoding='utf-8-sig').splitlines(),1):
  if not line.strip():continue
  try:
   row=json.loads(line);event=row['event'];at=int(row['at_ms'])
   match=re.match(r'(CREATED|STORED|SERVER_RECEIVED|SEND_ATTEMPT) ([0-9a-f]{64})(?: |$)',event)
   if not match:continue
   kind,id=match.groups()
   if kind=='CREATED':created[id]=min(created.get(id,at),at)
   if kind=='SERVER_RECEIVED':received[id]=min(received.get(id,at),at)
   if kind=='STORED':stored.add(id)
   if kind=='SEND_ATTEMPT':attempts+=1
  except (ValueError,KeyError,TypeError):errors.append(f'{file.name}:{number}')
delays=[(received[id]-at)/1000 for id,at in created.items() if id in received]
report={'scope':'Only generated IDs present in supplied origin logs; server receipt is not rescue arrival','requires_synchronized_clocks':True,'generated':len(created),'server_received':sum(id in received for id in created),'relay_stored_unique':len(stored&created.keys()),'delivery_ratio':sum(id in received for id in created)/len(created) if created else None,'mean_delay_s':statistics.mean(delays) if delays else None,'negative_delays':sum(d<0 for d in delays),'send_attempts_not_confirmed_transfers':attempts,'unmatched_server_ids':len(received.keys()-created.keys()),'invalid_lines':errors}
a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report,ensure_ascii=False,indent=2))
