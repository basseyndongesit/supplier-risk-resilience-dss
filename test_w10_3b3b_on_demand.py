"""Static safeguards for the on-demand UI, plus narrative tests in existing suite."""
import ast
import pathlib
import unittest
ROOT=pathlib.Path(__file__).resolve().parent
class OnDemandSafety(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ui=(ROOT/'w10_3b3b_live_ui.py').read_text()
        cls.app=(ROOT/'app_w10_3b3b.py').read_text()
    def test_syntax(self):
        for name in ('app_w10_3b3b.py','w10_3b3b_live_ui.py','w10_3b3b_dashboard.py'):
            ast.parse((ROOT/name).read_text())
    def test_button_gates_attribution(self):
        section=self.ui.split('def render_local_explanations(',1)[1]
        self.assertLess(section.index("st.button('Generate explanations"),section.index('report = cached_explain('))
        self.assertIn('if not st.button(',section)
        self.assertIn('return',section.split('if not st.button(',1)[1].split('report = cached_explain(',1)[0])
    def test_cache_scoped_to_selected_po(self):
        self.assertIn('int(po_id)',self.ui)
        self.assertIn('review_date',self.ui)
        self.assertIn('scenario, 64',self.ui)
        self.assertIn('tuple(signatures)',self.ui)
    def test_original_only_label(self):
        self.assertIn('ORIGINAL PO inputs only',self.ui)
        self.assertIn('independent of the PO and review date',self.app)
if __name__=='__main__': unittest.main()
