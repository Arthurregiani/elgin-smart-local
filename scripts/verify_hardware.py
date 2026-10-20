"""Controlled LAN acceptance, all three lamps sequentially; no credentials in evidence."""
import argparse,json,sys,time,signal
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE/'bridge'))
from worker import Transport, devices_path
from core import state_from_dps

def configured_devices():
 data=json.loads(devices_path().read_text())
 return data if isinstance(data,list) else data['devices']

def run(ip):
 d=next(d for d in configured_devices() if d['ip']==ip)
 t=Transport(d);original={k:v for k,v in t.read().items() if k in ('20','21','22','23','24')}
 report={'device':d['name'],'ip':ip,'protocol':d['version'],'original':original,'checks':[],'restored':False,'measurement':'DPS readback only; no photometer'}
 (BASE/'evidence').mkdir(exist_ok=True,mode=0o700)
 path=BASE/'evidence'/f'acceptance-{ip.split(".")[-1]}.json'
 def save():path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 save()
 try:
  # Dim configuration is written before switching power on.
  cases=[{'on':False,'mode':'white','white':10},{'on':True},{'mode':'colour','h':120,'s':0,'v':1},{'s':1},{'h':121},{'v':0},{'v':2},{'mode':'white'},{'mode':'colour'}]
  state=state_from_dps(t.read())
  for patch in cases:
   state,diff,sent=t.apply(state,patch)
   report['checks'].append({'patch':patch,'sent':sent,'actual':state,'differences':diff});save()
   print(d['name'],patch,'OK' if not diff else 'DIVERGENT',flush=True)
   if diff:raise RuntimeError('Unexpected DPS divergence')
   time.sleep(.3)
 finally:
  for attempt in range(3):
   try:
    t.write({'20':False});time.sleep(.2)
    t.write({k:v for k,v in original.items() if k!='20'});time.sleep(.2)
    t.write({'21':original['21']});time.sleep(.3)
    t.write({'20':original['20']});time.sleep(.3)
    actual=t.read();report['after']={k:actual.get(k) for k in original}
    report['restored']=all(actual.get(k)==v for k,v in original.items());save()
    if report['restored']:break
   except Exception:time.sleep(.5)
  print(d['name'],'RESTORED',report['restored'],flush=True)
  if not report['restored']:raise RuntimeError('Restoration not confirmed; snapshot in evidence')

if __name__=='__main__':
 def interrupted(*_):raise KeyboardInterrupt()
 signal.signal(signal.SIGTERM,interrupted)
 parser=argparse.ArgumentParser(description='Altera brevemente as lâmpadas e restaura o estado original.')
 group=parser.add_mutually_exclusive_group(required=True)
 group.add_argument('--ip',action='append',help='IP configurado; pode ser repetido')
 group.add_argument('--all',action='store_true',help='Testar todas as lâmpadas configuradas, sequencialmente')
 args=parser.parse_args()
 ips=[d['ip'] for d in configured_devices()] if args.all else args.ip
 for ip in ips:run(ip)
