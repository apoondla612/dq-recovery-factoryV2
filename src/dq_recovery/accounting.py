from __future__ import annotations
from collections import Counter
from pathlib import Path
import xml.etree.ElementTree as ET
from typing import Any
from .constants import MAPPED_ELEMENTS, MAPPED_ATTRIBUTES, EVIDENCE_ONLY_ATTRIBUTES
from .utils import attrs, local_name

def account_xml(paths:list[Path])->dict[str,Any]:
    e=Counter(); a=Counter(); t=Counter(); unknown_e=Counter(); unknown_a=Counter()
    for path in paths:
        root=ET.parse(path).getroot()
        for node in root.iter():
            tag=local_name(node.tag)
            if tag in MAPPED_ELEMENTS or tag.endswith('Field'):
                e['mapped']+=1
            else:
                e['marked_unknown']+=1; unknown_e[tag]+=1
            for raw in node.attrib:
                name=local_name(raw)
                if name in MAPPED_ATTRIBUTES: a['mapped']+=1
                elif name in EVIDENCE_ONLY_ATTRIBUTES: a['evidence_only']+=1
                else: a['marked_unknown']+=1; unknown_a[name]+=1
            if node.text and node.text.strip():
                # XML text is not interpreted by this adapter; it is still explicitly accounted.
                t['marked_unknown']+=1
    total_e=sum(e.values()); total_a=sum(a.values()); total_t=sum(t.values())
    inv={
        'element_denominator':total_e==e['mapped']+e['marked_unknown']+e['explicitly_ignored'],
        'attribute_denominator':total_a==a['mapped']+a['evidence_only']+a['marked_unknown']+a['explicitly_ignored'],
        'text_denominator':total_t==t['mapped']+t['marked_unknown']+t['explicitly_ignored'],
    }
    return {
        'elements_read':total_e,'attributes_read':total_a,'text_non_whitespace':total_t,
        'element_classification':dict(e),'attribute_classification':dict(a),'text_classification':dict(t),
        'unknown_elements':[{'name':k,'count':v} for k,v in unknown_e.most_common()],
        'unknown_attributes':[{'name':k,'count':v} for k,v in unknown_a.most_common()],
        'invariants':inv,'ok':all(inv.values()),
    }
