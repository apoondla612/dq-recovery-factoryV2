from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from .constants import RECOGNISED_BUILTINS

Token = tuple[str, str, int]
_PRECEDENCE = {"OR":1,"AND":2,"=":3,"<>":3,"!=":3,"^=":3,"<":4,"<=":4,">":4,">=":4,"||":5,"+":6,"-":6,"*":7,"/":7,"%":7}

class Lexer:
    def __init__(self, text: str):
        self.text=text or ""; self.n=len(self.text); self.i=0; self.comments=[]
    def _peek(self): return self.text[self.i] if self.i < self.n else ""
    def _advance(self): ch=self.text[self.i]; self.i+=1; return ch
    def tokens(self) -> list[Token]:
        out=[]
        while self.i < self.n:
            ch=self._peek()
            if ch in " \t\r\n": self.i+=1; continue
            if ch=="-" and self.i+1<self.n and self.text[self.i+1]=="-":
                start=self.i; self.i+=2
                while self.i<self.n and self.text[self.i] not in "\r\n": self.i+=1
                self.comments.append({"text":self.text[start:self.i],"offset":start}); continue
            if ch=="'": out.append(self._string()); continue
            if ch.isdigit() or (ch=="." and self.i+1<self.n and self.text[self.i+1].isdigit()):
                out.append(self._number()); continue
            two=self.text[self.i:self.i+2]
            if two in ("||","!=","<>","<=",">=","^="):
                out.append(("OP",two,self.i)); self.i+=2; continue
            if ch in "+-*/%<>=(),": out.append(("OP",ch,self.i)); self.i+=1; continue
            if ch==":" or ch.isalpha() or ch=="_": out.append(self._ident()); continue
            out.append(("OPAQUE",ch,self.i)); self.i+=1
        out.append(("EOF","",self.i)); return out
    def _string(self):
        start=self.i; self.i+=1; buf=[]
        while self.i<self.n:
            ch=self._advance()
            if ch=="'":
                if self._peek()=="'": self._advance(); buf.append("'"); continue
                return ("STR","".join(buf),start)
            buf.append(ch)
        return ("UNTERM_STR","".join(buf),start)
    def _number(self):
        start=self.i; dots=0
        while self.i<self.n and (self.text[self.i].isdigit() or self.text[self.i]=="."):
            dots += self.text[self.i]=="."; self.i+=1
        raw=self.text[start:self.i]
        return ("NUM",raw,start) if dots<=1 else ("OPAQUE",raw,start)
    def _ident(self):
        start=self.i
        while self.i<self.n and (self.text[self.i].isalnum() or self.text[self.i] in "._:$"):
            self.i+=1
        raw=self.text[start:self.i]; upper=raw.upper()
        if upper in {"AND","OR","NOT","NULL"}: return ("OP",upper,start)
        if upper in {"TRUE","FALSE"}: return ("BOOL",upper,start)
        return ("IDENT",raw,start)

@dataclass
class ParseResult:
    tree: dict[str, Any]
    parse_status: str
    comments: list[dict[str, Any]] = field(default_factory=list)
    constructs: list[str] = field(default_factory=list)
    error: str | None = None

class Parser:
    def __init__(self,text:str):
        self.text=text or ""; lex=Lexer(self.text); self.tokens=lex.tokens(); self.comments=lex.comments
        self.pos=0; self.constructs=[]; self.partial=False; self.opaque=False
    def _cur(self): return self.tokens[self.pos]
    def parse(self):
        try:
            if not self.text.strip():
                return ParseResult({"op":"LIT","kind":"empty","value":""},"complete",self.comments)
            tree=self._expr(0)
            if self._cur()[0] != "EOF":
                off=self._cur()[2]; self.opaque=True
                tree={"op":"SEQ","args":[tree,{"op":"OPAQUE","text":self.text[off:],"offset":off}]}
            status="opaque" if self.opaque else ("partial" if self.partial else "complete")
            return ParseResult(tree,status,self.comments,self.constructs)
        except Exception as exc:
            return ParseResult({"op":"OPAQUE","text":self.text,"offset":0},"opaque",self.comments,self.constructs,str(exc))
    def _expr(self,min_prec:int):
        left=self._prefix()
        while True:
            kind,val,_=self._cur()
            if kind!="OP" or val not in _PRECEDENCE: break
            prec=_PRECEDENCE[val]
            if prec<min_prec: break
            self.pos+=1; right=self._expr(prec+1); left={"op":val,"args":[left,right]}
        return left
    def _prefix(self):
        kind,val,off=self._cur()
        if kind=="OP" and val=="(":
            self.pos+=1; node=self._expr(0)
            if self._cur()[1]==")": self.pos+=1
            else: self.opaque=True
            return node
        if kind=="OP" and val in {"+","-","NOT"}:
            self.pos+=1; operand=self._expr(_PRECEDENCE["AND"]+1) if val=="NOT" else self._prefix()
            return {"op":"NOT" if val=="NOT" else "U"+val,"args":[operand]}
        if kind=="STR": self.pos+=1; return {"op":"LIT","kind":"string","value":val}
        if kind=="UNTERM_STR": self.pos+=1; self.opaque=True; return {"op":"OPAQUE","text":self.text[off:],"offset":off}
        if kind=="NUM": self.pos+=1; return {"op":"LIT","kind":"number","value":val}
        if kind=="OP" and val=="NULL": self.pos+=1; return {"op":"LIT","kind":"null","value":None}
        if kind=="BOOL": self.pos+=1; return {"op":"LIT","kind":"bool","value":val}
        if kind=="IDENT":
            self.pos+=1
            if self._cur()[1]=="(": return self._call((kind,val,off))
            return {"op":"IDENT","name":val}
        if kind=="OPAQUE": self.pos+=1; self.opaque=True; return {"op":"OPAQUE","text":val,"offset":off}
        if kind=="EOF": self.opaque=True; return {"op":"OPAQUE","text":"","offset":off}
        self.pos+=1; self.opaque=True; return {"op":"OPAQUE","text":val,"offset":off}
    def _call(self,ident:Token):
        name=ident[1]
        if self._cur()[1]=="(": self.pos+=1
        args=[]
        if self._cur()[1] != ")":
            while True:
                args.append(self._expr(0))
                if self._cur()[1]==",": self.pos+=1; continue
                break
        if self._cur()[1]==")": self.pos+=1
        else: self.opaque=True
        upper=name.upper()
        if upper.startswith(":LKP"):
            self.constructs.append(f"external_invocation:{name}")
            return {"op":"LKP","name":name,"args":args}
        recognised=upper in RECOGNISED_BUILTINS
        if recognised: self.constructs.append(f"expression_builtin:{upper}")
        else: self.partial=True; self.constructs.append(f"expression_builtin_unknown:{name}")
        return {"op":"CALL","name":upper if recognised else name,"recognised":recognised,"args":args}

def parse_expression(text:str) -> ParseResult:
    return Parser(text or "").parse()
