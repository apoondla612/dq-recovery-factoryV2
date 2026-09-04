from __future__ import annotations
import json, os, subprocess
from pathlib import Path
from typing import Any
from .parser import parse_expression
from .utils import jread, sha256
from .semantic import normalise, canonical_bytes, shape_with_slots, canonical_semantics, render
from .binding import bind_tree
from .descriptors import match_rule
from .constants import OUTCOME_UNIVERSE
from .discovery import _build_closure, _collect_construct

def _verification_status(primary, norm, structure, closure):
    parse_status='complete' if primary['parse_status']=='complete' and not primary['decode_error'] and not closure['unresolved'] and not closure['multiply'] else 'partial'
    full_expression_complete = all(x['parse_status']=='complete' and x['bind_status']=='complete' for x in closure['supporting']+closure['companions'])
    blocked=closure['external_dependencies'] or parse_status!='complete' or not full_expression_complete
    if blocked: return parse_status,'blocked_external',None
    checks=[('primary',norm)] + [(x['name'],x['_norm']) for x in closure['supporting']] + [(x['name'],x['_norm']) for x in closure['companions']]
    rendered_primary=None
    for label,tree in checks:
        expected=canonical_bytes(tree); rend=render(tree); rr=parse_expression(rend); rb=bind_tree(rr.tree,structure,primary.get('owner_transform_id'))
        if label=='primary': rendered_primary=rend
        if rr.parse_status!='complete' or rb['bind_status']!='complete' or canonical_bytes(normalise(rb['tree']))!=expected:
            return parse_status,'failed',rendered_primary
    return parse_status,'passed',rendered_primary

def _load_previous(previous:Path|None)->tuple[dict[str,Any]|None,set[tuple[str,str]]]:
    if previous is None: return None,set()
    if previous.is_dir():
        cov=jread(previous/'coverage.json') if (previous/'coverage.json').exists() else None
        matrix=jread(previous/'construct-matrix.json') if (previous/'construct-matrix.json').exists() else []
    else:
        obj=jread(previous); cov=obj.get('counts') if 'counts' in obj and isinstance(obj['counts'],dict) else obj; matrix=[]
    return cov,{(x.get('construct_class'),x.get('construct_name')) for x in matrix}

def _collapse_questions(items:list[dict[str,Any]])->list[dict[str,Any]]:
    grouped={}
    for q in items:
        key=(q.get('member'),q.get('mapping'),q.get('invocation_id'),q.get('primary_endpoint_id'),q.get('ambiguity_id'))
        if key not in grouped:
            grouped[key]={k:v for k,v in q.items() if k not in {'question','reason'}}; grouped[key]['issues']=[]
        issue={k:v for k,v in q.items() if k not in {'member','domain','mapping','invocation_id','invocation_name','definition_id','primary_endpoint_id','ambiguity_id','addressed_to','question'}}
        if issue not in grouped[key]['issues']: grouped[key]['issues'].append(issue)
    out=[]
    for rec in grouped.values():
        reasons={x.get('reason') for x in rec['issues']}
        if 'semantic_ambiguity' in reasons: question='Which of the listed bounded endpoints is the governed primary validation outcome for this invocation?'
        elif {'identifier_binding','unmatched_rule_type'} <= reasons: question='What are the correct source-field bindings for the listed identifiers, and which governed rule type should this recovered shape be ratified as?'
        elif 'identifier_binding' in reasons: question='Which source fields should the listed unresolved or multiply-resolved identifiers bind to in this validation scope?'
        elif 'partial_descriptor_binding' in reasons: question='What values or source bindings resolve the listed descriptor parameters for this rule?'
        elif 'unmatched_rule_type' in reasons: question='Which governed rule type should this recovered shape be ratified as?'
        elif 'definition_missing' in reasons: question='Which source definition should this invocation resolve to?'
        else: question='What evidence is needed to resolve the listed recovery issue for this rule?'
        rec['question']=question; out.append(rec)
    return sorted(out,key=lambda q:(q.get('domain',''),q.get('mapping',''),q.get('invocation_id') or '',q.get('primary_endpoint_id') or ''))

