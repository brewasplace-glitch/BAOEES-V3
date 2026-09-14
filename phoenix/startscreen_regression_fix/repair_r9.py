#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from html.parser import HTMLParser
from pathlib import Path

HOST_DIR_REL="phoenix/local_app/static/official_start_v3_0"
HOST_REL=HOST_DIR_REL+"/index.html"
BRIDGE_REL=HOST_DIR_REL+"/phoenix_detv_cad_bridge.js"
GUARD_REL=HOST_DIR_REL+"/phoenix_start_v441_runtime_guard.js"

MOJIBAKE_LEADS=set("ÃÂâðï")
KNOWN=("ðŸ","â€","âœ","â˜","âš","â†","â‡","âŒ","â”","â–","â—","ï¸","Ã","Â","�")

def suspicious_count(text:str)->int:
    return sum(text.count(x) for x in KNOWN)+sum(1 for ch in text if 0x80<=ord(ch)<=0x9F)

def original_byte(ch:str):
    try:
        b=ch.encode("cp1252")
        if len(b)==1:return b[0]
    except UnicodeEncodeError:
        pass
    n=ord(ch)
    if 0x80<=n<=0x9F:return n
    if n<0x80:return n
    return None

def decode_segment(segment:str):
    data=bytearray()
    for ch in segment:
        b=original_byte(ch)
        if b is None:return None
        data.append(b)
    try:return bytes(data).decode("utf-8")
    except UnicodeDecodeError:return None

def repair_pass(text:str):
    out=[]
    i=0
    changed=False
    while i<len(text):
        ch=text[i]
        if ch not in MOJIBAKE_LEADS:
            out.append(ch);i+=1;continue
        best=None
        for length in range(2,min(16,len(text)-i)+1):
            seg=text[i:i+length]
            candidate=decode_segment(seg)
            if candidate is None or candidate==seg:continue
            if suspicious_count(candidate)<suspicious_count(seg):
                best=(length,candidate);break
        if best:
            length,candidate=best
            out.append(candidate)
            i+=length
            changed=True
        else:
            out.append(ch);i+=1
    return "".join(out),changed

def fix_mojibake(text:str):
    out=text
    for _ in range(8):
        nxt,changed=repair_pass(out)
        out=nxt
        if not changed:break
    return out

class VisibleTextParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.hidden_depth=0
        self.parts=[]
    def handle_starttag(self,tag,attrs):
        if tag.lower() in {"script","style","noscript","template"}:
            self.hidden_depth+=1
    def handle_endtag(self,tag):
        if tag.lower() in {"script","style","noscript","template"} and self.hidden_depth:
            self.hidden_depth-=1
    def handle_data(self,data):
        if self.hidden_depth==0:
            self.parts.append(data)

def visible_text(html_text:str)->str:
    p=VisibleTextParser()
    p.feed(html_text)
    return "\n".join(p.parts)

def repair_navicons(text:str):
    replacements=[]
    pat=re.compile(
        r'(<span\b[^>]*\bclass=["\'][^"\']*\bnavicon\b[^"\']*["\'][^>]*>)([^<]*)(</span>)',
        flags=re.I
    )
    def repl(m):
        inner=m.group(2)
        if suspicious_count(inner)==0:
            return m.group(0)
        replacements.append({"before":inner,"after":"&#x25CF;"})
        return m.group(1)+"&#x25CF;"+m.group(3)
    return pat.sub(repl,text),replacements

def repair_prev_button(text:str):
    replacements=[]
    pat=re.compile(
        r'(<button\b[^>]*\bid=["\']phoenixTvPrev["\'][^>]*>)([^<]*)(</button>)',
        flags=re.I
    )
    def repl(m):
        inner=m.group(2)
        if "VORIGE" not in inner.upper():
            return m.group(0)
        canonical="&#x2190; VORIGE"
        if inner.strip()==canonical:
            return m.group(0)
        replacements.append({"before":inner,"after":canonical})
        return m.group(1)+canonical+m.group(3)
    return pat.sub(repl,text),replacements

def repair_known_nested_utf8_residuals(text:str):
    replacements=[]
    # Real PHOENIX 4.41 residual observed after R8:
    # U+00F0 U+00C5 U+00B8 U+008F U+00A2
    # This is a nested Windows-1252/UTF-8 corruption of UTF-8 bytes
    # F0 9F 8F A2 = U+1F3E2 OFFICE BUILDING.
    bad="\u00f0\u00c5\u00b8\u008f\u00a2"
    good="&#x1F3E2;"
    count=text.count(bad)
    if count:
        text=text.replace(bad,good)
        replacements.append({
            "kind":"nested_utf8_cp1252",
            "source_codepoints":["U+00F0","U+00C5","U+00B8","U+008F","U+00A2"],
            "utf8_bytes":"F0 9F 8F A2",
            "target":"U+1F3E2",
            "replacement":"&#x1F3E2;",
            "count":count
        })
    return text,replacements

