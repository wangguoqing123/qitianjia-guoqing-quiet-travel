"""Coverage gaps, weather bounds and uncertainty in the public itinerary."""
import json
from pathlib import Path
import re
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import render_outputs as ro
import validate_trip as vt

def sample():return json.loads((ROOT/'assets/examples/sample_trip.json').read_text())

class WeatherTransportTests(unittest.TestCase):
 def test_partial_forecast_keeps_missing_day_slot(self):
  t=sample();days=t['itinerary']['days'];sid=t['sources'][0]['source_id']
  t['itinerary']['weather'].update(kind='forecast',entries=[{'date':days[0]['date'],'summary':'测试地阴，零下 2 至 4 度','source_id':sid,'location':'测试地','condition':'阴','low_c':-2,'high_c':4,'basis':'forecast','wind':'小于3级','advice':'带薄外套'}])
  c=ro.Ctx(t);html=ro.render_html(c);md=ro.render_md(c)
  self.assertIn('data-date="'+days[1]['date']+'"',html)
  self.assertIn('尚未取得该日可核实的预报',html)
  for text in (ro.html_to_text(html),md):
   self.assertIn('-2～4℃',text);self.assertIn('带薄外套',text)
  self.assertEqual(ro.coverage(ro.html_to_text(html),c.required_strings())['missing'],[])
 def test_invalid_temperature_and_source_are_rejected(self):
  t=sample();t['itinerary']['weather'].update(kind='forecast',entries=[{'date':t['itinerary']['days'][0]['date'],'summary':'错误测试数据','source_id':'missing-weather-source','low_c':30,'high_c':20,'basis':'forecast'}])
  a=vt.Audit(t);vt.semantic_checks(t,a)
  self.assertTrue(any('最低温高于最高温' in x['evidence'] for x in a.issues))
  self.assertTrue(any('天气引用的来源不存在' in x['evidence'] for x in a.issues))
 def test_unknown_arrival_and_self_drive_hint(self):
  t=sample()
  for tm in t['itinerary']['transport_major']:tm.update(kind='自驾',arrive=None,status='suggested')
  page=ro.render_html(ro.Ctx(t))
  self.assertIn('按实际路况确定',page)
  self.assertIn('自驾时刻是建议安排',page)
  self.assertNotIn('不代表有余票',page)
 def test_unknown_cost_does_not_take_fake_bar_width(self):
  t=sample();t['itinerary']['budget']['hard_limit']=None;t['request']['budget']['amount_max']=None
  page=ro.render_html(ro.Ctx(t))
  widths=[float(x) for x in re.findall(r'class="seg(?: paid)?" style="flex:0 0 ([0-9.]+)%',page)]
  self.assertLessEqual(sum(widths),100.05)
  self.assertNotIn('class="seg unk"',page)

if __name__=='__main__':unittest.main()
