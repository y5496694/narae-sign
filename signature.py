"""Narae Sign: draw a handwritten signature and save only its ink as PNG."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageDraw, ImageTk


def render_signature(strokes, canvas_size=(900, 310), pen_width=3, scale=3, padding=10):
    """Render actual user strokes on alpha, crop ink, keep antialiased edges."""
    if not strokes or not any(stroke for stroke in strokes):
        raise ValueError('먼저 서명해 주세요.')
    width, height = canvas_size
    image = Image.new('RGBA', (width * scale, height * scale), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    for stroke in strokes:
        if not stroke:
            continue
        points = [(round(max(0, min(width - 1, x)) * scale),
                   round(max(0, min(height - 1, y)) * scale)) for x, y in stroke]
        radius = pen_width * scale / 2
        if len(points) > 1:
            draw.line(points, fill=(0, 0, 0, 255), width=pen_width * scale, joint='curve')
        for x, y in (points[0], points[-1]):
            draw.ellipse((x-radius, y-radius, x+radius, y+radius), fill=(0, 0, 0, 255))
    bounds = image.getchannel('A').getbbox()
    if bounds is None:
        raise ValueError('서명 획을 확인할 수 없습니다.')
    pad = padding * scale
    bounds = (max(0, bounds[0]-pad), max(0, bounds[1]-pad),
              min(width*scale, bounds[2]+pad), min(height*scale, bounds[3]+pad))
    image = image.crop(bounds)
    return image.resize((max(1, round(image.width/scale)), max(1, round(image.height/scale))),
                        Image.Resampling.LANCZOS)


def save_signature(image, destination, receipt=None):
    destination = Path(destination).expanduser().resolve()
    if destination.suffix.lower() != '.png':
        raise ValueError('저장 형식은 PNG입니다.')
    destination.parent.mkdir(parents=True, exist_ok=True)
    handle, staged = tempfile.mkstemp(prefix='.narae-sign-', suffix='.png', dir=destination.parent)
    os.close(handle)
    try:
        image.save(staged, 'PNG', dpi=(300, 300))
        with Image.open(staged) as saved:
            saved.load()
            if saved.mode != 'RGBA' or saved.getchannel('A').getextrema()[0] != 0:
                raise ValueError('투명 배경 검증에 실패했습니다.')
        os.replace(staged, destination)
    finally:
        Path(staged).unlink(missing_ok=True)
    result = {'saved': True, 'path': str(destination), 'width': image.width, 'height': image.height,
              'transparent': True, 'sha256': hashlib.sha256(destination.read_bytes()).hexdigest(),
              'source': 'user-drawn-confirmed'}
    if receipt:
        receipt = Path(receipt).expanduser().resolve()
        if receipt == destination:
            raise ValueError('결과 JSON 경로와 PNG 경로는 달라야 합니다.')
        receipt.parent.mkdir(parents=True, exist_ok=True)
        receipt.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return result


class SignatureApp:
    WIDTH, HEIGHT = 900, 310

    def __init__(self, root, output=None, receipt=None):
        self.root, self.output, self.receipt = root, output, receipt
        self.strokes = []
        self.current = None
        self.preview = None
        root.title('나래서명')
        root.configure(bg='#f3f5f8')
        root.resizable(False, False)
        style = ttk.Style(root)
        style.theme_use('clam')
        style.configure('TButton', font=('맑은 고딕', 11), padding=(14, 10))
        frame = tk.Frame(root, bg='#f3f5f8', padx=28, pady=24)
        frame.pack()
        tk.Label(frame, text='나래서명', font=('맑은 고딕', 23, 'bold'), bg='#f3f5f8', fg='#182642').pack(anchor='w')
        tk.Label(frame, text='마우스나 펜으로 서명한 뒤 ‘확인 · PNG 저장’을 눌러 주세요.',
                 font=('맑은 고딕', 11), bg='#f3f5f8', fg='#4d5b70').pack(anchor='w', pady=(6, 18))
        self.canvas = tk.Canvas(frame, width=self.WIDTH, height=self.HEIGHT, bg='white',
                                highlightthickness=1, highlightbackground='#bac4d2', cursor='pencil')
        self.canvas.pack()
        self.canvas.bind('<ButtonPress-1>', self.start)
        self.canvas.bind('<B1-Motion>', self.move)
        self.canvas.bind('<ButtonRelease-1>', self.end)
        self.guide = self.canvas.create_text(self.WIDTH/2, self.HEIGHT/2,
                                             text='여기에 서명하세요', fill='#a4adba', font=('맑은 고딕', 18), tags='guide')
        tk.Label(frame, text='흰 배경과 안내선은 저장되지 않습니다. 서명 획만 투명 PNG로 저장합니다.',
                 font=('맑은 고딕', 10), bg='#f3f5f8', fg='#596579').pack(anchor='w', pady=(10, 14))
        buttons = tk.Frame(frame, bg='#f3f5f8')
        buttons.pack(fill='x')
        ttk.Button(buttons, text='한 획 취소', command=self.undo).pack(side='left')
        ttk.Button(buttons, text='다시 쓰기', command=self.clear).pack(side='left', padx=8)
        ttk.Button(buttons, text='확인 · PNG 저장', command=self.confirm).pack(side='right')
        ttk.Button(buttons, text='취소', command=root.destroy).pack(side='right', padx=8)
        self.status = tk.StringVar(value='서명은 이 컴퓨터에만 저장됩니다.')
        tk.Label(frame, textvariable=self.status, font=('맑은 고딕', 10), bg='#f3f5f8', fg='#596579').pack(anchor='w', pady=(14, 0))
        root.update_idletasks()
        x = max(0, (root.winfo_screenwidth()-root.winfo_width())//2)
        y = max(0, (root.winfo_screenheight()-root.winfo_height())//2)
        root.geometry(f'+{x}+{y}')
        root.lift()
        root.focus_force()

    def point(self, event):
        return max(0, min(self.WIDTH-1, event.x)), max(0, min(self.HEIGHT-1, event.y))

    def start(self, event):
        self.canvas.delete('guide')
        self.current = [self.point(event)]
        self.strokes.append(self.current)
        x, y = self.current[0]
        self.canvas.create_oval(x-1.5, y-1.5, x+1.5, y+1.5, fill='black', outline='', tags='ink')

    def move(self, event):
        if self.current is None:
            return
        previous, point = self.current[-1], self.point(event)
        self.current.append(point)
        self.canvas.create_line(*previous, *point, width=3, fill='black', capstyle='round', joinstyle='round', tags='ink')

    def end(self, event):
        self.move(event)
        self.current = None

    def redraw(self):
        self.canvas.delete('ink')
        for stroke in self.strokes:
            if len(stroke) == 1:
                x,y=stroke[0]
                self.canvas.create_oval(x-1.5,y-1.5,x+1.5,y+1.5,fill='black',outline='',tags='ink')
            else:
                self.canvas.create_line(*[v for pt in stroke for v in pt], width=3, capstyle='round', joinstyle='round', tags='ink')

    def undo(self):
        if self.strokes:
            self.strokes.pop()
        self.current = None
        self.redraw()

    def clear(self):
        self.strokes.clear()
        self.current = None
        self.redraw()

    def confirm(self):
        try:
            image = render_signature(self.strokes, (self.WIDTH, self.HEIGHT))
        except ValueError as error:
            messagebox.showinfo('나래서명', str(error), parent=self.root)
            return
        destination = self.output or filedialog.asksaveasfilename(parent=self.root, title='서명 PNG 저장',
            initialdir=str(Path('D:/Codex/signatures') if os.name=='nt' else Path.home()),
            initialfile='signature.png', defaultextension='.png', filetypes=[('투명 PNG', '*.png')])
        if not destination:
            return
        if self.output and Path(destination).exists():
            if not messagebox.askyesno('나래서명', '기존 서명 파일을 새 서명으로 바꿀까요?', parent=self.root):
                return
        if self.receipt and Path(destination).resolve()==Path(self.receipt).resolve():
            messagebox.showerror('나래서명','PNG와 결과 JSON 경로는 달라야 합니다.',parent=self.root)
            return
        try:
            result = save_signature(image, destination, self.receipt)
        except (OSError, ValueError) as error:
            messagebox.showerror('저장 실패', str(error), parent=self.root)
            return
        self.status.set(f'저장 완료: {result["path"]}')
        self.root.title('나래서명 · 저장 완료')
        messagebox.showinfo('나래서명', '서명만 남긴 투명 PNG를 저장했습니다.\n\n'+result['path'], parent=self.root)
        self.root.destroy()


def main():
    parser=argparse.ArgumentParser(description='나래서명: 사용자가 직접 쓴 서명을 투명 PNG로 저장합니다.')
    parser.add_argument('--output', type=Path, help='저장할 PNG 경로. 생략하면 저장 창 표시')
    parser.add_argument('--result', type=Path, help='확인 후 저장 결과 JSON을 기록할 경로')
    args=parser.parse_args()
    if args.output and args.output.suffix.lower()!='.png':
        parser.error('--output은 .png 경로여야 합니다.')
    if args.output and args.result and args.output.resolve()==args.result.resolve():
        parser.error('--output과 --result는 다른 경로여야 합니다.')
    if os.name=='nt':
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError, OSError):
            pass
    root=tk.Tk()
    SignatureApp(root,args.output,args.result)
    root.mainloop()


if __name__=='__main__':
    main()
