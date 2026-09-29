"""国庆避拥挤数据在核查和两种输出中保持一致；示例均为虚构。"""
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import render_outputs as ro
import validate_trip as vt
import state_io


def sample():
    with open(os.path.join(ROOT, "assets", "examples", "sample_trip.json"), encoding="utf-8") as f:
        return json.load(f)


class QuietPlanTests(unittest.TestCase):
    def test_quiet_reason_visible_in_both_outputs(self):
        trip = sample()
        plan = trip["itinerary"]["crowd_plan"]
        ctx = ro.Ctx(trip)
        md = ro.render_md(ctx)
        html = ro.html_to_text(ro.render_html(ctx))
        for text in (plan["goal"], plan["strategy"][0], plan["recheck"][0], "景点人流"):
            self.assertIn(text, md)
            self.assertIn(text, html)

    def test_risk_evidence_must_reference_a_source(self):
        trip = sample()
        plan = trip["itinerary"]["crowd_plan"]
        plan["crowd_risk"] = "low"
        plan["evidence"] = [{"area": "示例片区", "time_window": "目标日午前", "dimension": "crowd", "risk": "low", "reason": "演示用假设", "source_ids": ["missing-source"], "observed_at": None, "limits": "未实查"}]
        audit = vt.Audit(trip)
        vt.semantic_checks(trip, audit)
        self.assertTrue(any(x["severity"] == "blocking" and "missing-source" in x["evidence"] for x in audit.issues))

    def test_edit_invalidates_old_risk(self):
        trip = sample()
        plan = trip["itinerary"]["crowd_plan"]
        plan["crowd_risk"] = "low"
        plan["road_risk"] = "moderate"
        state_io.invalidate_review(trip)
        self.assertEqual((plan["crowd_risk"], plan["road_risk"]), ("unknown", "unknown"))
        self.assertIsNone(plan["checked_at"])


    def test_unknown_paid_stays_unknown_in_outputs(self):
        trip = sample()
        trip["request"]["budget"]["paid_amount"] = None
        for category in trip["itinerary"]["budget"]["categories"]:
            category["paid"] = None
        ctx = ro.Ctx(trip)
        for text in (ro.render_md(ctx), ro.html_to_text(ro.render_html(ctx))):
            self.assertIn("待确认（已付金额未知）", text)
            self.assertIn("本方案费用预留", text)
            self.assertNotIn("已付合计：0", text)
        audit = vt.Audit(trip)
        vt.semantic_checks(trip, audit)
        self.assertTrue(any("已付金额尚未提供" in x["evidence"] for x in audit.issues))


if __name__ == "__main__":
    unittest.main()