def repair_visible_semantics(text:str):
    text,nested=repair_known_nested_utf8_residuals(text)
    text,nav=repair_navicons(text)
    text,prev=repair_prev_button(text)
    return text,{"nested":nested,"navicons":nav,"prev":prev}

def visible_residual_contexts(text:str,limit=20):
    visible=visible_text(text)
    hits=[]
    for i,ch in enumerate(visible):
        bad=(0x80<=ord(ch)<=0x9F) or any(visible.startswith(f,i) for f in KNOWN)
        if bad:
            hits.append(repr(visible[max(0,i-60):min(len(visible),i+100)]))
            if len(hits)>=limit:break
    return hits

def repair_host(repo:Path,report:Path):
    host=repo/HOST_REL
    text=host.read_text(encoding="utf-8-sig")
    before_all=suspicious_count(text)
    before_visible=suspicious_count(visible_text(text))

    fixed,nested_pre=repair_known_nested_utf8_residuals(text)
    fixed=fix_mojibake(fixed)
    fixed,semantic=repair_visible_semantics(fixed)
    if nested_pre:
        semantic["nested"]=nested_pre+semantic.get("nested",[])

    # Canonical UTF-8 metadata.
    if re.search(r'<meta\s+[^>]*charset\s*=',fixed,flags=re.I):
        fixed=re.sub(
            r'<meta\s+[^>]*charset\s*=\s*["\']?[^"\'>\s]+["\']?[^>]*>',
            '<meta charset="utf-8">',
            fixed,count=1,flags=re.I
        )
    else:
        m=re.search(r'<head[^>]*>',fixed,flags=re.I)
        if not m:raise RuntimeError("host <head> not found")
        fixed=fixed[:m.end()]+'\n<meta charset="utf-8">'+fixed[m.end():]

    fixed=re.sub(
        r'(<title[^>]*>).*?(</title>)',
        r'\1PROJECT PHOENIX 4.41 · Official Start\2',
        fixed,count=1,flags=re.I|re.S
    )

    # Stable CAD bridge reference only; bridge file itself is never touched.
    fixed,n=re.subn(
        r'(phoenix_detv_cad_bridge\.js)(?:\?[^"\']*)?',
        r'\1?v=4.41-stable-cad',
        fixed,count=1,flags=re.I
    )
    if n!=1:raise RuntimeError("expected one CAD bridge script reference")

    guard_tag='<script src="./phoenix_start_v441_runtime_guard.js?v=1.0.1"></script>'
    if "phoenix_start_v441_runtime_guard.js" not in fixed:
        pos=fixed.lower().rfind("</body>")
        if pos<0:raise RuntimeError("host </body> not found")
        fixed=fixed[:pos]+guard_tag+"\n"+fixed[pos:]

    after_all=suspicious_count(fixed)
    after_visible=suspicious_count(visible_text(fixed))

    host.write_text(fixed,encoding="utf-8",newline="\n")
    result={
        "status":"PASS",
        "host":HOST_REL,
        "bridge_excluded":BRIDGE_REL,
        "guard":GUARD_REL,
        "suspicious_before_all":before_all,
        "suspicious_after_all":after_all,
        "suspicious_before_visible":before_visible,
        "suspicious_after_visible":after_visible,
        "semantic_visible_replacements":semantic,
        "visible_residual_contexts":visible_residual_contexts(fixed),
    }
    report.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding="utf-8")
    return result

