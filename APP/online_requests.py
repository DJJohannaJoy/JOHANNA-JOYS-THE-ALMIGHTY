"""One bounded request budget and durable successful probes for both adapters."""
import asyncio,hashlib,json,threading,time,uuid,os
from contextlib import contextmanager
from email.utils import parsedate_to_datetime
from pathlib import Path

class RateLimited(RuntimeError):
    def __init__(self,message,retry_after=None):
        super().__init__(message)
        self.retry_after=30. if retry_after is None else float(retry_after)

def retry_delay(value):
    try:return max(0,float(value))
    except (ValueError,TypeError):
        try:return max(0,parsedate_to_datetime(value).timestamp()-time.time())
        except (ValueError,TypeError,AttributeError):return 30.

@contextmanager
def service_state(path):
    """A short file lock shares pacing across simultaneously open app windows."""
    handle=None;locked=False;locking=False
    try:
        path.parent.mkdir(parents=True,exist_ok=True)
        handle=path.with_suffix('.lock').open('a+b')
        handle.seek(0)
        if not handle.read(1):handle.write(b' ');handle.flush()
        handle.seek(0)
        locking=True
        if os.name=='nt':
            import msvcrt
            msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        locked=True
    except OSError as exc:
        if handle:handle.close()
        if not locking:raise RuntimeError('Gemeinsame Online-Steuerung nicht schreibbar: '+str(path)) from exc
        yield None;return
    try:
        try:state=json.loads(path.read_text(encoding='utf-8'))
        except (OSError,ValueError):state={}
        original=dict(state)
        yield state
        if state!=original:
            temp=path.with_suffix('.'+uuid.uuid4().hex+'.tmp')
            temp.write_text(json.dumps(state),encoding='utf-8');temp.replace(path)
    finally:
        if locked:
            handle.seek(0)
            if os.name=='nt':msvcrt.locking(handle.fileno(),msvcrt.LK_UNLCK,1)
            else:fcntl.flock(handle.fileno(),fcntl.LOCK_UN)
        handle.close()

class RequestGate:
    def __init__(self,limit=4,interval=2.,state_path=None):
        self.limit=limit;self.interval=interval;self.base_interval=interval;self.successes=0;self.active=0;self.next_start=0.;self.lock=threading.Lock();self.waiting=[]
        self.state_path=Path(state_path) if state_path else None
        self.pause_until=0.;self.epoch=0
    def _ticket(self):
        token=object()
        with self.lock:self.waiting.append(token)
        return token
    def _discard(self,token):
        with self.lock:
            if token in self.waiting:self.waiting.remove(token)
    def _try(self,token):
        with self.lock:
            now=time.monotonic()
            if not self.waiting or self.waiting[0] is not token or self.active>=self.limit or now<self.next_start or time.time()<self.pause_until:return False
            if self.state_path:
                with service_state(self.state_path) as state:
                    if state is None:return False
                    self.pause_until=max(self.pause_until,state.get('pause_until',0))
                    if state.get('backoff_until',0)>time.time():self.interval=max(self.base_interval,state.get('interval',self.base_interval))
                    else:self.interval=self.base_interval
                    if state.get('recovery_until',0)>time.time():self.epoch=max(self.epoch,int(state.get('recovery_epoch',0)))
                    remaining=self.pause_until-time.time()
                    if remaining>0 or time.time()<state.get('next_start',0):return False
                    state['next_start']=time.time()+self.interval
            self.waiting.pop(0)
            self.active+=1;self.next_start=now+self.interval;return True
    def _notice(self,notice,last):
        if notice and self.pause_until>time.time() and time.monotonic()-last>=1:
            notice(f'Anfragelimit · automatischer Wiederholungsversuch in {max(0,self.pause_until-time.time()):.0f} s')
            return time.monotonic()
        return last
    def recover(self,error,epoch):
        with self.lock:
            if epoch<self.epoch:return True
            delay=max(0,error.retry_after)
            self.pause_until=max(self.pause_until,time.time()+delay)
            self.interval=min(12.,max(2.,self.interval*2))
            self.successes=0
            self.epoch+=1
            if self.state_path:
                with service_state(self.state_path) as state:
                    if state is not None:
                        state['pause_until']=max(state.get('pause_until',0),self.pause_until)
                        state['interval']=max(state.get('interval',0),self.interval)
                        state['successes']=0
                        state['backoff_until']=time.time()+600
                        state['recovery_epoch']=self.epoch
                        state['recovery_until']=time.time()+300
            return True
    def successful(self,epoch):
        """Gradually recover throughput after six valid replies, including no-match."""
        with self.lock:
            if epoch!=self.epoch:return
            if self.state_path:
                with service_state(self.state_path) as state:
                    if state is None or int(state.get('recovery_epoch',0))!=epoch:return
                    state['successes']=int(state.get('successes',0))+1
                    if state['successes']>=6:
                        self.interval=max(self.base_interval,float(state.get('interval',self.interval))*.75)
                        state['interval']=self.interval;state['successes']=0
            else:
                self.successes+=1
                if self.successes>=6:
                    self.interval=max(self.base_interval,self.interval*.75);self.successes=0
    def acquire(self,cancel,notice=None):
        ticket=self._ticket()
        last=0.
        try:
            while not cancel.is_set():
                if self._try(ticket):return self.epoch
                last=self._notice(notice,last)
                cancel.wait(.05)
            raise RuntimeError('Scan wurde abgebrochen.')
        finally:self._discard(ticket)
    async def async_acquire(self,cancel,notice=None):
        ticket=self._ticket()
        last=0.
        try:
            while not cancel.is_set():
                if self._try(ticket):return self.epoch
                last=self._notice(notice,last)
                await asyncio.sleep(.05)
            raise RuntimeError('Scan wurde abgebrochen.')
        finally:self._discard(ticket)
    def release(self):
        with self.lock:self.active-=1

