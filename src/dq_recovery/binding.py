from __future__ import annotations
from collections import defaultdict
from copy import deepcopy
from urllib.parse import unquote
from typing import Any
from .utils import attrs, local_name


def _datatype(raw: str | None) -> str | None:
    if not raw:
        return None
    value = unquote(raw)
    if '/' in value:
        value = value.rsplit('/', 1)[-1]
    if '.' in value and value.startswith('smd:'):
        value = value.rsplit('.', 1)[-1]
    return value


def build_structure_map(mapping) -> dict[str, Any]:
    parents = {child: parent for parent in mapping.iter() for child in parent}
    fields_by_id: dict[str, dict[str, Any]] = {}
    by_scope_name: dict[tuple[str | None, str], list[dict[str, Any]]] = defaultdict(list)
    transforms: dict[str, dict[str, Any]] = {}

    for e in mapping.iter():
        a = attrs(e)
        if local_name(e.tag) == 'AbstractTransformation' and a.get('id'):
            transforms[a['id']] = {
                'id': a['id'], 'name': a.get('name'), 'type': a.get('type')
            }

    for e in mapping.iter():
        a = attrs(e)
        tag = local_name(e.tag)
        if not tag.endswith('Field') or not a.get('id') or not a.get('name'):
            continue
        cur = e
        owner = None
        while cur in parents:
            cur = parents[cur]
            ca = attrs(cur)
            if local_name(cur.tag) == 'AbstractTransformation':
                owner = ca
                break
        rec = {
            'id': a['id'],
            'name': a['name'],
            'field_kind': tag,
            'datatype': _datatype(a.get('type')),
            'precision': a.get('precision') or a.get('odbcPrecision'),
            'scale': a.get('scale'),
            'input': a.get('input') == 'true',
            'output': a.get('output') == 'true',
            'owner_transform_id': owner.get('id') if owner else None,
            'owner_transform_name': owner.get('name') if owner else None,
            'owner_transform_type': owner.get('type') if owner else None,
        }
        fields_by_id[rec['id']] = rec
        by_scope_name[(rec['owner_transform_id'], rec['name'])].append(rec)

    return {
        'fields_by_id': fields_by_id,
        'by_scope_name': dict(by_scope_name),
        'transformations': transforms,
    }


def bind_tree(tree: dict[str, Any], structure: dict[str, Any], scope_id: str | None) -> dict[str, Any]:
    unresolved: list[str] = []
    multiply_resolved: list[str] = []
    bindings: dict[str, dict[str, Any]] = {}

    def visit(node: Any) -> Any:
        if not isinstance(node, dict):
            return node
        out = {k: deepcopy(v) for k, v in node.items() if k != 'args'}
        if node.get('op') == 'IDENT':
            name = node.get('name')
            hits = structure['by_scope_name'].get((scope_id, name), [])
            if len(hits) == 1:
                hit = hits[0]
                binding = {
                    'field_id': hit['id'],
                    'datatype': hit.get('datatype'),
                    'precision': hit.get('precision'),
                    'scale': hit.get('scale'),
                    'owner_transform_id': hit.get('owner_transform_id'),
                    'input': hit.get('input'),
                    'output': hit.get('output'),
                }
                out['binding'] = binding
                bindings[hit['id']] = hit
            elif len(hits) > 1:
                multiply_resolved.append(name)
                out['binding'] = {'candidates': [h['id'] for h in hits]}
            else:
                unresolved.append(name)
                out['binding'] = None
        if 'args' in node:
            out['args'] = [visit(a) for a in node.get('args', [])]
        return out

    bound = visit(tree)
    return {
        'tree': bound,
        'bind_status': 'complete' if not unresolved and not multiply_resolved else 'partial',
        'unresolved': sorted(set(unresolved)),
        'multiply_resolved': sorted(set(multiply_resolved)),
        'bindings': [bindings[k] for k in sorted(bindings)],
    }