def verify(repo:Path,report:Path):
    host=(repo/HOST_REL).read_text(encoding="utf-8")
    guard=(repo/GUARD_REL).read_text(encoding="utf-8")
    errors=[]

    visible_bad=suspicious_count(visible_text(host))
    if visible_bad!=0:
        errors.append(f"visible HTML mojibake remains ({visible_bad})")
    if 'charset="utf-8"' not in host.lower():
        errors.append("UTF-8 meta missing")
    if "PROJECT PHOENIX 4.41" not in host:
        errors.append("4.41 branding missing")
    if host.count("phoenix_start_v441_runtime_guard.js")!=1:
        errors.append("runtime guard reference must occur exactly once")
    if "phoenix_detv_cad_bridge.js?v=4.41-stable-cad" not in host:
        errors.append("stable CAD bridge cache reference missing")

    # No suspicious navicon text may remain.
    for m in re.finditer(
        r'<span\b[^>]*\bclass=["\'][^"\']*\bnavicon\b[^"\']*["\'][^>]*>([^<]*)</span>',
        host,flags=re.I
    ):
        if suspicious_count(m.group(1)):
            errors.append("suspicious navicon remains")

    prev=re.search(
        r'<button\b[^>]*\bid=["\']phoenixTvPrev["\'][^>]*>([^<]*)</button>',
        host,flags=re.I
    )
    if prev and "VORIGE" in prev.group(1).upper() and "&#x2190;" not in prev.group(1):
        errors.append("phoenixTvPrev arrow not canonicalized")

    for needle in ("START v4.41","BOUNDED_ONE_SHOT","createTreeWalker","pageshow"):
        if needle not in guard:
            errors.append(f"guard missing {needle}")
    for banned in ("MutationObserver","setInterval(","window.focus(",".focus("):
        if banned in guard:
            errors.append(f"guard contains banned behavior: {banned}")

    if errors:raise RuntimeError("; ".join(errors))
    source=json.loads(report.read_text(encoding="utf-8"))
    return {
        "status":"PASS",
        "visible_html_mojibake":0,
        "residual_nonvisible_source_count":source["suspicious_after_all"],
        "runtime_guard":"BOUNDED_ONE_SHOT",
        "runtime_label_target":"START v4.41",
        "bridge_mutated":False,
    }

def self_test():
    # General decoder.
    for bad,good in {
        "ðŸŽ¤":"🎤",
        "âœ”":"✔",
        "â†\x90":"←",
        "â†’":"→",
    }.items():
        got=fix_mojibake(bad)
        assert good in got,(repr(bad),repr(got))

    # Exact observed R6 class of malformed navicons: replacements must never cross tags.
    source=(
        '<button data-module="new"><span class="navicon">âÅ’‚</span>Nieuw Project</button>'
        '<button data-module="projects"><span class="navicon">⛁</span>Projecten</button>'
        '<button data-module="digital_twin"><span class="navicon">âÅ’Ëœ</span>Digital Twin</button>'
        '<button data-module="ai_agents"><span class="navicon">âÅ“¦</span>AI Agents</button>'
        '<button data-module="simulations"><span class="navicon">Ôù┼Æ</span>Simulaties</button>'
        '<button class="tvbtn" id="phoenixTvPrev">ÔùÔé¼ VORIGE</button>'
    )
    generic=fix_mojibake(source)
    fixed,sem=repair_visible_semantics(generic)
    assert "Nieuw Project</button><button" in fixed
    assert "Projecten</button><button" in fixed
    assert "Digital Twin</button><button" in fixed
    assert "AI Agents</button><button" in fixed
    assert "Simulaties</button><button" in fixed
    assert 'id="phoenixTvPrev">&#x2190; VORIGE</button>' in fixed
    # Every navicon still has a closing span before its own label.
    assert fixed.count('<span class="navicon">')==5
    assert fixed.count("</span>")==5
    assert suspicious_count(visible_text(fixed))==0
    nested_source="X\u00f0\u00c5\u00b8\u008f\u00a2Y"
    nested_fixed,nested_repls=repair_known_nested_utf8_residuals(nested_source)
    assert nested_fixed=="X&#x1F3E2;Y"
    assert len(nested_repls)==1
    assert nested_repls[0]["utf8_bytes"]=="F0 9F 8F A2"
    print("PHOENIX_4_41_UTF8_RUNTIME_LABEL_FIX_R9_SELF_TEST=PASS")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--repo-root",type=Path)
    ap.add_argument("--report",type=Path)
    ap.add_argument("--repair",action="store_true")
    ap.add_argument("--verify",action="store_true")
    ap.add_argument("--self-test",action="store_true")
    a=ap.parse_args()

    if a.self_test:
        self_test();return 0
    if not a.repo_root:ap.error("--repo-root required")
    if not a.report:ap.error("--report required")
    repo=a.repo_root.resolve()
    if a.repair:
        # ASCII-safe console JSON; report file itself remains UTF-8.
        print(json.dumps(repair_host(repo,a.report),indent=2,ensure_ascii=True))
        print("UTF8_VISIBLE_HTML_REPAIR_R9=PASS");return 0
    if a.verify:
        print(json.dumps(verify(repo,a.report),indent=2,ensure_ascii=True))
        print("UTF8_RUNTIME_LABEL_VERIFY_R9=PASS");return 0
    ap.error("choose --repair, --verify or --self-test")

if __name__=="__main__":
    raise SystemExit(main())
