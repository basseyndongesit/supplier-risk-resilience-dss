"""Static regression checks for navigation and human-decision preservation."""
import unittest
from pathlib import Path

APP = Path(__file__).with_name('app_w10_3b4.py').read_text(encoding='utf-8')
DASH = Path(__file__).with_name('w10_3b4_dashboard.py').read_text(encoding='utf-8')

class WorkflowTests(unittest.TestCase):
    def test_navigation_order(self):
        names=['1. Weekly Risk Review','2. PO / Supplier Detail','3. Scenario Comparison',
               '4. Management Review','5. Predictive Risk Ranking','6. Interactive What-If Prediction',
               '7. Model Validation & Explainability Evidence','8. Integrated Decision Dashboard',
               '9. Options & Decision Record']
        self.assertEqual([APP.index(repr(n)) for n in names], sorted(APP.index(repr(n)) for n in names))
    def test_final_screen_contains_evidence_and_decision_form(self):
        block=APP.split("elif screen.startswith('9.'):")[1].split("elif screen.startswith('5.'):")[0]
        for needle in ['render_decision_evidence(', 'Save decision', 'Decision owner', 'Decision rationale', 'Human_Decisions']:
            self.assertIn(needle, block)
    def test_original_db_protected_before_save(self):
        block=APP.split("elif screen.startswith('9.'):")[1].split("elif screen.startswith('5.'):")[0]
        self.assertLess(block.index('if record_db == Path(db).resolve():'), block.index("if st.button('Save decision'):"))
    def test_dashboard_navigation_labels(self):
        self.assertIn('Use Screen 9 to record one.', DASH)
        self.assertIn('Screen 7 uses historical validation examples;', DASH)
    def test_explanations_remain_on_demand(self):
        live=Path(__file__).with_name('w10_3b3b_live_ui.py').read_text(encoding='utf-8')
        self.assertIn('Generate explanations', live)

if __name__=='__main__':
    unittest.main()
