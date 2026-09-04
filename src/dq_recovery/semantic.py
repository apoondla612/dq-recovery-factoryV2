from __future__ import annotations
import json
from .constants import *
from .utils import attrs, local_name

def find_mapping(root,target):
    hits=[]
    for e in root.iter():
        a=attrs(e)
        if a.get('name')==target and (local_name(e.tag)=='Mapping' or a.get('type')=='mapping:Mapping'): hits.append(e)
    return max(hits,key=lambda e:sum(1 for _ in e.iter())) if hits else None

def mapping_index(root):
    out={}
    for e in root.iter():
        a=attrs(e)
        if (local_name(e.tag)=='Mapping' or a.get('type')=='mapping:Mapping') and a.get('id'): out[a['id']]=e
    return out

def infer_outcomes(node,env,seen=frozenset()):
    if not isinstance(node,dict): return None
    op=node.get('op')
    if op=='LIT' and node.get('kind')=='string':
        v=node.get('value'); return {OUTCOME_MAP[v]} if v in OUTCOME_MAP else set()
    if op=='IDENT':
        n=node.get('name')
        if n in seen: return None
        return infer_outcomes(env[n],env,seen|{n}) if n in env else None
    if op=='CALL':
        name=node.get('name','').upper(); args=node.get('args',[])
        if name=='IIF' and len(args)>=3:
            a=infer_outcomes(args[1],env,seen); b=infer_outcomes(args[2],env,seen)
            return None if a is None or b is None else a|b
        if name=='DECODE' and len(args)>=3:
            vals=[]; i=2
            while i<len(args): vals.append(args[i]); i+=2
            if len(args)%2==0: vals.append(args[-1])
            out=set()
            for v in vals:
                r=infer_outcomes(v,env,seen)
                if r is None: return None
                out|=r
            return out
    return None

def normalise(node):
    if not isinstance(node,dict) or 'op' not in node: raise ValueError('malformed tree')
    op=node['op']
    if op in {'AND','OR'}:
        children=[]
        def add(n):
            nn=normalise(n)
            if nn.get('op')==op: children.extend(nn.get('args',[]))
            else: children.append(nn)
        for c in node.get('args',[]): add(c)
        return {'op':op,'args':children}
    if op=='CALL':
        name=node.get('name',''); rec=bool(node.get('recognised')) or name.upper() in RECOGNISED_BUILTINS
        return {'op':'CALL','name':name.upper() if rec else name,'recognised':rec,'args':[normalise(a) for a in node.get('args',[])]}
    if op=='LKP': return {'op':'LKP','name':node.get('name'),'args':[normalise(a) for a in node.get('args',[])]}
    if op=='LIT':
        d={'op':'LIT','kind':node.get('kind'),'value':node.get('value')}
        if d['kind']=='string' and d['value'] in OUTCOME_MAP: d['outcome']=OUTCOME_MAP[d['value']]
        return d
    if op in {'IDENT','OPAQUE'}: return {k:v for k,v in node.items() if k in {'op','name','text','offset'}}
    return {'op':op,'args':[normalise(a) for a in node.get('args',[])]} if 'args' in node else dict(node)

def canonical_bytes(node): return json.dumps(node,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def shape(node):
    op=node.get('op')
    if op=='IDENT': return 'FIELD'
    if op=='LIT':
        if node.get('outcome'): return 'OUTCOME'
        return {'string':'STR','number':'NUM','null':'NULL','bool':'BOOL','empty':'EMPTY'}.get(node.get('kind'),'LIT')
    if op=='LKP': return ['reference_lookup','REF',[shape(a) for a in node.get('args',[])]]
    if op=='CALL': return [node.get('name'),[shape(a) for a in node.get('args',[])]]
    if 'args' in node: return [op,[shape(a) for a in node.get('args',[])]]
    return [op]

def canonical_semantics(node):
    op=node.get('op')
    if op=='CALL': return {'kind':'call','name':CANON_CALLS.get(node.get('name'),node.get('name')),'args':[canonical_semantics(a) for a in node.get('args',[])]}
    if op=='LKP': return {'kind':'reference_lookup','reference':node.get('name'),'args':[canonical_semantics(a) for a in node.get('args',[])]}
    if op=='IDENT': return {'kind':'field','name':node.get('name')}
    if op=='LIT':
        if node.get('outcome'): return {'kind':'outcome','value':node['outcome']}
        return {'kind':'literal','type':node.get('kind'),'value':node.get('value')}
    if op=='OPAQUE': return {'kind':'opaque'}
    if op in CANON_OPS: return {'kind':CANON_OPS[op],'args':[canonical_semantics(a) for a in node.get('args',[])]}
    return {'kind':str(op).lower(),'args':[canonical_semantics(a) for a in node.get('args',[])]}

def render(node):
    op=node.get('op')
    if op=='LIT':
        k=node.get('kind'); v=node.get('value')
        if k=='string': return "'"+str(v).replace("'","''")+"'"
        if k=='null': return 'NULL'
        return str(v)
    if op=='IDENT': return node.get('name','')
    if op=='LKP': return f"{node.get('name')}("+', '.join(render(a) for a in node.get('args',[]))+')'
    if op=='CALL': return f"{node.get('name')}("+', '.join(render(a) for a in node.get('args',[]))+')'
    if op in {'NOT','U+','U-'}: return ('NOT ' if op=='NOT' else op[1])+render(node['args'][0])
    if op in {'AND','OR'}: return (' '+op+' ').join('('+render(a)+')' for a in node.get('args',[]))
    if len(node.get('args',[]))==2: return '('+render(node['args'][0])+f' {op} '+render(node['args'][1])+')'
    return ''
