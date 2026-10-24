import os, sqlite3, json, uuid, subprocess, tempfile, textwrap
from pathlib import Path
from datetime import date, timedelta
from flask import Flask, request, jsonify, render_template, send_from_directory, abort
from PIL import Image, ImageDraw, ImageFont, ImageOps
ROOT=Path(__file__).parent
DATA=Path(os.environ.get('LIFE_DATA',ROOT/'data')); DATA.mkdir(exist_ok=True)
app=Flask(__name__); app.config['MAX_CONTENT_LENGTH']=25*1024*1024
FONT=next((str(p) for p in [
 Path(os.environ.get('LIFE_FONT','/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')),
 Path('/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc'),
 Path('/System/Library/Fonts/ヒラギノ丸ゴ ProN W4.ttc'),
 Path('/Library/Fonts/Arial Unicode.ttf'),
] if p.is_file()),None)
if FONT is None:
 raise RuntimeError('日本語フォントが見つかりません。LIFE_FONTにフォントファイルのパスを設定してください。')
MISSIONS=[['好きな飲み物を一杯作る','お気に入りの曲を一曲聴く','窓の向こうの景色を撮る','食べたいものを一つ選ぶ','好きな映画のワンシーンを見る','部屋の好きな場所を整える','今の気持ちを一行書く','柔らかいタオルに触れる','ゆっくり深呼吸する','好きな香りを楽しむ'],['近所を10分散歩する','好きなお菓子を買いに行く','いつもと違う道を歩く','公園で5分過ごす','飲み物をテイクアウトする','書店で気になる本を探す','今日の空を撮影する','近所の花を見つける','ベンチでひと休みする','朝の空気を感じる'],['初めてのカフェに行く','友達をランチに誘う','気になる体験レッスンを探す','一人で映画館に行く','普段行かない街を散策する','興味のある展示を見に行く','新しい料理を作ってみる','図書館で知らない分野に触れる','植物を育て始める','新しい趣味を体験する']]
def db():
 c=sqlite3.connect(DATA/'life.db'); c.row_factory=sqlite3.Row; return c
with db() as c:
 c.executescript('CREATE TABLE IF NOT EXISTS journeys(mode TEXT PRIMARY KEY,title TEXT,start TEXT,message TEXT); CREATE TABLE IF NOT EXISTS entries(mode TEXT,day INTEGER,mission INTEGER,status TEXT,mood TEXT,note TEXT,media TEXT,PRIMARY KEY(mode,day));')
def mode():
 m=request.args.get('mode','normal')
 if m not in ('normal','demo'): abort(400)
 return m
def probe(p):
 return json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(p)],timeout=20))
@app.before_request
def local_only():
 if request.method not in ('GET','HEAD','OPTIONS'):
  from urllib.parse import urlparse
  origin=request.headers.get('Origin')
  if origin and urlparse(origin).netloc != request.host: abort(403)
@app.errorhandler(413)
def large(e): return jsonify(error='ファイルは25MB以下にしてください。'),413
@app.errorhandler(400)
def bad(e): return jsonify(error='入力内容を確認してください。'),400
@app.get('/')
def home(): return render_template('index.html')
@app.get('/api/state')
def state():
 m=mode()
 with db() as c:
  j=c.execute('SELECT * FROM journeys WHERE mode=?',(m,)).fetchone()
  entries=[dict(e) for e in c.execute('SELECT * FROM entries WHERE mode=? ORDER BY day',(m,))]
 return jsonify(journey=dict(j) if j else None,entries=entries,missions=MISSIONS,today=date.today().isoformat())
@app.post('/api/journey')
def journey():
 v=request.json; start=date.fromisoformat(v['start']); title=str(v.get('title','')).strip()[:80] or 'My New Chapter'
 with db() as c: c.execute('INSERT OR REPLACE INTO journeys VALUES(?,?,?,?)',(mode(),title,start.isoformat(),str(v.get('message',''))[:500]))
 return jsonify(ok=True)
@app.post('/api/entry/<int:day>')
def entry(day):
 m=mode()
 if not 1<=day<=3650: abort(400)
 v=request.form; mission=int(v.get('mission',0)); status=v.get('status','selected'); mood=v.get('mood','普通')
 if mission not in (0,1,2) or status not in ('selected','complete','rest') or mood not in ('悲しい','疲れた','普通','穏やか','楽しい'): abort(400)
 with db() as c:
  if not c.execute('SELECT 1 FROM journeys WHERE mode=?',(m,)).fetchone(): abort(400)
  old=c.execute('SELECT media FROM entries WHERE mode=? AND day=?',(m,day)).fetchone(); media=old['media'] if old else ''
  f=request.files.get('media')
  if f and f.filename:
   raw=DATA/(uuid.uuid4().hex+'.upload'); f.save(raw)
   try:
    try:
     with Image.open(raw) as im:
      if im.format not in ('JPEG','PNG','WEBP'): raise ValueError()
      im=ImageOps.exif_transpose(im); im.thumbnail((1920,1920)); media=uuid.uuid4().hex+'.jpg'; im.convert('RGB').save(DATA/media)
    except Exception:
     info=probe(raw); stream=next(s for s in info['streams'] if s['codec_type']=='video')
     if stream['width']*stream['height']>3840*2160 or not 1<=float(info['format']['duration'])<=3.2: raise ValueError()
     media=uuid.uuid4().hex+'.mp4'
     subprocess.run(['ffmpeg','-v','error','-y','-i',str(raw),'-t','3','-vf','scale=720:1280:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih)/2','-an','-c:v','libx264','-threads','2','-pix_fmt','yuv420p',str(DATA/media)],check=True,timeout=60)
   except Exception:
    abort(400)
   finally: raw.unlink(missing_ok=True)
  c.execute('INSERT OR REPLACE INTO entries VALUES(?,?,?,?,?,?,?)',(m,day,mission,status,mood,v.get('note','')[:500],media))
  if old and old['media'] and old['media']!=media: (DATA/old['media']).unlink(missing_ok=True)
 return jsonify(ok=True)
