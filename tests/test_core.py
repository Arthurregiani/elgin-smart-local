import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bridge'))
from core import *
from worker import Transport

BASE=dict(on=True,mode='colour',white=10,temperature=321,h=243,s=777,v=2)
class Precision(unittest.TestCase):
 def test_hsv_full_native_range(self):
  for h in (0,1,359,360):
   for s in (0,1,10,999,1000):
    for v in (0,1,2,999,1000):self.assertEqual(decode_hsv(encode_hsv(h,s,v)),(h,s,v))
 def test_hue_preserves_sv(self):self.assertEqual(command(BASE,{'h':17}),{'24':encode_hsv(17,777,2)})
 def test_saturation_preserves_hv(self):self.assertEqual(command(BASE,{'s':1}),{'24':encode_hsv(243,1,2)})
 def test_color_brightness_preserves_hs(self):self.assertEqual(command(BASE,{'v':0}),{'24':encode_hsv(243,777,0)})
 def test_white_off_is_not_min(self):
  self.assertEqual(command(BASE,{'white':0}),{'20':False})
  for n in range(1,11):self.assertEqual(command(BASE,{'white':n}),{'22':10})
  self.assertEqual(command(BASE,{'white':1000}),{'22':1000})
 def test_every_white_step(self):
  for n in range(10,1001):self.assertEqual(command(BASE,{'white':n}),{'22':n})
 def test_independent_temperature(self):self.assertEqual(command(BASE,{'temperature':0}),{'23':0})
 def test_mode_keeps_both_memories(self):self.assertEqual(command(BASE,{'mode':'white'}),{'21':'white'})
 def test_validation(self):
  for p in ({'v':-1},{'v':1001},{'v':float('nan')},{'v':True},{'v':'1'},{'h':361},{'mode':'scene'},{'key':'secret'},{'on':1},{}):
   with self.assertRaises(ValueError):command(BASE,p)
 def test_incomplete_state_rejected(self):
  with self.assertRaises(ValueError):state_from_dps({'24':'000000000000'})
 def test_divergence(self):self.assertEqual(differences({'22':1},{'22':10}),{'22':{'sent':1,'read':10}})
 def test_coalescing_latest_and_independent(self):
  q=Pending();q.put({'s':1},1)
  for i in range(10000):q.put({'h':i%360},i+2)
  p,s=q.take();self.assertEqual(p,{'s':1,'h':9999%360});self.assertEqual(s,10001);self.assertFalse(q.patch)
 def test_power_after_zero_brightness_is_latest(self):
  q=Pending();q.put({"white":0},1);q.put({"on":True},2)
  self.assertEqual(q.take(),({"on":True},2))
 def test_invalid_does_not_poison_pending(self):
  q=Pending();q.put({'s':1},1)
  with self.assertRaises(ValueError):q.put({'h':900},2)
  self.assertEqual(q.take(),({'s':1},1))

class Fake:
 instances=[];fail=False;partial=False
 def __init__(self,*a,**kw):self.closed=False;self.version=kw['version'];self.__class__.instances.append(self)
 def set_socketTimeout(self,v):self.timeout=v
 def set_socketRetryLimit(self,v):pass
 def set_socketPersistent(self,v):self.persistent=v
 def close(self):self.closed=True
 def status(self):
  if self.fail:raise OSError('sensitive upstream message')
  return {'dps':{'24':'000000000000'} if self.partial else {'20':True,'21':'white','22':10,'23':0,'24':'000000000000'}}
 def set_multiple_values(self,v):
  if self.fail:raise OSError('sensitive upstream message')
  return None
class Connections(unittest.TestCase):
 def setUp(self):Fake.instances=[];Fake.fail=False;Fake.partial=False
 def transport(self,version='3.5'):return Transport(dict(id='test',key='not-a-real-key',ip='127.0.0.1',version=version),Fake)
 def test_protocols_and_closure(self):
  for version in ('3.4','3.5'):
   t=self.transport(version);t.write({'20':False});t.read()
  self.assertEqual([d.version for d in Fake.instances],[3.4,3.4,3.5,3.5]);self.assertTrue(all(d.closed and not d.persistent for d in Fake.instances))
 def test_error_closes_socket(self):
  Fake.fail=True
  for op in (lambda:self.transport().read(),lambda:self.transport().write({'20':True})):
   with self.assertRaises(OSError):op()
  self.assertTrue(all(d.closed for d in Fake.instances))
 def test_partial_closed_and_rejected(self):
  Fake.partial=True
  with self.assertRaises(ValueError):self.transport().read()
  self.assertTrue(Fake.instances[0].closed)
if __name__=='__main__':unittest.main()

class ImplicitMode(unittest.TestCase):
 def test_white_fields_cannot_override_final_colour_preset(self):
  class ModeTransport(Transport):
   def __init__(self):self.dps={'20':True,'21':'colour','22':10,'23':0,'24':'007800010002'};self.writes=[]
   def write(self,dps):
    self.writes.append(dps.copy());self.dps.update(dps)
    if '22' in dps or '23' in dps:self.dps['21']='white'
   def read(self):return self.dps.copy()
  t=ModeTransport()
  state,diff,sent=t.apply(state_from_dps(t.read()),{'mode':'colour','white':10,'temperature':0,'h':120,'s':1,'v':1})
  self.assertEqual(state['mode'],'colour');self.assertEqual(diff,{})
  self.assertEqual(t.writes[-1],{'21':'colour'});self.assertEqual(len(t.writes),2)
