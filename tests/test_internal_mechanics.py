from __future__ import annotations
import json, tempfile, unittest
from pathlib import Path
from dq_recovery.parser import parse_expression
from dq_recovery.accounting import account_xml
from dq_recovery.descriptors import load_descriptor_set, match_rule
from dq_recovery.semantic import normalise, shape_with_slots

class InternalMechanicsTests(unittest.TestCase):
    def test_parser_is_total_on_malformed_input(self):
        result=parse_expression("IIF(A = 'x', (B > 2),")
        self.assertIn(result.parse_status, {'complete','partial','opaque'})
        self.assertIsInstance(result.tree, dict)

    def test_accounting_marks_unknowns_but_reconciles(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'x.xml'; p.write_text('<Root mystery="1"><Unknown/></Root>',encoding='utf-8')
            report=account_xml([p])
            self.assertTrue(report['ok'])
            self.assertGreater(report['element_classification']['marked_unknown'],0)
            self.assertGreater(report['attribute_classification']['marked_unknown'],0)

    def _descriptor_dir(self, duplicate=False):
        td=tempfile.TemporaryDirectory(); path=Path(td.name)
        tree=normalise(parse_expression('A > 10').tree); shp=shape_with_slots(tree)
        d={'name':'greater_than','version':'1','shape':shp,'parameters':[{'name':'field','slot':1},{'name':'threshold','slot':2}],'outcomes':['VALID','INVALID'],'example':'A > 10'}
        (path/'one.json').write_text(json.dumps(d),encoding='utf-8')
        if duplicate:
            d2=dict(d); d2['name']='greater_than_duplicate'; (path/'two.json').write_text(json.dumps(d2),encoding='utf-8')
        return td,path,tree,shp

    def test_descriptor_match_and_conflict(self):
        td,path,tree,shp=self._descriptor_dir(False)
        try:
            ds=load_descriptor_set(path); result=match_rule(tree,shp,ds,'complete')
            self.assertEqual(result['status'],'matched')
            self.assertEqual(result['matched_type'],'greater_than')
        finally: td.cleanup()
        td,path,tree,shp=self._descriptor_dir(True)
        try:
            ds=load_descriptor_set(path); result=match_rule(tree,shp,ds,'complete')
            self.assertEqual(result['status'],'descriptor_conflict')
        finally: td.cleanup()

    def test_invalid_descriptor_shape_fails_loading(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'bad.json'; p.write_text(json.dumps({'name':'bad','version':'1','shape':{'bad':'shape'},'parameters':[],'outcomes':[],'example':'x'}),encoding='utf-8')
            with self.assertRaises(ValueError): load_descriptor_set(Path(td))

if __name__=='__main__': unittest.main()
