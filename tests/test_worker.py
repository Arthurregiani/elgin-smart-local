import sys,time,unittest,threading
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bridge'))
import worker
from core import state_from_dps,command
DPS={'20':True,'21':'colour','22':10,'23':0,'24':'007800010002'}
class FakeTransport:
 def __init__(self):self.calls=[];self.dps=DPS.copy()
 def read(self):return self.dps.copy()
 def apply(self,state,patch):
  self.calls.append((time.monotonic(),patch.copy()));sent=command(state,patch);self.dps.update(sent)
  return state_from_dps(self.dps),{},sent
class Workers(unittest.TestCase):
 def setUp(self):worker.STOP.clear();worker.DRAIN.clear();self.ws=[]
 def tearDown(self):
  worker.STOP.set()
  for w in self.ws:
   with w.cv:w.cv.notify()
   w.join(2)
  worker.STOP.clear();worker.DRAIN.clear()
 def make(self):
  w=worker.Worker(0,{});w.transport=FakeTransport();self.ws.append(w);return w
 def wait_for(self,predicate):
  end=time.monotonic()+3
  while not predicate() and time.monotonic()<end:time.sleep(.01)
  self.assertTrue(predicate())
 def test_last_value_survives_and_rate_is_bounded(self):
  w=self.make();events=[]
  with patch.object(worker,'emit',events.append):
   w.start();self.wait_for(lambda:len(events)>0)
   for i in range(1000):w.submit({'s':i},i+1)
   self.wait_for(lambda:w.seq==1000)
   self.assertEqual(w.state['s'],999)
   self.assertLessEqual(len(w.transport.calls),2)
   w.submit({'v':1},1001);self.wait_for(lambda:w.seq==1001)
   times=[c[0] for c in w.transport.calls]
   for a,b in zip(times,times[1:]):self.assertGreaterEqual(b-a,.29)
 def test_graceful_close_drains_last_patch(self):
  w=self.make();w.submit({'s':0,'v':1},30);worker.DRAIN.set()
  with patch.object(worker,'emit'):
   w.start();w.join(3)
  self.assertFalse(w.is_alive());self.assertEqual(w.state['s'],0);self.assertEqual(w.seq,30)
 def test_slow_device_does_not_block_another(self):
  slow=self.make();fast=self.make();gate=threading.Event()
  def read_slow():gate.wait(2);return DPS.copy()
  slow.transport.read=read_slow
  try:
   with patch.object(worker,'emit'):
    slow.start();fast.submit({'s':0},5);fast.start()
    self.wait_for(lambda:fast.seq==5)
    self.assertTrue(slow.is_alive());self.assertEqual(fast.state['s'],0)
  finally:gate.set()
 def test_fresh_read_preserves_external_brightness(self):
  w=self.make();events=[]
  with patch.object(worker,'emit',events.append):
   w.start();self.wait_for(lambda:len(events)>0)
   w.transport.dps['24']='0078000101f4'
   w.submit({'h':121},3);self.wait_for(lambda:w.seq==3)
   self.assertEqual(w.state['v'],500)
 def test_failure_is_sanitized_and_not_retried_forever(self):
  w=self.make();events=[]
  def fail():raise RuntimeError('LOCAL_KEY_SECRET')
  w.transport.read=fail
  with patch.object(worker,'emit',events.append):
   w.start();self.wait_for(lambda:len(events)>0);time.sleep(.4)
  self.assertEqual(len(events),1);self.assertNotIn('LOCAL_KEY',str(events));self.assertEqual(events[0]['event'],'error')
if __name__=='__main__':unittest.main()
