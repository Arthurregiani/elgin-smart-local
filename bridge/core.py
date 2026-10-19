"""Lighting DPS only. Never changes pairing, firmware, timers or scenes."""
import math

FIELDS = {'on', 'mode', 'white', 'temperature', 'h', 's', 'v'}

def integer(value, lo, hi):
    if isinstance(value, bool) or not isinstance(value, (int,float)) or not math.isfinite(value):
        raise ValueError('Valor numérico inválido')
    if value < lo or value > hi:
        raise ValueError('Valor fora da faixa')
    return int(math.floor(value + .5))

def encode_hsv(h, s, v):
    return ''.join(f'{integer(x,0,limit):04x}' for x,limit in zip((h,s,v),(360,1000,1000)))

def decode_hsv(value):
    if not isinstance(value,str) or len(value)!=12: raise ValueError('HSV inválido')
    h,s,v = (int(value[i:i+4],16) for i in (0,4,8))
    encode_hsv(h,s,v)
    return h,s,v

def state_from_dps(dps):
    if not all(k in dps for k in ('20','21','22','23','24')):
        raise ValueError('Estado incompleto')
    h,s,v=decode_hsv(dps['24'])
    return dict(on=bool(dps['20']),mode=dps['21'],white=int(dps['22']),temperature=int(dps['23']),h=h,s=s,v=v)

def validate_patch(patch):
    if not isinstance(patch,dict) or not patch or set(patch)-FIELDS: raise ValueError('Comando inválido')
    clean={}
    for k,v in patch.items():
        if k=='on':
            if not isinstance(v,bool):raise ValueError('Liga/desliga inválido')
            clean[k]=v
        elif k=='mode':
            if v not in ('white','colour'):raise ValueError('Modo inválido')
            clean[k]=v
        else:clean[k]=integer(v,0,360 if k=='h' else 1000)
    if clean.get("white")==0:
        clean.pop("white")
        clean["on"]=False
    return clean

def command(state, patch):
    patch=validate_patch(patch)
    merged=state|patch
    dps={}
    if 'on' in patch:dps['20']=patch['on']
    if 'mode' in patch:dps['21']=patch['mode']
    if 'white' in patch:
        if patch['white']==0:
            dps['20']=False  # off is distinct from firmware minimum 10
        else:dps['22']=max(10,patch['white'])
    if 'temperature' in patch:dps['23']=patch['temperature']
    if {'h','s','v'} & patch.keys():dps['24']=encode_hsv(merged['h'],merged['s'],merged['v'])
    return dps

def differences(sent, actual):
    return {k:{'sent':v,'read':actual.get(k)} for k,v in sent.items() if actual.get(k)!=v}

class Pending:
    """Bounded coalescing: unrelated edits survive, newest value of each field wins."""
    def __init__(self):self.patch={};self.seq=0
    def put(self,patch,seq):
        clean=validate_patch(patch)
        self.patch.update(clean);self.seq=seq
    def take(self):
        p,s=self.patch,self.seq;self.patch={}
        return p,s
