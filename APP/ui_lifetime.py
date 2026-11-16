"""Keep Tcl resource destruction on the thread that owns the GUI.

Python's cyclic collector can run in a scan/model worker. Destroyed dialogs
leave variable/image/font cycles behind; their finalizers must not call Tcl
from whichever worker happens to collect them. Retain those resources until
the GUI thread can release them. This also covers explicit worker gc.collect().
"""
import atexit
import gc
import time
import functools
import queue
import threading
import traceback

_pending=queue.SimpleQueue()
_owner=None
_installed=False
deferred_count=0
released_count=0


def drain():
    global released_count
    if threading.get_ident()!=_owner:
        raise RuntimeError('Tcl cleanup must run on the GUI thread')
    while True:
        try:original,resource=_pending.get_nowait()
        except queue.Empty:return
        try:original(resource)
        except Exception:traceback.print_exc()
        finally:
            # Break retained cycles here too, so their final Tcl-interpreter
            # reference cannot later be dropped by a worker's collector.
            resource.__dict__.clear()
            released_count+=1


def _protect(cls):
    original=cls.__del__
    @functools.wraps(original)
    def finalize(resource):
        global deferred_count
        if threading.get_ident()==_owner:return original(resource)
        # SimpleQueue.put is reentrant in CPython, including during finalizers.
        _pending.put((original,resource));deferred_count+=1
    cls.__del__=finalize


def install(root):
    global _owner,_installed
    current=threading.get_ident()
    if _owner is not None and _owner!=current:
        raise RuntimeError('All ALMIGHTY windows must belong to the GUI thread')
    _owner=current
    if not _installed:
        import tkinter
        from tkinter.font import Font
        from PIL.ImageTk import PhotoImage
        for cls in (tkinter.Variable,tkinter.Image,Font,PhotoImage):_protect(cls)
        atexit.register(drain)
        _installed=True
    # Automatic cyclic GC otherwise runs in whichever scan thread allocates
    # the threshold object, potentially freeing cycles holding a Tcl interpreter.
    # Collect cycles only from the owning event loop while this root is alive.
    was_enabled=gc.isenabled();gc.disable()
    last=[time.monotonic(),time.monotonic()]
    job=[None]
    def tick():
        drain()
        now=time.monotonic()
        if now-last[0]>=2:
            gc.collect(2 if now-last[1]>=30 else 0);last[0]=now
            if now-last[1]>=30:last[1]=now
        job[0]=root.after(50,tick)
    def destroyed(event):
        if event.widget is not root:return
        if job[0] is not None:
            try:root.after_cancel(job[0])
            except Exception:pass
            job[0]=None
        drain()
        gc.collect()
        if was_enabled:gc.enable()
    root.bind('<Destroy>',destroyed,add='+')
    tick()