class ShazamHTTP:
    """Single HTTP attempt: no library's hidden twenty-attempt retry loop."""
    async def __aenter__(self):
        import aiohttp
        self.session=aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20,connect=8))
        return self
    async def __aexit__(self,*args):await self.session.close()
    async def request(self,method,url,**kwargs):
        payload=kwargs.get('json')
        if isinstance(payload,dict) and 'signature' in payload and 'timestamp' in payload:
            # Fingerprints are reusable; the request time must reflect the send,
            # including time spent waiting for service recovery or other probes.
            kwargs['json']={**payload,'timestamp':int(time.time()*1000)}
        async with self.session.request(method,url,**kwargs) as response:
            if response.status==429:
                retry=response.headers.get('Retry-After','')
                raise RateLimited('Shazam: Anfragelimit (HTTP 429)'+(' · erneut nach '+retry+' s' if retry.isdigit() else ' · später erneut prüfen'),retry_delay(retry))
            response.raise_for_status()
            if response.content_type!='application/json':
                raise RuntimeError('Shazam antwortet ohne JSON: '+response.content_type)
            return await response.json()

def probe_cache(data,mix,position,adapter):
    mix=Path(mix)
    try:stat=mix.stat()
    except OSError:return None
    key=hashlib.sha256(json.dumps(('online-v1',str(mix.resolve()),stat.st_size,stat.st_mtime_ns,
                                 round(float(position),3),adapter)).encode()).hexdigest()
    return Path(data)/'Online-Proben'/(key+'.json')

def read_probe(path):
    if path is None:return None
    try:
        value=json.loads(path.read_text(encoding='utf-8'))
        return value if value.get('completed') is True else None
    except (OSError,ValueError,TypeError):return None

def save_probe(path,record):
    if path is None:return
    try:
        path.parent.mkdir(parents=True,exist_ok=True)
        temp=path.with_suffix('.'+uuid.uuid4().hex+'.tmp')
        temp.write_text(json.dumps({'completed':True,'record':record},ensure_ascii=False),encoding='utf-8')
        temp.replace(path)
    except OSError:pass
