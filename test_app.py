import os, tempfile, unittest, io, subprocess, json
sandbox=tempfile.TemporaryDirectory();os.environ['LIFE_DATA']=sandbox.name
from app import app, DATA, MISSIONS
from PIL import Image
class Workflow(unittest.TestCase):
 def test_full_journey(self):
  c=app.test_client()
  self.assertEqual(c.get('/').status_code,200)
  self.assertIsNone(c.get('/api/state').json['journey'])
  self.assertEqual(c.post('/api/journey',json={'start':'2026-10-01','title':'My chapter','message':'ゆっくりでいい'}).status_code,200)
  for level in MISSIONS: self.assertEqual(len(level),len(set(level)))
  self.assertEqual(c.post('/api/entry/1',data={'mission':2,'status':'selected'}).status_code,200)
  im=io.BytesIO();Image.new('RGB',(320,480),'pink').save(im,'PNG');im.seek(0)
  self.assertEqual(c.post('/api/entry/1',data={'mission':0,'status':'complete','note':'温かい一杯','mood':'穏やか','media':(im,'photo.png')}).status_code,200)
  self.assertEqual(c.post('/api/entry/2',data={'status':'rest'}).status_code,200)
  vid=DATA/'test.mp4'
  subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=green:s=180x320:d=1.5','-c:v','libx264','-threads','2','-pix_fmt','yuv420p',str(vid)],check=True)
  with vid.open('rb') as f: self.assertEqual(c.post('/api/entry/3',data={'status':'complete','media':(f,'clip.mp4')}).status_code,200)
  self.assertEqual(len(c.get('/api/state').json['entries']),3)
  self.assertEqual(c.post('/api/sample?mode=demo').status_code,200)
  self.assertEqual(len(c.get('/api/state?mode=demo').json['entries']),7)
  self.assertEqual(len(c.get('/api/state').json['entries']),3)
  self.assertEqual(c.post('/api/entry/4',data={'media':(io.BytesIO(b'bad'),'bad.jpg')}).status_code,400)
  self.assertEqual(c.post('/api/reset',headers={'Origin':'https://evil.example'}).status_code,403)
  r=c.post('/api/movie',json={'count':7});self.assertEqual(r.status_code,200)
  url=r.json['url']; self.assertEqual(c.get(url).status_code,200)
  self.assertIn('attachment',c.get(url+'?download=1').headers['Content-Disposition'])
  path=DATA/url.split('/')[-1]
  p=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(path)]))
  self.assertEqual((p['streams'][0]['width'],p['streams'][0]['height']),(360,640))
  self.assertAlmostEqual(float(p['format']['duration']),18,delta=.1)
  subprocess.run(['ffmpeg','-v','error','-i',str(path),'-f','null','-'],check=True)
  self.assertEqual(c.post('/api/reset?mode=demo').status_code,200)
  self.assertEqual(len(c.get('/api/state').json['entries']),3)
if __name__=='__main__': unittest.main()
