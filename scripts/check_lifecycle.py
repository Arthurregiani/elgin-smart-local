"""Runs a read-only GUI session, samples idle CPU/RSS, then simulates GUI death."""
import json,os,subprocess,time
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
(BASE/'evidence').mkdir(exist_ok=True,mode=0o700)
exe=BASE/'native/target/release/elgin-smart-local'
log=open('/tmp/elgin-lifecycle-ui.log','w')
p=subprocess.Popen([str(exe)],stdout=log,stderr=log)
def children(pid):
 try:return [int(x) for x in Path(f'/proc/{pid}/task/{pid}/children').read_text().split()]
 except FileNotFoundError:return []
def sample(pid):
 try:
  text=Path(f'/proc/{pid}/stat').read_text();s=text[text.rfind(')')+2:].split()
  return dict(ticks=int(s[11])+int(s[12]),rss_kib=int(s[21])*os.sysconf('SC_PAGE_SIZE')//1024)
 except FileNotFoundError:return None
try:
 time.sleep(5)
 assert p.poll() is None,'GUI exited early'
 ids=[p.pid]+children(p.pid);start={pid:sample(pid) for pid in ids};t0=time.monotonic();time.sleep(6);elapsed=time.monotonic()-t0
 measurements=[]
 for pid in ids:
  end=sample(pid)
  if end and start[pid]:measurements.append(dict(role='GUI' if pid==p.pid else 'TinyTuya',rss_mib=round(end['rss_kib']/1024,1),cpu_one_core_percent=round((end['ticks']-start[pid]['ticks'])/os.sysconf('SC_CLK_TCK')/elapsed*100,2)))
 p.kill();p.wait(timeout=3)
 deadline=time.monotonic()+8
 while any(Path(f'/proc/{pid}').exists() and sample(pid) for pid in ids[1:]) and time.monotonic()<deadline:time.sleep(.1)
 remaining=[]
 for pid in ids[1:]:
  if Path(f'/proc/{pid}/stat').exists():
   s=Path(f'/proc/{pid}/stat').read_text();state=s[s.rfind(')')+2:].split()[0]
   if state!='Z':remaining.append(pid)
 report=dict(idle_sample_seconds=round(elapsed,2),measurements=measurements,helper_count=len(ids)-1,helpers_running_after_parent_sigkill=remaining)
 (BASE/'evidence/lifecycle.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
 assert len(ids)==2 and not remaining
finally:
 if p.poll() is None:p.kill();p.wait()
 log.close()
