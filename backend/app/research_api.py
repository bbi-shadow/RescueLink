import csv,io,json,time
from types import SimpleNamespace
from typing import Literal
from fastapi import APIRouter,Depends,HTTPException
from fastapi.responses import Response
from pydantic import BaseModel,Field,ConfigDict
from sqlalchemy import select,update,func
from .database import Incident,AuditEvent
from .triage import suggest
class TriageInput(BaseModel):
 model_config=ConfigDict(extra='forbid')
 text:str=Field(min_length=3,max_length=1000)
 priority:int=Field(default=3,ge=1,le=3)
 needs:list[Literal["medical","evacuation","food","water","other"]]=Field(default_factory=list,max_length=5)
class PriorityUpdate(BaseModel):
 model_config=ConfigDict(extra='forbid')
 version:int=Field(ge=1)
 priority:int=Field(ge=1,le=3)
 reason:str=Field(min_length=3,max_length=250)
def build_router(session,require_admin,view):
 router=APIRouter(prefix='/api/v1',dependencies=[Depends(require_admin)])
 @router.post('/triage/preview')
 def preview(data:TriageInput):
  if not data.text.strip():raise HTTPException(422,'Nội dung trống')
  return suggest(SimpleNamespace(**data.model_dump()))
 @router.patch('/sos/{message_id}/priority')
 def adjust(message_id:str,data:PriorityUpdate,db=Depends(session)):
  row=db.get(Incident,message_id)
  if not row:raise HTTPException(404,'Không tìm thấy SOS')
  if row.status=='RESOLVED':raise HTTPException(422,'SOS đã hoàn tất')
  if not data.reason.strip():raise HTTPException(422,'Cần lý do')
  old=row.priority
  r=db.execute(update(Incident).where(Incident.message_id==message_id,Incident.version==data.version).values(priority=data.priority,version=data.version+1).execution_options(synchronize_session=False))
  if r.rowcount!=1:db.rollback();raise HTTPException(409,'Xung đột cập nhật')
  db.add(AuditEvent(message_id=message_id,event='PRIORITY_CHANGED',details=json.dumps({'from':old,'to':data.priority,'reason':data.reason.strip()},ensure_ascii=False),at_ms=int(time.time()*1000)))
  db.commit();db.expire_all();return view(db.get(Incident,message_id))
 @router.get('/stats')
 def stats(db=Depends(session)):
  statuses=dict(db.execute(select(Incident.status,func.count()).group_by(Incident.status)).all())
  priorities={str(p):n for p,n in db.execute(select(Incident.priority,func.count()).where(Incident.status!='RESOLVED').group_by(Incident.priority))}
  return {'total':sum(statuses.values()),'statuses':statuses,'open_priorities':priorities}
 @router.get('/export.csv')
 def export(db=Depends(session)):
  # Bound export memory. Caller gets explicit count/limit headers.
  rows=db.scalars(select(Incident).order_by(Incident.received_at_ms.desc()).limit(10000)).all()
  stream=io.StringIO();w=csv.writer(stream);w.writerow(['message_id','priority','status','team','text','location','latitude','longitude','received_at_ms'])
  def safe(v):
   s=str(v or '')
   return "'"+s if s.lstrip().startswith(('=','+','-','@','\t','\r')) else s
  for r in rows:w.writerow([r.message_id,r.priority,r.status,safe(r.assigned_team),safe(r.body['text']),safe(r.body['location_text']),r.body['latitude'],r.body['longitude'],r.received_at_ms])
  return Response('\ufeff'+stream.getvalue(),media_type='text/csv',headers={'Content-Disposition':'attachment; filename="rescuelink-sos.csv"','X-Export-Count':str(len(rows)),'X-Export-Limit':'10000'})
 return router
