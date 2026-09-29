"""Offline media rendering: no network, no real trip claims in fixtures."""
import base64
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from html.parser import HTMLParser

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import render_outputs as ro
import validate_trip as vt
from media_support import media_assets

PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/lWQAAAAASUVORK5CYII=')

class MediaTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name).resolve()
        (self.base / 'media').mkdir()
        (self.base / 'media/test.png').write_bytes(PNG)
        self.trip = json.loads((ROOT / 'assets/examples/sample_trip.json').read_text())
        self.trip['media'] = [dict(media_id='test-photo',path='media/test.png',place_id=self.trip['places'][0]['place_id'],kind='illustration',role='cover',caption='测试配图',alt='测试用单色像素',creator='Test fixture',source_url=None,license='CC0',license_url='https://creativecommons.org/publicdomain/zero/1.0/',taken_at=None)]
    def tearDown(self):
        self.temp.cleanup()
    def test_photo_embeds_offline_and_keeps_credit(self):
        ctx = ro.Ctx(self.trip, self.base)
        page = ro.render_html(ctx)
        self.assertIn('data:image/png;base64,', page)
        self.assertIn('Test fixture', page)
        self.assertEqual(ro.coverage(ro.html_to_text(page), ctx.required_strings())['missing'], [])
    def test_missing_or_outside_file_fails(self):
        (self.base / 'media/test.png').unlink()
        with self.assertRaises(OSError): media_assets(self.trip, self.base)
        self.trip['media'][0]['path'] = '../private.png'
        with self.assertRaises(ValueError): media_assets(self.trip, self.base)
    def test_critical_tip_visible_before_details(self):
        day = self.trip['itinerary']['days'][0]
        item = next(x for x in day['items'] if x['kind'] == 'visit')
        item['brief'] = '看一小段就好'
        item['essential_tips'] = ['必须先确认当日开放']
        page = ro.render_html(ro.Ctx(self.trip, self.base))
        class Visible(HTMLParser):
            def __init__(self):super().__init__();self.depth=0;self.ignored=0;self.words=[]
            def handle_starttag(self,tag,attrs):
                if tag=='details':self.depth+=1
                if tag in ('script','style'):self.ignored+=1
            def handle_endtag(self,tag):
                if tag=='details':self.depth-=1
                if tag in ('script','style'):self.ignored-=1
            def handle_data(self,data):
                if not self.depth and not self.ignored:self.words.append(data)
        p=Visible();p.feed(page)
        self.assertIn('必须先确认当日开放',' '.join(p.words))
    def test_changed_image_is_rejected_by_output_check(self):
        path=self.base/'trip.json';path.write_text(json.dumps(self.trip,ensure_ascii=False))
        self.assertEqual(ro.main([str(path)]),0)
        audit=vt.Audit(self.trip);vt.check_outputs(self.trip,str(path),None,audit)
        self.assertEqual(audit.summary()['blocking'],0,audit.issues)
        (self.base/'media/test.png').write_bytes(PNG+b'changed')
        audit=vt.Audit(self.trip);vt.check_outputs(self.trip,str(path),None,audit)
        self.assertGreater(audit.summary()['blocking'],0)

if __name__=='__main__':unittest.main()