def _recover_primary(mem, target, domain, ia, base, p, outcomes, recs, structure, definition, descriptor_set, constructs, questions, ambiguity_id=None):
    norm=normalise(p['tree']); cb=canonical_bytes(norm); shape_obj=shape_with_slots(norm); shape_sig=json.dumps(shape_obj,sort_keys=True,separators=(',',':'))
    closure=_build_closure(p,recs,structure,definition)
    for d in closure['external_dependencies']:
        _collect_construct(constructs,'semantic_operation',d['canonical_kind'],f"{mem['name']}::{target}::{ia.get('name')}")
        _collect_construct(constructs,'external_dependency_type',d.get('type') or 'external',f"{mem['name']}::{target}::{ia.get('name')}")
    parse_status,verification,rendered=_verification_status(p,norm,structure,closure)
    match=match_rule(norm,shape_obj,descriptor_set,parse_status); recovery_status='semantic_ambiguity' if ambiguity_id else match['status']
    if not ambiguity_id:
        if recovery_status=='unmatched': questions.append({**base,'primary_endpoint_id':p['id'],'question':'Which governed rule type should this candidate shape be ratified as?','addressed_to':domain,'reason':'unmatched_rule_type','shape_signature':shape_sig})
        elif recovery_status=='partial': questions.append({**base,'primary_endpoint_id':p['id'],'question':'Which values or bindings resolve the listed descriptor parameters for this rule?','addressed_to':domain,'reason':'partial_descriptor_binding','candidates':match.get('candidates',[])})
    if closure['unresolved'] or closure['multiply']:
        questions.append({**base,'primary_endpoint_id':p['id'] if not ambiguity_id else None,'ambiguity_id':ambiguity_id,'question':'Which source fields should the unresolved or multiply-resolved identifiers bind to in this validation scope?','addressed_to':domain,'reason':'identifier_binding','unresolved':closure['unresolved'],'multiply_resolved':closure['multiply']})
    rule={
        'semantics':{'primary':canonical_semantics(norm),'supporting_expressions':[{'name':x['name'],'expression':x['canonical']} for x in closure['supporting']],'companion_outputs':[{'name':x['name'],'expression':x['canonical']} for x in closure['companions']],'operations':[{'kind':d['canonical_kind']} for d in closure['external_dependencies']],'outcome_universe':OUTCOME_UNIVERSE,'reachable_outcomes':outcomes},
        'bindings':{'fields':closure['bound_fields'],'unresolved_identifiers':closure['unresolved'],'multiply_resolved_identifiers':closure['multiply'],'external_dependencies':closure['external_dependencies'],'parameters':match.get('parameters',{})},
        'evidence':{'source_member':mem['name'],'source_sha256':mem['sha256'],'domain':domain,'mapping':target,'invocation_id':ia.get('id'),'invocation_name':ia.get('name'),'definition_id':ia.get('mapplet'),'primary_endpoint_id':p['id'],'primary_endpoint_name':p['name'],'primary_expression_raw':p['raw'],'primary_expression_decoded':p['decoded'],'supporting_expression_records':[{'id':x['id'],'name':x['name'],'raw':x['raw']} for x in closure['supporting']],'companion_output_records':[{'id':x['id'],'name':x['name'],'raw':x['raw']} for x in closure['companions']],'semantic_hash':sha256(cb),'shape_signature':shape_sig,'descriptor_candidates':match.get('candidates',[]),'rendered_primary_expression':rendered},
        'status':{'parse_status':parse_status,'recovery_status':recovery_status,'verification_status':verification},
    }
    if ambiguity_id:
        rule['evidence']['ambiguity_id']=ambiguity_id; rule['evidence']['assumed_reading']=f"Treat output endpoint {p['name']} as the primary governed validation outcome for this invocation."
    elif match.get('matched_type'): rule['semantics']['rule_type']={'name':match['matched_type'],'version':match.get('matched_version')}
    return rule

def _resolve_code_sha(explicit:str|None)->str:
    if explicit: return explicit
    if os.getenv('GITHUB_SHA'): return os.environ['GITHUB_SHA']
    try: return subprocess.check_output(['git','rev-parse','HEAD'],cwd=Path(__file__).resolve().parents[2],stderr=subprocess.DEVNULL,text=True,timeout=2).strip()
    except Exception: return 'unavailable'
