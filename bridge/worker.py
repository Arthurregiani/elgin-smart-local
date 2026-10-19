#!/usr/bin/env python3
"""One app-owned JSONL helper, no listening sockets. Credentials never leave Python."""
import ctypes
import fcntl
import json
import os
from pathlib import Path
import signal
import sys
import threading
import time
import tinytuya
from core import Pending, command, differences, state_from_dps

BASE=Path(__file__).resolve().parents[1]
OUTPUT=threading.Lock()
STOP=threading.Event()
DRAIN=threading.Event()

def emit(obj):
    with OUTPUT:
        try:print(json.dumps(obj,ensure_ascii=False),flush=True)
        except (BrokenPipeError,OSError):STOP.set()

class Transport:
    def __init__(self, config, factory=tinytuya.Device):self.config=config;self.factory=factory
    def connect(self):
        d=self.config
        dev=self.factory(d['id'],d['ip'],d['key'],version=float(d['version']))
        dev.set_socketTimeout(1.5);dev.set_socketRetryLimit(1);dev.set_socketPersistent(False)
        return dev
    def read(self):
        for attempt in range(2):
            try:return self._read_once()
            except Exception:
                if attempt or STOP.wait(.3):raise
    def _read_once(self):
        dev=self.connect()
        try:
            result=dev.status()
            if not isinstance(result,dict) or 'dps' not in result:raise ConnectionError('LAN indisponível')
            state_from_dps(result['dps'])  # reject partial unsolicited updates
            return result['dps']
        finally:dev.close()
    def write(self,dps):
        dev=self.connect()
        try:
            result=dev.set_multiple_values(dps)
            if isinstance(result,dict) and 'Error' in result:raise ConnectionError('Comando sem confirmação')
        finally:dev.close()
    def apply(self,state,patch):
        sent=command(state,patch)
        expected=sent|{'21':patch.get('mode',state['mode'])}
        self.write(sent)
        STOP.wait(.12)
        actual=self.read()  # fresh session avoids interpreting a partial push as full status
        # Some A70 firmware implicitly selects white when DPS 22/23 is written,
        # even if the same packet asks for colour. Select the intended mode last.
        if actual.get('21')!=expected['21'] and {'white','temperature','h','s','v'} & patch.keys():
            if not STOP.wait(.3):
                self.write({'21':expected['21']})
                STOP.wait(.12)
                actual=self.read()
        diff=differences(expected,actual)
        if diff and not STOP.wait(.25):
            actual=self.read();diff=differences(expected,actual)
        return state_from_dps(actual),diff,sent

class Worker(threading.Thread):
    def __init__(self,index,config):
        super().__init__(name=f'bulb-{index}',daemon=True)
        self.index=index;self.config=config;self.transport=Transport(config)
        self.cv=threading.Condition();self.pending=Pending();self.refresh=True
        self.state=None;self.seq=0;self.last=0.;self.next_poll=0.
    def submit(self,patch,seq):
        with self.cv:
            self.pending.put(patch,seq);self.cv.notify()
    def run(self):
        while not STOP.is_set():
            with self.cv:
                if DRAIN.is_set() and not self.pending.patch:return
                now=time.monotonic()
                due=max(0.,.3-(now-self.last))
                if not self.pending.patch and not self.refresh and now<self.next_poll:
                    self.cv.wait(min(1.,self.next_poll-now));continue
                if due:
                    self.cv.wait(due);continue
                patch,seq=self.pending.take();self.refresh=False
            try:
                # Re-read immediately before a partial HSV edit to preserve changes
                # made by Google Home or another controller since the last poll.
                self.state=state_from_dps(self.transport.read())
                diff={};sent={}
                if patch:
                    self.state,diff,sent=self.transport.apply(self.state,patch);self.seq=seq
                emit(dict(event='state',index=self.index,seq=self.seq,state=self.state,status='divergent' if diff else 'synced',differences=diff,sent=sent))
            except Exception:
                # Never echo exception text: upstream exceptions can contain packet/config data.
                if patch:self.seq=seq
                emit(dict(event='error',index=self.index,seq=self.seq,message='Sem confirmação LAN. Verifique energia/rede e use Sincronizar.'))
                self.state=None
            self.last=time.monotonic();self.next_poll=self.last+15


def main():
    # Kill/EOF handling prevents orphan helpers even if the GUI crashes.
    parent=os.getppid()
    ctypes.CDLL(None).prctl(1,signal.SIGTERM)
    if os.getppid()!=parent:return
    signal.signal(signal.SIGTERM,lambda *_:STOP.set())
    signal.signal(signal.SIGINT,lambda *_:STOP.set())
    path=Path(os.environ.get('ELGIN_DEVICES_FILE',BASE/'devices.json')).expanduser()
    lockpath=Path(os.environ.get('XDG_RUNTIME_DIR','/tmp'))/f'elgin-smart-{os.getuid()}.lock'
    lock=open(lockpath,'w')
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:
        emit(dict(event='fatal',message='Outra instância já está conectada.'));return
    try:
        data=json.loads(path.read_text());data=data if isinstance(data,list) else data['devices']
        devices=[d for d in data if all(d.get(k) for k in ('id','key','ip','version'))]
        if not devices:raise ValueError()
    except Exception:
        emit(dict(event='fatal',message='Não foi possível carregar devices.json.'));return
    workers=[Worker(i,d) for i,d in enumerate(devices)]
    emit(dict(event='devices',devices=[dict(index=i,name=d.get('name',f'Lâmpada {i+1}'),ip=d['ip'],version=str(d['version'])) for i,d in enumerate(devices)]))
    for w in workers:w.start()
    def reader():
        try:
            for line in sys.stdin:
                if STOP.is_set():break
                try:
                    r=json.loads(line)
                    if r.get('op')=='quit':
                        DRAIN.set()
                        return
                    index=r['index']
                    if type(index)!=int or not 0<=index<len(workers):raise ValueError()
                    w=workers[index]
                    if r['op']=='set':w.submit(r['patch'],int(r['seq']))
                    elif r['op']=='refresh':
                        with w.cv:w.refresh=True;w.cv.notify()
                    else:raise ValueError()
                except Exception:emit(dict(event='invalid',message='Comando local inválido.'))
        finally:
            if not DRAIN.is_set():STOP.set()
    threading.Thread(target=reader,daemon=True).start()
    while not STOP.wait(.1):
        if DRAIN.is_set():break
    for w in workers:
        with w.cv:w.cv.notify()
    deadline=time.monotonic()+5
    for w in workers:w.join(max(0.,deadline-time.monotonic()))
    STOP.set()
    lock.close()

if __name__=='__main__':main()
