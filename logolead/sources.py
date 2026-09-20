import asyncio
from datetime import datetime, timezone
from classifier import score
async def scan_chat(client,chat,cutoff,seen,key_fn,limit=120):
 out=[]
 async for m in client.iter_messages(chat,limit=limit):
  if not m.message or not m.date or m.date<cutoff:continue
  k=key_fn(getattr(chat,'id',0),m.id)
  if k in seen:continue
  seen.add(k); sc,why=score(m.message)
  if sc<=0:continue
  username=getattr(chat,'username',None)
  url=f'https://t.me/{username}/{m.id}' if username else ''
  out.append((sc,m.date,m.message,url,why))
 return out

def merge_unique(items):
 best={}
 for x in items:
  sig=(x[2].strip().lower()[:500],x[3])
  if sig not in best or x[0]>best[sig][0]:best[sig]=x
 return list(best.values())
