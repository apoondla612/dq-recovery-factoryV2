from __future__ import annotations
import json, time, resource
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
import xml.etree.ElementTree as ET
from typing import Any
from .constants import LOGIC_ATTRS, PARSEABLE_KINDS, CANON_OPS
from .parser import parse_expression
from .utils import attrs, local_name, jwrite, jread, sha256, decode_native
from .semantic import find_mapping, mapping_index, infer_outcomes
from .descriptors import load_descriptor_set
from .accounting import account_xml
from .discovery import _expr_records, _domain_from_member, _collect_construct
from .rule_engine import _recover_primary, _load_previous, _collapse_questions, _resolve_code_sha

def scan_and_recover(work:Path, manifest:dict[str,Any], descriptors_dir:Path|None=None, previous:Path|None=None, code_sha:str|None=None, budget_path:Path|None=None)->dict[str,Any]:
    started=time.perf_counter(); counts=Counter(); parse_counts=Counter(); tx_counts=Counter(); constructs={}; candidates=[]; rules=[]; ambiguous=[]; helpers=[]; decode_errors=[]; questions=[]
    descriptor_set=load_descriptor_set(descriptors_dir); xml_paths=[work/m['path'] for m in manifest['members']]; accounting=account_xml(xml_paths); jwrite(work/'output'/'accounting.json',accounting)
    for mem in manifest['members']:
        path=work/mem['path']; root=ET.parse(path).getroot(); target=Path(mem['name']).stem; mids=mapping_index(root); selected=find_mapping(root,target); domain=_domain_from_member(mem['name'])
        for e in root.iter():
            a=attrs(e)
            if local_name(e.tag)=='AbstractTransformation' and a.get('type'):
                tx_counts[a['type']]+=1; _collect_construct(constructs,'transformation_type',a['type'],f"{mem['name']}::{a.get('name') or a.get('id')}")
            for k,v in a.items():
                if k in LOGIC_ATTRS:
                    kind=LOGIC_ATTRS[k]; counts[kind]+=1; loc=f"{mem['name']}::{a.get('name') or a.get('id')}::{k}"; _collect_construct(constructs,'record_kind',kind,loc)
                    if kind in PARSEABLE_KINDS:
                        dec,err=decode_native(v)
                        if err: decode_errors.append({'member':mem['name'],'owner_id':a.get('id'),'kind':kind,'error':err})
                        pr=parse_expression(dec); parse_counts[pr.parse_status]+=1
                        for c in pr.constructs:
                            cls,name=c.split(':',1); _collect_construct(constructs,cls,name,loc)
                        def walk(n):
                            if isinstance(n,dict):
                                if n.get('op') in CANON_OPS: _collect_construct(constructs,'expression_operator',n['op'],loc)
                                for ch in n.get('args',[]): walk(ch)
                        walk(pr.tree)
        if selected is None: continue
        invs=[e for e in selected.iter() if attrs(e).get('type')=='mapplet:MappletTx' and (attrs(e).get('name') or '').startswith('rule_')]
        for inv in invs:
            ia=attrs(inv); base={'member':mem['name'],'domain':domain,'mapping':target,'invocation_id':ia.get('id'),'invocation_name':ia.get('name'),'definition_id':ia.get('mapplet')}; candidates.append(base); definition=mids.get(ia.get('mapplet'))
            if definition is None:
                helpers.append({**base,'reason':'definition_missing'}); questions.append({**base,'question':'Which source definition should this invocation resolve to?','addressed_to':domain,'reason':'definition_missing'}); continue
            env,recs,structure=_expr_records(definition); prim=[]
            for r in recs:
                if not r['output']: continue
                scope_env={name:tree for (scope,name),tree in env.items() if scope==r['owner_transform_id']}; outs=infer_outcomes(r['tree'],scope_env)
                if outs: prim.append((r,sorted(outs)))
            if len(prim)==0: helpers.append({**base,'reason':'no_bounded_primary_endpoint'}); continue
            ambiguity_id=None
            if len(prim)>1:
                ambiguity_id=sha256((mem['sha256']+str(ia.get('id'))).encode())[:16]
                ambiguous.append({**base,'reason':'multiple_primary_endpoints','ambiguity_id':ambiguity_id,'endpoints':[{'id':r['id'],'name':r['name'],'outcomes':o} for r,o in prim]})
                questions.append({**base,'question':'Which of the listed bounded endpoints is the governed primary validation outcome for this invocation?','addressed_to':domain,'reason':'semantic_ambiguity','ambiguity_id':ambiguity_id})
            for p,outcomes in prim: rules.append(_recover_primary(mem,target,domain,ia,base,p,outcomes,recs,structure,definition,descriptor_set,constructs,questions,ambiguity_id=ambiguity_id))
    rules_dir=work/'output'/'rules'; rules_dir.mkdir(parents=True,exist_ok=True); ordered=sorted(rules,key=lambda x:(x['evidence']['mapping'],x['evidence']['invocation_id'] or '',x['evidence']['primary_endpoint_id'] or ''))
    for i,r in enumerate(ordered):
        inv=(r['evidence']['invocation_id'] or 'unknown').replace(':','_'); jwrite(rules_dir/f"{i+1:04d}-{r['evidence']['mapping']}-{inv}.json",r)
    clusters=defaultdict(list)
    for r in rules: clusters[r['evidence']['shape_signature']].append(r)
    cluster_list=[]
    for sig,items in sorted(clusters.items(),key=lambda kv:(-len(kv[1]),kv[0])):
        cluster_list.append({'shape_signature':sig,'count':len(items),'covered_by_descriptor':any(x['status']['recovery_status']=='matched' for x in items),'example_location':f"{items[0]['evidence']['source_member']}::{items[0]['evidence']['mapping']}::{items[0]['evidence']['invocation_name']}"})
    coverage={'source_members':manifest['member_count'],'structural':{'elements':accounting['elements_read'],'attributes':accounting['attributes_read'],'text_non_whitespace':accounting['text_non_whitespace']},'record_kinds':dict(sorted(counts.items())),'parse_status':dict(sorted(parse_counts.items())),'candidate_rule_invocations':len(candidates),'primary_endpoint_denominator':len(rules),'helper_or_non_outcome_invocations':len(helpers),'semantic_ambiguities':len(ambiguous),'recovery_status':dict(Counter(r['status']['recovery_status'] for r in rules)),'verification_status':dict(Counter(r['status']['verification_status'] for r in rules)),'descriptor_set_version':descriptor_set.version,'descriptor_set_hash':descriptor_set.hash}
    matched=coverage['recovery_status'].get('matched',0); denom=coverage['primary_endpoint_denominator']; coverage['matched_percentage']=round((100.0*matched/denom),6) if denom else 0.0
    accounted_invocations=len(rules)+len(helpers)-len(ambiguous); parseable=sum(parse_counts.values()); complete=parse_counts.get('complete',0); verified=coverage['verification_status'].get('passed',0)
    coverage['coverage_metrics']={'discovery_coverage':{'numerator':accounted_invocations,'denominator':len(candidates),'percentage':round(100.0*accounted_invocations/len(candidates),6) if candidates else 0.0},'parse_completeness':{'numerator':complete,'denominator':parseable,'percentage':round(100.0*complete/parseable,6) if parseable else 0.0},'canonical_recovery_coverage':{'numerator':matched,'denominator':denom,'percentage':coverage['matched_percentage']},'roundtrip_verification':{'numerator':verified,'denominator':denom,'percentage':round(100.0*verified/denom,6) if denom else 0.0},'truth_table_verification':{'numerator':0,'denominator':denom,'percentage':0.0,'status':'not_run'},'external_blocker_count':coverage['verification_status'].get('blocked_external',0)}
    previous_cov,previous_constructs=_load_previous(previous); matrix=[]
    for key in sorted(constructs):
        rec=constructs[key]; rec['support_status']='supported' if rec['construct_class'] in {'record_kind','transformation_type','expression_operator','expression_builtin','external_invocation'} else 'observed'; rec['newly_unsupported']=bool(previous_constructs and (rec['construct_class'],rec['construct_name']) not in previous_constructs and rec['support_status']!='supported'); matrix.append(rec)
    jwrite(work/'output'/'coverage.json',coverage); jwrite(work/'output'/'construct-matrix.json',matrix); jwrite(work/'output'/'ambiguities.json',ambiguous); jwrite(work/'output'/'helpers.json',helpers); jwrite(work/'output'/'candidate-clusters.json',cluster_list)
    collapsed_questions=_collapse_questions(questions); jwrite(work/'output'/'open-questions.json',collapsed_questions)
    spec_hashes={}; spec_status={}; auth=Path(__file__).resolve().parents[2]/'specs'/'authority-hashes.json'
    if auth.exists():
        authority=jread(auth); spec_hashes=authority.get('documents',{}); spec_status=authority.get('required_specifications',{})
    run_manifest={'archive_sha256':manifest['archive_sha256'],'member_shas':[m['sha256'] for m in manifest['members']],'code_sha':_resolve_code_sha(code_sha),'tool_version':'0.3.0','specification_hashes':spec_hashes,'specification_status':spec_status,'descriptor_set_version':descriptor_set.version,'descriptor_set_hash':descriptor_set.hash,'reference_data_snapshot_hashes':{},'configuration':{'descriptors_dir':str(descriptors_dir) if descriptors_dir else None},'counts':coverage}; jwrite(work/'output'/'run-manifest.json',run_manifest)
    failures=[]
    if not accounting['ok']: failures.append('accounting invariant failure')
    if parse_counts.get('opaque',0): failures.append('opaque parse records')
    if decode_errors: failures.append('decode errors')
    if any(r['status']['verification_status']=='failed' for r in rules): failures.append('round-trip failure')
    if any(r['status']['recovery_status']=='descriptor_conflict' for r in rules): failures.append('descriptor conflict')
    if previous_cov is not None:
        prev_pct=float(previous_cov.get('matched_percentage',0.0)); cur_pct=float(coverage['matched_percentage'])
        if cur_pct < prev_pct: failures.append(f'coverage regression: matched percentage {cur_pct} < {prev_pct}')
    bad=[]
    for p in rules_dir.glob('*.json'):
        obj=jread(p); s=json.dumps(obj['semantics']).lower()
        for token in ('informatica','snowflake',':lkp'):
            if token in s: bad.append((p.name,token))
    if bad: failures.append('vendor token in semantics')
    wall_seconds=time.perf_counter()-started; max_rss_kb=int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss); budget_measurement={'wall_seconds':round(wall_seconds,6),'max_rss_kb':max_rss_kb}; budget_result={'enforced':False,'passed':None}
    if budget_path is not None:
        b=jread(budget_path); budget_result['enforced']=True; budget_result['limits']=b; over=[]
        if b.get('max_wall_seconds') is not None and wall_seconds>float(b['max_wall_seconds']): over.append('wall_seconds')
        if b.get('max_rss_kb') is not None and max_rss_kb>int(b['max_rss_kb']): over.append('max_rss_kb')
        budget_result['passed']=not over; budget_result['exceeded']=over
        if over: failures.append('run budget exceeded: '+','.join(over))
    gates={'accounting':accounting['ok'],'parse_totality_on_pilot':not parse_counts.get('opaque',0),'roundtrip_for_verifiable_rules':not any(r['status']['verification_status']=='failed' for r in rules),'vendor_neutral_semantics':not bad,'coverage_non_regression':not any(x.startswith('coverage regression') for x in failures),'descriptor_conflict_free':not any(r['status']['recovery_status']=='descriptor_conflict' for r in rules),'run_budget':budget_result,'failures':failures,'ok':not failures}
    jwrite(work/'output'/'gates.json',gates); jwrite(work/'run-event.json',{'completed_at':datetime.now(timezone.utc).isoformat(),'performance':{**budget_measurement,'budget':budget_result},'operational_note':'Operational metadata kept outside output/ so deterministic output can be diffed literally.'})
    return {'coverage':coverage,'gates':gates,'rules':rules,'ambiguous':ambiguous,'helpers':helpers,'questions':collapsed_questions}
