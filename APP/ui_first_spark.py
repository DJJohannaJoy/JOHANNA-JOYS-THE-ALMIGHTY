# -*- coding: utf-8 -*-
"""FIRST SPARK · genuine Tkinter controls with custom crimson skin.

No pre-rendered fake screenshot is used as an interface: every button, status,
progress widget, file input and results table below is interactive.
"""
from __future__ import annotations
import tkinter as tk
from tkinter import ttk, scrolledtext
from pathlib import Path
from PIL import Image, ImageTk, ImageDraw, ImageFilter
from functools import lru_cache
import math
import json,uuid
from ui_text import tr,VERSION_LABEL

BASE = '#090A0B'
PANEL = '#131415'
PANEL2 = '#151617'
FIELD = '#0F1011'
LINE = '#353638'
RED = '#C8001E'
HOT = '#FF1632'
RED_DARK = '#680716'
TEXT = '#F5F2F3'
MUTE = '#B7B7BB'
GOOD = '#20E66C'
BAD = '#FF1632'
CAUTION = '#E8B66A'


def _raster_panel(width, height, fill=PANEL, edge=LINE, radius=13):
    """Lightweight antialiased chrome; operational content is made of widgets."""
    k = 2
    w, h = max(8, int(width))*k, max(8, int(height))*k
    im = Image.new('RGBA', (w, h))
    draw = ImageDraw.Draw(im)
    for y in range(h):
        t = y/max(1, h-1)
        v = round(18 + 10 * math.exp(-t*8))
        draw.line((0, y, w, y), fill=(v, v+1, v+2, 255))
    mask = Image.new('L', (w, h))
    ImageDraw.Draw(mask).rounded_rectangle((2, 2, w-3, h-3), radius=radius*k, fill=255)
    im.putalpha(mask)
    draw.rounded_rectangle((2, 2, w-3, h-3), radius=radius*k,
                           outline=edge, width=k)
    draw.line((radius*k, 3, w-radius*k, 3), fill='#4B3034', width=1)
    # A restrained crimson reflection, like the upper edge in the reference.
    draw.line((int(w*.32), 2, int(w*.68), 2), fill='#94162A', width=1)
    return ImageTk.PhotoImage(im.resize((w//k, h//k), Image.Resampling.LANCZOS))


class RoundedCard(tk.Canvas):
    """Round panel perimeter, with a genuine Tk frame for input widgets."""
    def __init__(self,parent,padx,pady,desired_height=170):
        super().__init__(parent,bg=BASE,highlightthickness=0,bd=0,relief='flat',height=desired_height)
        self.inner=tk.Frame(self,bg=PANEL,padx=padx,pady=pady)
        self._win=self.create_window(7,7,window=self.inner,anchor='nw')
        self._bmp=None
        self._last=(0,0)
        self.bind('<Configure>',self._resize)
    def _resize(self,event):
        w,h=event.width,event.height
        self.itemconfigure(self._win,width=max(1,w-14),height=max(1,h-14))
        if (w,h)!=self._last and w>=30 and h>=25:
            self._bmp=_raster_panel(w,h)
            self.delete('panel_background')
            self.create_image(0,0,image=self._bmp,anchor='nw',tags='panel_background')
            self.tag_lower('panel_background')
            self._last=(w,h)


@lru_cache(maxsize=80)
def _button_art(w, h, outline, hover, disabled):
    k = 2
    W, H = max(8,w)*k, max(8,h)*k
    im = Image.new('RGBA', (W,H))
    d = ImageDraw.Draw(im)
    for y in range(H):
        t = y/max(1,H-1)
        if disabled:
            col = (45,29,32)
        elif outline:
            v = int(28-13*t) + (7 if hover else 0)
            col = (v+4,v,v+1)
        else:
            # Bright blood-red upper bevel falls into a deep black-red centre.
            v = int(95 + 123*math.exp(-t*5) + 30*t*t)
            if hover: v = min(255,v+28)
            col = (v,3+int(9*(1-t)),18+int(10*(1-t)))
        d.line((0,y,W,y),fill=(*col,255))
    mask = Image.new('L',(W,H))
    ImageDraw.Draw(mask).rounded_rectangle((2,2,W-3,H-3),radius=8*k,fill=255)
    im.putalpha(mask)
    d.rounded_rectangle((2,2,W-3,H-3),radius=8*k,
                         outline='#503037' if disabled else '#FF1231',width=k)
    if not outline and not disabled:
        d.line((18,4,W-18,4),fill='#FF5365',width=1)
    return im.resize((w,h),Image.Resampling.LANCZOS)


def _button_image(w,h,outline,hover,disabled):
    return ImageTk.PhotoImage(_button_art(w,h,outline,hover,disabled))


class BloodButton(tk.Canvas):
    """Real clickable red button with antialiased rounded rectangle and hover state."""
    def __init__(self,parent,title,command,width=175,height=43,outline_only=False,
                 font_size=11,fg=TEXT,symbol=None,**kw):
        super().__init__(parent,width=width,height=height,bg=parent.cget('bg'),
                         highlightthickness=0,bd=0,relief='flat',cursor='hand2',takefocus=1,**kw)
        self.caption=title;self.action=command;self.outline_only=outline_only
        self.font_size=font_size;self.fgcolor=fg
        self.symbol=symbol
        self.disabled=False;self.over=False;self._bmp=None;self._last=None
        self.bind('<Configure>',lambda e:self._paint())
        self.bind('<Enter>',lambda e:self._hover(True))
        self.bind('<Leave>',lambda e:self._hover(False))
        self.bind('<Button-1>',lambda e:self.focus_set())
        self.bind('<ButtonRelease-1>',self._clicked)
        self.bind('<Return>',self._keyboard)
        self.bind('<space>',self._keyboard)
        self.bind('<FocusIn>',lambda e:self._paint())
        self.bind('<FocusOut>',lambda e:self._paint())
        self._paint()
    def configure(self,cnf=None,**kw):
        if cnf and isinstance(cnf,dict):kw.update(cnf)
        if 'state' in kw:
            self.disabled=str(kw.pop('state'))=='disabled'
            self['cursor']='arrow' if self.disabled else 'hand2'
        if 'text' in kw:self.caption=kw.pop('text')
        if kw:super().configure(**kw)
        self._paint()
    config=configure
    def _hover(self,on):
        if not self.disabled:self.over=on;self._paint()
    def _clicked(self,e):
        if (not self.disabled and self.action and
                0 <= e.x < self.winfo_width() and 0 <= e.y < self.winfo_height()):
            self.action()
    def _keyboard(self,event):
        if not self.disabled and self.action:self.action()
        return 'break'
    def _paint(self):
        w=int(self.winfo_width()) if self.winfo_width()>1 else int(self.cget('width'))
        h=int(self.winfo_height()) if self.winfo_height()>1 else int(self.cget('height'))
        if w<10 or h<10:return
        image_key=(w,h,self.outline_only,self.over,self.disabled)
        if image_key!=self._last:
            self._bmp=_button_image(w,h,self.outline_only,self.over,self.disabled)
            self._last=image_key
        self.delete('all')
        self.create_image(0,0,image=self._bmp,anchor='nw')
        if self.symbol!='reset':
            self.create_text(w/2,h/2,text=tr(self,self.caption),fill='#A19AA0' if self.disabled else self.fgcolor,
                             font=('Segoe UI',self.font_size,'bold'))
        else:
            cx,cy=w/2,h/2;r=min(w,h)*.27;color=MUTE if self.disabled else TEXT
            self.create_arc(cx-r,cy-r,cx+r,cy+r,start=45,extent=285,style='arc',outline=color,width=2,tags='reset_icon')
            self.create_polygon(cx+r*.75,cy-r*.80,cx+r*.75-7,cy-r*.80+1,cx+r*.75-1,cy-r*.80+7,fill=color,outline='',tags='reset_icon')
        if self.symbol=='save':
            x,y=17,h/2-9
            self.create_rectangle(x,y,x+18,y+18,outline=self.fgcolor,width=2)
            self.create_rectangle(x+4,y,x+13,y+7,outline=self.fgcolor)
            self.create_rectangle(x+4,y+11,x+14,y+18,outline=self.fgcolor)


class Header(tk.Canvas):
    """Approved decorative brand strip, fitted without stretching the artwork."""
    def __init__(self,parent,app,source:Path):
        super().__init__(parent,bg=BASE,height=118,highlightthickness=0,bd=0,takefocus=1)
        self.app=app
        self._source=Image.open(source).convert('RGB')
        self._source=self._source.crop((0,0,self._source.width,self._source.height-4))
        self._gear_source=self._source.crop((1460,14,1543,94))
        # Reuse the gear's actual rounded red chrome at precisely the same size.
        self._book_source=self._gear_source.copy()
        pen=ImageDraw.Draw(self._book_source)
        for yy in range(12,68):
            shade=round(22-10*(yy-12)/56)
            pen.line((13,yy,70,yy),fill=(shade,shade,shade+1))
        self._language_source=self._book_source.copy()
        pen.polygon([(41,28),(32,23),(20,23),(20,55),(32,55),(41,60)],fill='#171719',outline='#E4E4E6',width=2)
        pen.polygon([(42,28),(51,23),(63,23),(63,55),(51,55),(42,60)],fill='#171719',outline='#E4E4E6',width=2)
        pen.line((41,28,41,60),fill='#A7A7AB',width=2)
        for yy in (33,41,49):
            pen.line((25,yy-2,35,yy+1),fill='#B5B5BA',width=1)
            pen.line((48,yy+1,58,yy-2),fill='#B5B5BA',width=1)
        # Remove the original edge-mounted gear from the decorative background.
        # Reuse clean matrix texture so the banner runs to both window edges.
        self._source.paste(self._source.crop((1377,0,1460,self._source.height)),(1460,0))
        self._source.paste(self._source.crop((1050,75,1365,103)).resize((315,38)),(1050,36))
        self._img=None
        self._last_width=0
        self.gear_bounds=(0,0,0,0)
        self.library_bounds=(0,0,0,0)
        self.language_bounds=(0,0,0,0)
        self.bind('<Configure>',self.redraw)
        self.bind('<ButtonRelease-1>',self.click)
        self.bind('<Motion>',self.move)
        self.bind('<Leave>',lambda event:self.configure(cursor='arrow'))
        self.bind('<Return>',lambda e:self.app.toggle_settings())
        self.bind('<space>',lambda e:self.app.toggle_settings())
        self.bind('<FocusIn>',lambda e:self._focus(True))
        self.bind('<FocusOut>',lambda e:self._focus(False))
    def _focus(self,on):
        self.delete('focus')
    def in_gear(self,event):
        x0,y0,x1,y1=self.gear_bounds
        return x0<=event.x<=x1 and y0<=event.y<=y1
    def click(self,event):
        if self.in_gear(event):
            self.focus_set()
            self.app.toggle_settings()
        elif self.in_library(event):self.app.show_library()
        elif self.in_language(event):self.app.toggle_language()
    def in_language(self,event):
        x0,y0,x1,y1=self.language_bounds
        return x0<=event.x<=x1 and y0<=event.y<=y1
    def in_library(self,event):
        x0,y0,x1,y1=self.library_bounds
        return x0<=event.x<=x1 and y0<=event.y<=y1
    def move(self,event):
        self.configure(cursor='hand2' if self.in_gear(event) or self.in_library(event) or self.in_language(event) else 'arrow')
    def redraw(self,event=None):
        w=self.winfo_width()
        if w<10 or self._last_width==w:return
        self._last_width=w
        # Full-bleed artwork, with the settings control independently inset.
        scale=w/self._source.width
        h=round(self._source.height*scale)
        self.configure(height=h)
        self.delete('all')
        art=self._source.resize((w,h),Image.Resampling.LANCZOS)
        self._rail_background=art.copy()
        gw,gh=round(self._gear_source.width*scale),round(self._gear_source.height*scale)
        gx,gy=w-40-gw,round((h-gh)/2)
        art.paste(self._gear_source.resize((gw,gh),Image.Resampling.LANCZOS),(gx,gy))
        lx=gx-gw-8
        art.paste(self._book_source.resize((gw,gh),Image.Resampling.LANCZOS),(lx,gy))
        sx=lx-gw-8
        art.paste(self._language_source.resize((gw,gh),Image.Resampling.LANCZOS),(sx,gy))
        self._img=ImageTk.PhotoImage(art)
        self.create_image(0,0,anchor='nw',image=self._img)
        self.gear_bounds=(gx,gy,gx+gw,gy+gh)
        self.library_bounds=(lx,gy,lx+gw,gy+gh)
        self.language_bounds=(sx,gy,sx+gw,gy+gh)
        active=getattr(self.app,'language',None)
        for code,y in [('de',.33),('en',.68)]:
            self.create_text(sx+gw/2,gy+gh*y,text=code.upper(),fill=HOT if active and active.code==code else TEXT,font=('Segoe UI',max(10,round(15*scale)),'bold'))
        from tkinter.font import Font
        font=Font(family='Segoe UI',size=-max(10,round(17*scale)),weight='bold')
        vx=round(1030*scale);available=sx-12-vx
        while font.measure(VERSION_LABEL)>available and abs(font.cget('size'))>8:font.configure(size=font.cget('size')+1)
        self.create_text(vx,h/2,text=VERSION_LABEL,anchor='w',fill=TEXT,font=font,tags='version')
        self.version_bounds=self.bbox('version')
        self._focus(self.focus_get()==self)
        if hasattr(self,'rail'):self.rail.draw()


class BrandRail(tk.Canvas):
    """Stepped metal rail; banner texture continues above its sloped contour."""
    def __init__(self,parent,header):
        super().__init__(parent,height=49,bg=BASE,bd=0,highlightthickness=0)
        self.header=header
        header.rail=self
        self.bind('<Configure>',self.draw)
    def draw(self,event=None):
        w,h=max(20,self.winfo_width()),49
        k=2
        art=Image.new('RGB',(w*k,h*k))
        d=ImageDraw.Draw(art)
        for y in range(h*k):
            t=y/(h*k)
            v=round(15+10*math.sin(t*math.pi))
            d.line((0,y,w*k,y),fill=(v,v+2,v+3))
        path=[(0,1),(w*.49,1),(w*.50,9),(w,9)]
        points=[(round(x*k),round(y*k)) for x,y in path]
        # The region ABOVE the lowered edge belongs to the brand background.
        # Reflect its last rows to extend the real edge texture without a seam;
        # clip the metal surface to the contour instead of filling the whole row.
        banner=getattr(self.header,'_rail_background',None)
        if banner is not None:
            tail=banner.crop((0,banner.height-h,banner.width,banner.height))
            tail=tail.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
            background=tail.resize((w*k,h*k),Image.Resampling.LANCZOS)
        else:
            background=Image.new('RGB',art.size,BASE)
        mask=Image.new('L',art.size)
        ImageDraw.Draw(mask).polygon(points+[(w*k,h*k),(0,h*k)],fill=255)
        art=Image.composite(art,background,mask)
        glow=Image.new('RGBA',art.size)
        ImageDraw.Draw(glow).line(points,fill=(255,0,35,110),width=2*k)
        glow=glow.filter(ImageFilter.GaussianBlur(2*k))
        art=art.convert('RGBA')
        art.alpha_composite(glow)
        d=ImageDraw.Draw(art)
        d.line(points,fill='#FF1833',width=2)
        d.line((0,(h-2)*k,w*k,(h-2)*k),fill='#CC1329',width=2)
        self._art=ImageTk.PhotoImage(art.resize((w,h),Image.Resampling.LANCZOS))
        self.delete('all')
        self.create_image(0,0,image=self._art,anchor='nw')


def tracked_text(canvas,text,x,y,size=29,spacing=2.7,weight='normal',color=TEXT):
    """Live canvas lettering with the reference's deliberate letter spacing."""
    from tkinter.font import Font
    font=Font(root=canvas,family='Segoe UI',size=-size,weight=weight)
    widths=[font.measure(c) for c in text]
    total=sum(widths)+spacing*(len(text)-1)
    cursor=x-total/2
    for char,width in zip(text,widths):
        canvas.create_text(cursor,y,text=char,font=font,fill=color,anchor='w')
        cursor+=width+spacing
    if not hasattr(canvas,'_letter_fonts'):canvas._letter_fonts=[]
    canvas._letter_fonts.append(font)
    canvas._letter_fonts=canvas._letter_fonts[-2:]


class GlowProgress(tk.Canvas):
    """Animated indeterminate progress showing actual busy/idle state."""
    def __init__(self,parent,**kw):
        super().__init__(parent,bg=parent.cget('bg'),highlightthickness=0,
                         height=17,bd=0,**kw)
        self.busy=False;self.phase=0;self.job=None;self.value=None
        self.bind('<Configure>',lambda e:self.draw())
    def start(self,interval=30):
        if self.busy:return
        self.value=None
        self.busy=True
        self._tick()
    def stop(self):
        self.busy=False
        if self.job:
            try:self.after_cancel(self.job)
            except tk.TclError:pass
            self.job=None
        self.draw()
    def set_progress(self,value):
        self.value=max(0.,min(1.,float(value)))
        if self.job:
            self.after_cancel(self.job)
            self.job=None
        self.draw()
    def _tick(self):
        if not self.busy:return
        self.phase=(self.phase+0.012)%1
        self.draw()
        self.job=self.after(35,self._tick)
    def draw(self):
        w=max(20,self.winfo_width());h=max(10,self.winfo_height())
        self.delete('all')
        self.create_rectangle(1,2,w-2,h-3,fill='#252627',outline='#49494B',width=1)
        if self.value is not None and self.value>0:
            end=3+(w-7)*self.value
            self.create_rectangle(3,4,end,h-5,fill=RED,outline='')
            self.create_line(3,4,end,4,fill=HOT,width=2)
        elif self.busy and self.value is None:
            length=max(70,int(w*.25))
            x=int((w+length)*self.phase)-length
            self.create_rectangle(max(3,x),4,min(w-4,x+length),h-5,
                                  fill='#C60B32',outline='')
            self.create_line(max(3,x),4,min(w-4,x+length),4,
                             fill='#FF3D56',width=2)


class StageProxy:
    """Tiny adapter for the existing scan-event API."""
    def __init__(self,strip,key,role):
        self.strip=strip
        self.key=key
        self.role=role
    def configure(self,**kw):
        if self.role=='dot':
            self.strip.states[self.key]=(kw.get('text','○'),kw.get('fg',MUTE))
        else:
            self.strip.caption_colors[self.key]=kw.get('fg',MUTE)
        self.strip.redraw()


class StageStrip(tk.Canvas):
    """Real stepper: connector line, state-driven glowing nodes and stable text."""
    def __init__(self,parent,spec):
        super().__init__(parent,bg=PANEL,highlightthickness=0,bd=0,height=76)
        self.spec=spec
        self.states={key:('◉',HOT) if i==0 else ('○',MUTE)
                     for i,(key,_) in enumerate(spec)}
        self.caption_colors={key:TEXT if i==0 else MUTE for i,(key,_) in enumerate(spec)}
        self.node_images={}
        self.percentages={key:0 for key,_ in spec}
        self.progress_labels={}
        self.skipped=set()
        self.bind('<Configure>',lambda e:self.redraw())
    def redraw(self):
        w=max(self.winfo_width(),300)
        self.delete('all')
        count=len(self.spec)
        xs=[(i+.5)*w/count for i in range(count)]
        y=19
        self.create_line(xs[0],y,xs[-1],y,fill='#68676C',width=2)
        for ix,(key,title) in enumerate(self.spec):
            x=xs[ix]
            sym,color=self.states[key]
            if sym=='✓': fill=GOOD
            elif sym=='◉': fill=HOT
            elif sym=='✕': fill=BAD
            elif sym in ('–','Ⅱ'): fill=CAUTION
            else: fill=PANEL
            art=Image.new('RGBA',(76,76))
            pen=ImageDraw.Draw(art)
            if sym=='◉':
                pen.ellipse((4,4,72,72),outline='#700016',width=3)
                pen.ellipse((12,12,64,64),fill=HOT,outline='#FF596B',width=2)
            else:
                pen.ellipse((14,14,62,62),outline=color,fill=fill,width=3)
            self.node_images[key]=ImageTk.PhotoImage(art.resize((38,38),Image.Resampling.LANCZOS))
            self.create_image(x,y,image=self.node_images[key])
            if sym=='✓':
                self.create_text(x,y,text='✓',font=('Segoe UI',11,'bold'),fill=BASE)
            elif sym=='✕':
                self.create_text(x,y,text='×',font=('Segoe UI',14,'bold'),fill=BASE)
            elif sym=='Ⅱ':self.create_text(x,y,text='Ⅱ',font=('Segoe UI',11,'bold'),fill=BASE)
            elif sym=='◉':
                pass
            self.create_text(x,38,text=tr(self,title),anchor='n',justify='center',width=(w-40)/count,
                             font=('Segoe UI',-13,'bold'),fill=self.caption_colors[key])


def label(parent,text,size=11,weight='normal',color=TEXT,bg=None,anchor='w'):
    return tk.Label(parent,text=text,bg=bg or parent.cget('bg'),fg=color,
                    font=('Segoe UI',size,weight),anchor=anchor)


class SectionHeading(tk.Canvas):
    def __init__(self,parent,text,icon='sliders',size=21):
        super().__init__(parent,bg=PANEL,height=34,bd=0,highlightthickness=0)
        self.title,self.icon,self.size=text,icon,size
        self._language_redraw=self.draw
        self.bind('<Configure>',self.draw)
    def draw(self,event=None):
        from tkinter.font import Font
        w=max(20,self.winfo_width())
        self.delete('all')
        # Small vector icons avoid missing-glyph boxes on Windows.
        x,y=15,13
        if self.icon=='chip':
            self.create_rectangle(x-7,y-7,x+7,y+7,outline=HOT,width=2)
            for v in (-5,0,5):
                for a,b,c,d in [(x+v,y-11,x+v,y-7),(x+v,y+7,x+v,y+11),
                                (x-11,y+v,x-7,y+v),(x+7,y+v,x+11,y+v)]:
                    self.create_line(a,b,c,d,fill=HOT,width=2)
        elif self.icon=='sliders':
            for i in range(3):
                yy=6+i*7
                self.create_line(4,yy,25,yy,fill=HOT,width=2)
                xx=10 if i!=1 else 20
                self.create_oval(xx-2,yy-2,xx+2,yy+2,fill=HOT,outline=HOT)
        else:
            self.create_rectangle(5,3,23,25,outline=HOT,width=2)
            for yy in (9,15,21):self.create_line(9,yy,20,yy,fill=HOT,width=1)
        f=Font(family='Segoe UI',size=-self.size,weight='bold');title=tr(self,self.title)
        while f.measure(title)>w-52 and abs(f.cget('size'))>13:
            f.configure(size=f.cget('size')+1)
        self.create_text(42,12,text=title,anchor='w',font=f,fill=TEXT,tags='title')
        self.create_line(0,32,w,32,fill=LINE)


def section(parent,text,icon='sliders',size=21):
    heading=SectionHeading(parent,text,icon,size)
    heading.pack(fill='x',pady=(0,9))
    return heading


def field_icon(parent,kind):
    c=tk.Canvas(parent,width=30,height=32,bg=FIELD,bd=0,highlightthickness=0)
    c.pack(side='left',padx=(9,3))
    if kind=='folder':
        c.create_line(3,11,3,25,26,25,26,10,14,10,11,7,3,7,3,11,
                      fill='#C5C5C6',width=2)
    else:
        c.create_rectangle(3,9,26,25,outline=MUTE,width=1)
        c.create_polygon(12,12,12,22,20,17,fill=MUTE)
    return c


def placeholder(entry,var,message):
    """View-only prompt that disappears immediately on typing."""
    hint=tk.Label(entry.master,text=message,bg=FIELD,fg='#77737E',
                  font=('Segoe UI',10),anchor='w',cursor='xterm')
    def show(*_):
        if var.get() or entry.focus_get()==entry:hint.place_forget()
        else:hint.place(x=42,y=3,relheight=.78)
    hint.bind('<Button-1>',lambda e:(hint.place_forget(),entry.focus_set()))
    entry.bind('<FocusIn>',lambda e:hint.place_forget(),add='+')
    entry.bind('<FocusOut>',show,add='+')
    var.trace_add('write',show)
    entry.after_idle(show)



def card(parent,padx=14,pady=10,desired_height=170):
    holder=RoundedCard(parent,padx,pady,desired_height)
    return holder,holder.inner

def resizable_columns(table,app,view,on_change):
    """Keep native heading drags, refresh clipped text and remember each view's widths."""
    target=app.C_DATA/'spaltenbreiten.json';job=[None];drag=[False];pending_save=[False]
    def read():
        try:
            value=json.loads(target.read_text(encoding='utf-8'))
            return value if isinstance(value,dict) else {}
        except (OSError,ValueError):return {}
    stored=read().get(view,{})
    if isinstance(stored,dict) and stored:
        for key in table['columns']:
            width=stored.get(key)
            if isinstance(width,int) and 30<=width<=4096:table.column(key,width=width,stretch=False)
    def update(save=False):
        pending_save[0]=pending_save[0] or save
        if job[0] is not None:table.after_cancel(job[0])
        def finish():
            job[0]=None
            if not table.winfo_exists():return
            if pending_save[0]:
                pending_save[0]=False
                data=read();data[view]={key:table.column(key,'width') for key in table['columns']}
                temporary=target.with_suffix('.'+uuid.uuid4().hex+'.tmp')
                try:
                    target.parent.mkdir(parents=True,exist_ok=True)
                    temporary.write_text(json.dumps(data,indent=2),encoding='utf-8');temporary.replace(target)
                except OSError:pass
            on_change()
        job[0]=table.after(70,finish)
    def press(event):
        drag[0]=table.identify_region(event.x,event.y)=='separator'
        if drag[0]:
            for key in table['columns']:table.column(key,stretch=False)
    def release(event):
        if drag[0]:drag[0]=False;update(save=True)
    def destroy(event):
        if event.widget==table and job[0] is not None:table.after_cancel(job[0]);job[0]=None
    table.bind('<ButtonPress-1>',press,add='+')
    table.bind('<B1-Motion>',lambda event:update() if drag[0] else None,add='+')
    table.bind('<ButtonRelease-1>',release,add='+')
    table.bind('<Configure>',lambda event:update(),add='+')
    table.bind('<Destroy>',destroy,add='+')


def build_ui(a):
    """Construct the approved three-column/header + full-width scanner UI."""
    root=a.root
    root.configure(bg=BASE)
    root.title("Johanna Joy's THE ALMIGHTY · "+VERSION_LABEL)
    a._app_icon=ImageTk.PhotoImage(Image.open(a.C_APP/'assets/almighty_icon.png'))
    root.iconphoto(True,a._app_icon)
    if __import__('os').name=='nt':
        root.iconbitmap(str(a.C_APP/'assets/almighty_icon.ico'))
        root.iconbitmap(default=str(a.C_APP/'assets/almighty_icon.ico'))
    root.geometry('1570x990+20+0')
    root.minsize(1250,980)
    root.columnconfigure(0,weight=1)
    root.rowconfigure(2,weight=1)

    header=Header(root,a,a.C_APP/'assets'/'approved_banner.png')
    a.header=header
    header.grid(row=0,column=0,sticky='ew')
    BrandRail(root,header).grid(row=1,column=0,sticky='ew')

    body=tk.Frame(root,bg=BASE,padx=16,pady=12)
    body.grid(row=2,column=0,sticky='nsew')
    body.columnconfigure(0,weight=1)
    body.rowconfigure(2,weight=1,minsize=265)
    body.rowconfigure(0,minsize=231)

    top=tk.Frame(body,bg=BASE)
    top.grid(row=0,column=0,sticky='nsew',pady=(0,10))
    top.columnconfigure(0,weight=52,uniform='toparea')
    top.columnconfigure(1,weight=25,uniform='toparea')
    top.columnconfigure(2,weight=22,uniform='toparea')
    top.rowconfigure(0,weight=1)

    upload_wrap,upload=card(top,9,7,desired_height=231)
    upload_wrap.grid(row=0,column=0,sticky='nsew',padx=(0,10))
    upload.columnconfigure(0,weight=1)
    upload.rowconfigure(0,weight=1)

    # The drop zone is a functional, animated-focus Canvas, not a static picture.
    drop=tk.Canvas(upload,height=113,bg='#141213',highlightthickness=0,bd=0,cursor='hand2')
    drop.grid(row=0,column=0,sticky='nsew',pady=(0,12))
    texture_left=Image.open(a.C_APP/'assets/drop_texture_left.png').convert('RGB')
    texture_right=Image.open(a.C_APP/'assets/drop_texture_right.png').convert('RGB')
    def paint_drop(event=None):
        w,h=max(drop.winfo_width(),20),max(drop.winfo_height(),20)
        drop.delete('all')
        texture=Image.effect_noise((w,h),9).point(lambda v: 12+v//24).convert('RGB')
        for patch,right_side in ((texture_left,False),(texture_right,True)):
            pw=round(patch.width*h/patch.height)
            pw=min(pw,w//2)
            art=patch.resize((pw,h),Image.Resampling.LANCZOS)
            mask=Image.new('L',(pw,h))
            md=ImageDraw.Draw(mask)
            for x in range(pw):
                edge=x if right_side else pw-1-x
                opacity=min(255,round(255*edge/max(1,pw*.28)))
                md.line((x,0,x,h),fill=opacity)
            texture.paste(art,(w-pw if right_side else 0,0),mask)
        # Dashed rounded crimson perimeter at double resolution for smooth corners.
        border=Image.new('RGBA',(w*2,h*2))
        pen=ImageDraw.Draw(border)
        for x in range(14,w-14,12):
            for y in (4,h-5):pen.line((x*2,y*2,min(w-14,x+7)*2,y*2),fill='#FF102C',width=3)
        for y in range(15,h-15,12):
            for x in (4,w-5):pen.line((x*2,y*2,x*2,min(h-15,y+7)*2),fill='#FF102C',width=3)
        for box,angles in [((4,4,24,24),(180,270)),((w-25,4,w-5,24),(270,360)),
                           ((4,h-25,24,h-5),(90,180)),((w-25,h-25,w-5,h-5),(0,90))]:
            pen.arc(tuple(v*2 for v in box),*angles,fill='#FF102C',width=3)
        texture=texture.convert('RGBA')
        texture.alpha_composite(border.resize((w,h),Image.Resampling.LANCZOS))
        drop._art=ImageTk.PhotoImage(texture)
        drop.create_image(0,0,image=drop._art,anchor='nw')
        tracked_text(drop,tr(drop,'HIER REINZIEHEN'),w/2,h/2-15,size=29,spacing=2.7,weight='bold')
        tracked_text(drop,'MP3  ·  WAV  ·  FLAC  ·  AIFF  ·  VIDEO',w/2,h/2+25,
                     size=15,spacing=.8,color=MUTE)
    drop.bind('<Configure>',paint_drop)
    drop._language_redraw=paint_drop
    drop.bind('<ButtonRelease-1>',lambda e:a.pick_set())
    if a.DND_OK:
        drop.drop_target_register(a.DND_FILES)
        drop.dnd_bind('<<Drop>>',a._dropped)

    form=tk.Frame(upload,bg=PANEL)
    form.grid(row=1,column=0,sticky='ew',pady=(0,10))
    form.grid_columnconfigure(0,weight=1)
    filebox=tk.Frame(form,bg=FIELD,highlightthickness=1,highlightbackground='#51505A')
    filebox.grid(row=0,column=0,sticky='nsew')
    field_icon(filebox,'folder')
    fentry=a._entry(filebox,a.set_path)
    fentry.configure(font=('Segoe UI',11),bg=FIELD,highlightthickness=0)
    fentry.pack(side='left',fill='both',expand=True,ipady=8)
    placeholder(fentry,a.set_path,'Noch kein Set ausgewählt')
    browse=BloodButton(form,'DURCHSUCHEN',a.pick_set,width=198,height=41,font_size=13)
    browse.grid(row=0,column=1,sticky='nsew',padx=(13,0))

    links=tk.Frame(upload,bg=PANEL)
    links.grid(row=2,column=0,sticky='ew')
    links.grid_columnconfigure(0,weight=1)
    linkbox=tk.Frame(links,bg=FIELD,highlightthickness=1,highlightbackground='#51505A')
    linkbox.grid(row=0,column=0,sticky='nsew')
    field_icon(linkbox,'play')
    lentry=a._entry(linkbox,a.media_url)
    lentry.configure(font=('Segoe UI',11),bg=FIELD,highlightthickness=0)
    lentry.pack(side='left',fill='both',expand=True,ipady=8)
    placeholder(lentry,a.media_url,'YOUTUBE / SOUNDCLOUD / MIXCLOUD')
    load=BloodButton(links,'LINK LADEN',a.start_download,width=198,height=41,font_size=13)
    load.grid(row=0,column=1,sticky='nsew',padx=(13,0))
    a.file_button=browse
    a.link_button=load

    right_wrap,right=card(top,10,5,desired_height=231)
    right_wrap.grid(row=0,column=1,sticky='nsew',padx=(0,10))
    section(right,'VORAUSSETZUNGEN')
    a.statuses={}
    a.status_actions={}
    captions=[('ffmpeg','FFmpeg','EINRICHTEN'),('db','Musikdatenbank','ANLEGEN'),
              ('offline','Offline-Engine','EINRICHTEN'),('mixid','mix-id','EINRICHTEN'),
              ('shazam','ShazamIO','EINRICHTEN')]
    for key,desc,fixcaption in captions:
        row=tk.Frame(right,bg=PANEL,height=30)
        row.pack(fill='x',pady=(0,1))
        row.pack_propagate(False)
        row.grid_columnconfigure(1,weight=1)
        sym=label(row,'○',16,'bold',MUTE)
        sym.grid(row=0,column=0,sticky='w',padx=(1,7))
        label(row,desc,11,'normal').grid(row=0,column=1,sticky='w')
        stat=label(row,'Prüfe …',10,'bold',MUTE)
        stat.grid(row=0,column=2,sticky='e',padx=(5,0))
        fix=BloodButton(row,fixcaption,lambda k=key:a.fix_prerequisite(k),
                        width=108,height=27,outline_only=True,font_size=9)
        fix.grid(row=0,column=3,padx=(7,0))
        fix.grid_remove()
        tk.Frame(right,bg=LINE,height=1).pack(fill='x')
        a.statuses[key]=(sym,stat)
        a.status_actions[key]=fix

    ai_wrap,ai=card(top,11,5,desired_height=231)
    ai_wrap.grid(row=0,column=2,sticky='nsew')
    section(ai,'LOKALE KI — OPTIONAL',icon='chip',size=20)
    import local_ai
    installed=local_ai.find_lmstudio(a.cfg)
    BloodButton(ai,'LM STUDIO ÖFFNEN' if installed else 'LM STUDIO ZUWEISEN',a.open_local_ai,height=42,
                outline_only=True,font_size=11).pack(fill='x',pady=(3,6))
    BloodButton(ai,'MODELL / VERBINDUNG',a.configure_local_ai,height=42,
                outline_only=True,font_size=11).pack(fill='x',pady=(3,6))
    BloodButton(ai,'KI-NACHPRÜFUNG',a.show_ai_findings,height=42,
                outline_only=True,font_size=11).pack(fill='x',pady=(3,5))
    a.ai_status_text=tk.StringVar(value='LM Studio erkannt · Modell wird geprüft' if installed else 'Optional · LM Studio zuweisen')
    tk.Label(ai,textvariable=a.ai_status_text,bg=PANEL,fg=MUTE,
             font=('Segoe UI',8),wraplength=260,height=1,anchor='w',justify='left').pack(fill='x')

    # A row spanning all columns makes scanning a single, easy-to-follow path.
    flow_wrap,flow=card(body,18,5,desired_height=160)
    flow_wrap.grid(row=1,column=0,sticky='nsew',pady=(0,10))
    flow.columnconfigure(0,weight=66,uniform='scan')
    flow.columnconfigure(1,weight=34,uniform='scan')
    flowhead=tk.Frame(flow,bg=PANEL);flowhead.grid(row=0,column=0,sticky='ew')
    label(flowhead,'ABLAUF',14,'bold').pack(side='left')
    nodes=tk.Frame(flow,bg=PANEL)
    nodes.grid(row=1,column=0,sticky='new',padx=(0,20))
    stagespec=[('setup','DATEIEN\nVORBEREITEN'),('A','SCHNELLSCAN'),
               ('B','TIEFENSCAN 1'),('M','TIEFENSCAN 2'),
               ('S','SHAZAM'),('KI','KI-PRÜFUNG'),('E','ERGEBNIS')]
    stagebar=StageStrip(nodes,stagespec)
    a.stagebar=stagebar
    stagebar.pack(fill='x')
    a.stages={key:(StageProxy(stagebar,key,'dot'),StageProxy(stagebar,key,'caption'))
              for key,_ in stagespec}
    actions=tk.Frame(flow,bg=PANEL);actions.grid(row=0,column=1,rowspan=2,sticky='new',padx=(12,12))
    actions.columnconfigure(0,weight=1,uniform='actions');actions.columnconfigure(1,weight=0,minsize=50);actions.columnconfigure(2,weight=1,uniform='actions')
    a.save_button=BloodButton(actions,'SPEICHERN',a.save_current_set,height=36,font_size=10,outline_only=True,symbol='save')
    a.save_button.grid(row=0,column=0,sticky='ew',padx=(0,4))
    a.reset_button=BloodButton(actions,'',a.reset_set,width=48,height=36,font_size=22,outline_only=True,symbol='reset')
    a.reset_button.grid(row=0,column=1,sticky='ew',padx=2)
    a.retry_button=BloodButton(actions,'ERNEUT PRÜFEN',a.show_retry_methods,height=36,font_size=10,outline_only=True)
    a.retry_button.grid(row=0,column=2,sticky='ew',padx=(4,0))
    primary=tk.Frame(actions,bg=PANEL)
    primary.grid(row=1,column=0,columnspan=3,sticky='ew',pady=(8,0))
    primary.columnconfigure(0,weight=3,uniform='primary')
    primary.columnconfigure(1,weight=0,minsize=8)
    primary.columnconfigure(2,weight=2,uniform='primary')
    a.start_button=BloodButton(primary,'SCANNEN',a.start_scan,width=3,height=64,font_size=23)
    a.start_button.grid(row=0,column=0,sticky='ew')
    a.rekordbox_button=BloodButton(primary,'REKORDBOX-EXPORT',a.show_rekordbox_export,width=2,height=64,outline_only=True,font_size=10)
    a.rekordbox_button.grid(row=0,column=2,sticky='ew')
    a.timeline_nodes={}

    hits_wrap,hits=card(body,4,4,desired_height=190)
    hits_wrap.grid(row=2,column=0,sticky='nsew',pady=(0,10))
    hithead=tk.Frame(hits,bg=PANEL)
    hithead.pack(fill='x',padx=7,pady=(0,4))
    a.result_heading=label(hithead,'ERGEBNIS',14,'bold');a.result_heading.pack(side='left')
    a.large_results_button=BloodButton(hithead,'GROSS ANZEIGEN',a.show_results,width=170,height=26,outline_only=True,font_size=9)
    a.large_results_button.pack(side='right',padx=(8,0))
    a.ai_findings_button=BloodButton(hithead,'KI-BEFUNDE',a.show_ai_findings,width=125,height=26,outline_only=True,font_size=9)
    a.ai_findings_button.pack(side='right',padx=(8,0))
    a.stop_button=BloodButton(hithead,'ABBRECHEN',a.stop,width=105,height=31,
                              outline_only=True,font_size=9)
    # Only show cancellation while actually scanning, to match the clean UI.
    a.stop_button.configure(state='disabled')

    style=ttk.Style(root)
    if 'clam' in style.theme_names(): style.theme_use('clam')
    style.configure('Almighty.Treeview',background='#101112',foreground=TEXT,
                    fieldbackground='#101112',borderwidth=0,rowheight=30,lightcolor=LINE,darkcolor=LINE,
                    bordercolor=LINE,relief='flat',font=('Segoe UI',10))
    style.configure('Almighty.Treeview.Heading',background='#252627',foreground=TEXT,
                    relief='flat',borderwidth=0,font=('Segoe UI',10,'bold'))
    style.map('Almighty.Treeview',background=[('selected','#812031')],
              foreground=[('selected',TEXT)])
    a.result_table=ttk.Treeview(hits,columns=('number','time','title','format','bpm','method','source'),
                                show='headings',style='Almighty.Treeview',height=6)
    for key,name,width,stretch in [('number','NR.',45,False),('time','ZEIT',90,False),('title','TITEL',380,True),
            ('format','FORMAT',75,False),('bpm','BPM',80,False),('method','METHODE',215,False),('source','QUELLE',245,False)]:
        a.result_table.heading(key,text=name,anchor='center' if key in {'number','time','format','bpm'} else 'w')
        a.result_table.column(key,width=width,minwidth=45 if key=='number' else 60,stretch=stretch,
                              anchor='center' if key in {'number','time','format','bpm'} else 'w')
    table_scroll=ttk.Scrollbar(hits,orient='horizontal',command=a.result_table.xview)
    table_scroll.pack(side='bottom',fill='x')
    a.result_table.configure(xscrollcommand=table_scroll.set)
    a.result_table.pack(fill='both',expand=True)
    a.result_table.bind('<Double-1>',a.show_hit_detail)
    resizable_columns(a.result_table,a,'results',lambda:a._render_hits([]) if getattr(a,'_hit_rows',None) else None)
    # Empty rows are visual grid guides, never fabricated recognitions;
    # scanner._render_hits clears them before showing actual results.
    a.result_table.tag_configure('empty0',background='#101112')
    a.result_table.tag_configure('empty1',background='#151617')
    for i in range(6):a.result_table.insert('','end',values=('','','','','','',''),tags=('empty'+str(i%2),))

    foot_wrap,foot=card(body,12,4,desired_height=114)
    foot_wrap.grid(row=3,column=0,sticky='ew')
    foothead=tk.Frame(foot,bg=PANEL);foothead.pack(fill='x',pady=(0,4))
    foot_header=label(foothead,'FORTSCHRITT',13,'bold');foot_header.pack(side='left')
    a.progress_toggle=BloodButton(foothead,'METHODEN / SCHNIPSEL',lambda:toggle_progress(),width=205,height=26,outline_only=True,font_size=9)
    a.progress_toggle.pack(side='right')
    a.ai_live_label=tk.Label(foothead,text='',bg=PANEL,fg=MUTE,font=('Segoe UI',9),anchor='w',width=1)
    a.ai_live_label.pack(side='left',fill='x',expand=True,padx=12)
    row=tk.Frame(foot,bg=PANEL)
    row.pack(fill='x')
    row.columnconfigure(0,weight=1,uniform='totals');row.columnconfigure(1,weight=1,uniform='totals')
    style.configure('Spark.Horizontal.TProgressbar',troughcolor='#383A42',
                    background=HOT,lightcolor=HOT,darkcolor=RED_DARK,
                    thickness=12,borderwidth=0)
    from ui_workspace import ProgressPanel,NamedProgress,NAMES
    a.progressbar=NamedProgress(row);a.progressbar.caption='GESAMT · 0 %'
    a.progressbar.configure(height=26)
    a.progressbar.grid(row=0,column=0,sticky='ew',padx=(0,6))
    a.progress=tk.StringVar(value='Bereit für den ersten Scan')
    a.overall_percent=tk.StringVar(value='0 %')
    a.metadata_progress=NamedProgress(row);a.metadata_progress.configure(height=26)
    a.metadata_progress.grid(row=0,column=1,sticky='ew',padx=(6,0))
    a.metadata_caption=tk.StringVar(value='Format / BPM · 0/0 · 0 %')
    a.metadata_progress.caption=a.metadata_caption.get()
    methods=tk.Frame(foot,bg=PANEL);methods.pack(fill='x',pady=(4,0))
    a.method_progress={}
    for i,(key,title) in enumerate(NAMES.items()):
        methods.columnconfigure(i,weight=1,uniform='methods')
        bar=NamedProgress(methods);bar.caption=title+' · 0 %';bar.configure(height=26)
        bar.grid(row=0,column=i,sticky='ew',padx=(0,5) if i<6 else (0,0));a.method_progress[key]=bar
        if key=='KI':bar.bind('<ButtonRelease-1>',lambda e:a.show_ai_findings());bar.configure(cursor='hand2')
    a.progress_panel=ProgressPanel(foot,a);a.progress_panel.frame.pack_forget()
    def sync_totals(*args):
        a.progressbar.caption=tr(a.progressbar,'GESAMT')+' · '+a.overall_percent.get();a.progressbar.draw()
        a.metadata_progress.caption=tr(a.metadata_progress,a.metadata_caption.get());a.metadata_progress.draw()
    a.metadata_caption.trace_add('write',sync_totals);a.overall_percent.trace_add('write',sync_totals)
    sync_totals()
    def toggle_progress():
        a.show_progress_details()
    a.toggle_progress_details=toggle_progress
    a.logbox=scrolledtext.ScrolledText(foot,height=2,wrap='word',bg='#0E1013',fg='#CFCBD0',
                                       insertbackground=TEXT,relief='flat',font=('Consolas',9))
    # Keep the diagnostic log available on click, but avoid a permanent
    # distracting empty textbox not present in the approved design.
    a.logbox.configure(state='disabled')
    def toggle_log(event=None):
        existing=getattr(a,'log_window',None)
        if existing is not None and existing.winfo_exists():existing.destroy();return
        from ui_workspace import shell
        a.log_window=shell(a,'Protokoll','1000x650')
        log_window=a.log_window
        text=scrolledtext.ScrolledText(log_window,bg=FIELD,fg=TEXT,font=('Consolas',10),wrap='word',relief='flat')
        text.pack(fill='both',expand=True,padx=20,pady=(0,20));text.configure(state='disabled')
        def update_log():
            if not log_window.winfo_exists():return
            value=a.logbox.get('1.0','end-1c')
            if value!=getattr(text,'_last_value',None):
                text.configure(state='normal');text.delete('1.0','end');text.insert('1.0',value);text.configure(state='disabled');text.see('end');text._last_value=value
            log_window.after(500,update_log)
        update_log()
    foot_header.configure(cursor='hand2')
    foot_header.bind('<Button-1>',toggle_log)

    a._build_settings()


def show_completion(app,message,context=None):
    """A real completion dialog using the same artwork and controls as the app."""
    import os
    previous=getattr(app,'completion_dialog',None)
    if previous is not None and previous.winfo_exists():previous.destroy()
    dialog=tk.Toplevel(app.root);app.completion_dialog=dialog
    dialog.title("THE ALMIGHTY · Ergebnis" if context else "THE ALMIGHTY · Abgeschlossen")
    dialog.configure(bg=HOT);dialog.transient(app.root);dialog.resizable(False,False)
    errors=context.get('errors',[]) if context else []
    width=860;height=800 if errors else 710 if context else 420
    app.root.update_idletasks()
    x=app.root.winfo_rootx()+max(0,(app.root.winfo_width()-width)//2)
    y=app.root.winfo_rooty()+max(0,(app.root.winfo_height()-height)//2)
    dialog.geometry(f'{width}x{height}{x:+d}{y:+d}')
    shell=tk.Frame(dialog,bg=BASE);shell.pack(fill='both',expand=True,padx=1,pady=1)
    banner=tk.Canvas(shell,bg=BASE,height=66,highlightthickness=0,bd=0);banner.pack(fill='x')
    art=app.header._source.crop((0,0,1390,104))
    dialog._completion_banner=ImageTk.PhotoImage(art.resize((width-2,64),Image.Resampling.LANCZOS))
    banner.create_image(0,0,anchor='nw',image=dialog._completion_banner)
    banner.create_text(round(1030*(width-2)/1390),32,text=VERSION_LABEL,anchor='w',fill=TEXT,font=('Segoe UI',10,'bold'))
    banner.create_line(0,65,width,65,fill=HOT)
    footer=tk.Frame(shell,bg=BASE,padx=26,pady=20);footer.pack(side='bottom',fill='x')
    body=tk.Frame(shell,bg=BASE,padx=26,pady=20);body.pack(fill='both',expand=True)
    label(body,'ERGEBNIS GESPEICHERT' if context else 'VORGANG ABGESCHLOSSEN',17,'bold').pack(anchor='w')
    def close():
        if dialog.grab_current()==dialog:dialog.grab_release()
        dialog.destroy()
    def retry():close();app.show_retry_methods()
    actions=[]
    if context:
        count=len(app.current_hits)
        headline=tk.Frame(body,bg=BASE);headline.pack(fill='x',pady=(14,3))
        label(headline,str(count),46,'bold',HOT,bg=BASE).pack(side='left')
        label(headline,'ERKANNTE\nTRACKS',14,'bold',bg=BASE).pack(side='left',padx=(18,0))
        label(body,'Nummeriert · chronologisch sortiert · gemeinsame Tracklist',10,color=MUTE,bg=BASE).pack(anchor='w')
        metrics=tk.Frame(body,bg=BASE);metrics.pack(fill='x',pady=(18,16))
        results=context.get('results',{})
        for i,(name,key,caption) in enumerate([('OFFLINE','offline','Trefferkandidaten'),
                ('TIEFENSCAN 2','mixid','Beobachtungen'),('SHAZAM','shazam','Beobachtungen')]):
            metrics.columnconfigure(i,weight=1,uniform='metric')
            box=tk.Frame(metrics,bg=PANEL2,highlightthickness=1,highlightbackground=LINE,padx=14,pady=10)
            box.grid(row=0,column=i,sticky='nsew',padx=(0,10 if i<2 else 0))
            label(box,name,10,'bold',MUTE).pack(anchor='w')
            label(box,str(len(results.get(key,[]))),26,'bold').pack(anchor='w')
            label(box,caption,9,color=MUTE).pack(anchor='w')
        status=tk.Frame(body,bg=PANEL2,highlightthickness=1,highlightbackground=RED_DARK if errors else LINE,padx=14,pady=10)
        status.pack(fill='x',pady=(0,16))
        label(status,'MIT HINWEISEN BEENDET' if errors else 'SCAN ERFOLGREICH BEENDET',11,'bold',HOT if errors else GOOD).pack(anchor='w')
        if errors:
            detail_wrap=tk.Frame(status,bg=PANEL2);detail_wrap.pack(fill='x',pady=(7,0))
            details=tk.Text(detail_wrap,height=4,wrap='word',font=('Segoe UI',10),
                bg=PANEL2,fg=MUTE,relief='flat',bd=0,highlightthickness=0)
            style=ttk.Style(dialog)
            style.configure('Completion.Vertical.TScrollbar',background=PANEL2,troughcolor=BASE,
                bordercolor=LINE,lightcolor=PANEL2,darkcolor=PANEL2,arrowcolor=MUTE,arrowsize=12)
            style.map('Completion.Vertical.TScrollbar',background=[('active',RED_DARK)])
            scroll=ttk.Scrollbar(detail_wrap,orient='vertical',command=details.yview,style='Completion.Vertical.TScrollbar')
            scroll.pack(side='right',fill='y',padx=(8,0));details.pack(side='left',fill='both',expand=True)
            details.configure(yscrollcommand=scroll.set)
            details.insert('1.0','\n\n'.join(str(e) for e in errors));details.configure(state='disabled')
        else:label(status,'Deine Tracklist ist gespeichert und bereit.',10,color=MUTE).pack(anchor='w',pady=(4,0))
        report=Path(context['report'])
        label(body,'ERGEBNISDATEI',9,'bold',MUTE,bg=BASE).pack(anchor='w')
        tk.Label(body,text=report.name,bg=BASE,fg=TEXT,font=('Segoe UI',10,'bold'),
                 wraplength=width-60,anchor='w',justify='left').pack(fill='x',pady=(5,3))
        tk.Label(body,text=str(report.parent),bg=BASE,fg=MUTE,font=('Segoe UI',9),
                 wraplength=width-60,anchor='w',justify='left').pack(fill='x')
        actions=[('ERGEBNIS ÖFFNEN',lambda:os.startfile(report),False),
                 ('ORDNER ÖFFNEN',lambda:app._open(report.parent),True),('ERNEUT PRÜFEN',retry,True)]
    else:
        tk.Label(body,text=message,bg=BASE,fg=TEXT,font=('Segoe UI',12),wraplength=width-70,
                 justify='left',anchor='nw').pack(fill='both',expand=True,pady=(20,0))
    actions.append(('SCHLIESSEN',close,True))
    for i,(text,command,outline) in enumerate(actions):
        footer.columnconfigure(i,weight=1)
        button=BloodButton(footer,text,command,width=190 if len(actions)>1 else 150,height=43,
                           outline_only=outline,font_size=10)
        button.grid(row=0,column=i,sticky='ew',padx=(0,9 if i<len(actions)-1 else 0))
        if text=='SCHLIESSEN':dialog.after_idle(button.focus_set)
    dialog.protocol('WM_DELETE_WINDOW',close);dialog.bind('<Escape>',lambda e:close())
    dialog.grab_set()
    return dialog