@app.post('/api/reset')
def reset():
 m=mode()
 with db() as c:
  files=[r[0] for r in c.execute('SELECT media FROM entries WHERE mode=?',(m,))]
  c.execute('DELETE FROM entries WHERE mode=?',(m,)); c.execute('DELETE FROM journeys WHERE mode=?',(m,))
 for f in files:
  if f: (DATA/f).unlink(missing_ok=True)
 for p in DATA.glob(m+'-*.mp4'): p.unlink()
 return jsonify(ok=True)
@app.post('/api/sample')
def sample():
 if mode()!='demo': abort(400)
 with db() as c:
  c.execute('INSERT OR IGNORE INTO journeys VALUES(?,?,?,?)',('demo','A little more myself',(date.today()-timedelta(days=6)).isoformat(),'自分のペースで、大丈夫。'))
  for day in range(1,8):
   media=''
   if day in (1,3,5,7):
    media=uuid.uuid4().hex+'.jpg'; im=Image.new('RGB',(720,1280),['#ded5c3','#c4cbb9','#e3c8b7','#c3ccd0'][day//2]); d=ImageDraw.Draw(im); d.ellipse((100,300,620,820),fill='#f7f0df'); d.text((90,900),'A quiet moment',font=ImageFont.truetype(FONT,42),fill='#6a584c'); im.save(DATA/media)
   c.execute('INSERT OR REPLACE INTO entries VALUES(?,?,?,?,?,?,?)',('demo',day,(day-1)%3,'rest' if day==4 else 'complete','穏やか',['少しだけ、外の空気を。','好きな曲に助けられた。','今日の光を覚えておこう。','何もしない日も大切に。','温かい一杯。','昨日とは違う景色。','ここまでの私に、ありがとう。'][day-1],media))
 return jsonify(ok=True)
def card(path,title,subtitle,note='',media=None):
 im=Image.new('RGB',(360,640),'#f4eee5'); d=ImageDraw.Draw(im)
 if media and media.suffix=='.jpg':
  with Image.open(media) as pic: im.paste(ImageOps.fit(pic,(320,340)),(20,110))
 d=ImageDraw.Draw(im)
 d.text((24,32),title[:30],font=ImageFont.truetype(FONT,22),fill='#56493f')
 d.text((24,75),subtitle,font=ImageFont.truetype(FONT,13),fill='#8d7768')
 for i,line in enumerate(textwrap.wrap(note,19)[:5]): d.text((24,480+i*24),line,font=ImageFont.truetype(FONT,16),fill='#56493f')
 im.save(path)
@app.post('/api/movie')
def movie():
 m=mode(); v=request.json or {}; start=int(v.get('start',1)); count=int(v.get('count',7))
 if start<1 or count not in (7,30) or start>3650: abort(400)
 with db() as c:
  j=c.execute('SELECT * FROM journeys WHERE mode=?',(m,)).fetchone()
  entries={e['day']:dict(e) for e in c.execute('SELECT * FROM entries WHERE mode=?',(m,))}
 if not j: abort(400)
 name=m+'-'+uuid.uuid4().hex+'.mp4'
 with tempfile.TemporaryDirectory(dir=DATA) as tmp:
  tmp=Path(tmp); clips=[]
  for i in range(count+2):
   img=tmp/f'{i}.png'; out=tmp/f'{i}.mp4'; media=None
   if i==0: card(img,j['title'],'YOUR STORY',f'{count}日間の、小さな物語。')
   elif i==count+1: card(img,'To be continued','LIFE TRANSITION',j['message'] or 'あなたのペースで、この先も。')
   else:
    day=start+i-1; e=entries.get(day,{}); media=DATA/e['media'] if e.get('media') else None
    card(img,f'Day {day}',(date.fromisoformat(j['start'])+timedelta(days=day-1)).isoformat(),e.get('note') or ('今日はお休み。' if e.get('status')=='rest' else '余白も、物語の一部。'),media)
   args=['ffmpeg','-v','error','-y','-loop','1','-i',str(img)]
   vf='fade=t=in:st=0:d=0.25,fade=t=out:st=1.75:d=0.25'
   if media and media.suffix=='.mp4':
    args+=['-stream_loop','-1','-i',str(media)]; vf='[1:v]scale=320:340:force_original_aspect_ratio=increase,crop=320:340[v];[0:v][v]overlay=20:110,fade=t=in:st=0:d=0.25,fade=t=out:st=1.75:d=0.25'
   subprocess.run(args+['-filter_complex',vf,'-t','2','-r','24','-an','-c:v','libx264','-threads','2','-preset','ultrafast','-pix_fmt','yuv420p',str(out)],check=True,timeout=45); clips.append(out)
  listing=tmp/'list.txt'; listing.write_text(''.join(f"file '{p}'\n" for p in clips))
  subprocess.run(['ffmpeg','-v','error','-y','-f','concat','-safe','0','-i',str(listing),'-c','copy','-movflags','+faststart',str(DATA/name)],check=True,timeout=30)
 return jsonify(url='/media/'+name)
@app.get('/media/<name>')
def media(name):
 if not name.endswith(('.jpg','.mp4')) or '/' in name or '..' in name: abort(404)
 return send_from_directory(DATA,name,as_attachment=request.args.get('download')=='1')
if __name__=='__main__': app.run(host='127.0.0.1',port=3000)
