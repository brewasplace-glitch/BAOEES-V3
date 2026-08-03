"""Phoenix Public Real-World HTML Source Integration v1.0.

Normalizes explicitly configured public supplier/product pages to Phoenix
market-price and material-supply contracts. The parser is conservative:
commercial availability may be confirmed from an orderable local listing, but
structural engineering qualification is never inferred from a price/title.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Any

VERSION="1.0.0"

class _HTMLTextParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts=[]
        self._skip=0
        self._jsonld=False
        self.jsonld=[]
        self._buffer=[]
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag in {"script","style","noscript"}:
            if tag=="script" and "ld+json" in str(attrs.get("type") or "").lower():
                self._jsonld=True;self._buffer=[]
            else:self._skip+=1
        if tag in {"br","p","div","li","h1","h2","h3","h4","tr","td","section","article"} and not self._skip:
            self.parts.append("\n")
    def handle_endtag(self,tag):
        if tag=="script" and self._jsonld:
            self._jsonld=False
            raw="".join(self._buffer).strip()
            if raw:self.jsonld.append(raw)
            self._buffer=[]
        elif tag in {"script","style","noscript"} and self._skip:
            self._skip-=1
        if tag in {"p","div","li","h1","h2","h3","h4","tr","section","article"} and not self._skip:
            self.parts.append("\n")
    def handle_data(self,data):
        if self._jsonld:self._buffer.append(data);return
        if self._skip:return
        value=re.sub(r"\s+"," ",html.unescape(data or "")).strip()
        if value:self.parts.append(value+" ")

def visible_text(raw:bytes)->tuple[str,list[Any]]:
    parser=_HTMLTextParser();parser.feed(raw.decode('utf-8',errors='ignore'))
    text="".join(parser.parts)
    text=re.sub(r"[ \t]+"," ",text)
    text=re.sub(r"\n\s*\n+","\n",text)
    objects=[]
    for block in parser.jsonld:
        try:
            obj=json.loads(block)
            objects.append(obj)
        except Exception:pass
    return text.strip(),objects

def _money(value:str)->float|None:
    raw=str(value or '').strip().replace(' ','')
    if not raw:return None
    if ',' in raw and '.' in raw:
        if raw.rfind(',')>raw.rfind('.'):
            raw=raw.replace('.','').replace(',','.')
        else:raw=raw.replace(',','')
    elif ',' in raw:
        raw=raw.replace('.','').replace(',','.')
    try:return float(raw)
    except ValueError:return None

def _family(name:str)->str:
    low=str(name or '').casefold()
    if any(x in low for x in ('beton ijzer','betonijzer','wapening','rebar')):return 'reinforcement_steel'
    if any(x in low for x in ('constructie buis','constructiebuis','steel tube','stalen profiel','steel profile','galvaan 50x','galvaan 60x','galvaan 80x')):return 'structural_steel_section'
    if any(x in low for x in ('steen 4','steen 6','steen 8','block','bouwsteen','hollow block','solid block','lintel block','masonry')):return 'masonry_unit'
    if any(x in low for x in ('hout ','timber','walaba','soemaroeba','hardhout')):return 'structural_timber'
    if any(x in low for x in ('cement','hydraulic cement')):return 'cement_binder'
    if any(x in low for x in ('zand','grind','steenslag','aggregate')):return 'aggregate'
    if any(x in low for x in ('betonmortel','ready mix','ready-mix','betonspecie')):return 'structural_concrete'
    if any(x in low for x in ('dakplaat','roof','dakbedekking')):return 'roof_covering'
    return 'other'

def _technical(name:str,family:str)->dict[str,Any]:
    low=str(name or '')
    out={}
    if family=='reinforcement_steel':
        m=re.search(r"(?i)(?:rond|ijzer|rebar)\s*(\d{1,2})\b",low)
        if m:out['diameter_mm']=float(m.group(1));out['product_form']='deformed_bar_candidate'
    elif family=='structural_steel_section':
        m=re.search(r"(?i)(\d{2,3})\s*[xX]\s*(\d{2,3})(?:\s*[xX]\s*(\d+(?:[.,]\d+)?))?",low)
        if m:
            out['section_width_mm']=float(m.group(1));out['section_height_mm']=float(m.group(2))
            if m.group(3):out['wall_thickness_mm']=float(m.group(3).replace(',','.'))
            out['product_form']='commercial_hollow_section_candidate'
    elif family=='structural_timber':
        m=re.search(r"(?i)\b(\d+(?:\s+1/2)?)\s*[xX]\s*(\d+(?:\s+1/2)?)\b",low)
        if m:out['nominal_size_text']=m.group(0)
    elif family=='masonry_unit':
        m=re.search(r"(?i)\b(\d{1,2})\s*(?:''|\"|inch)",low)
        if m:out['nominal_thickness_in']=int(m.group(1))
    return out

def _availability(segment:str)->str:
    low=str(segment or '').casefold()
    if any(x in low for x in ('uitverkocht','out of stock','niet beschikbaar')):return 'OUT_OF_STOCK'
    if any(x in low for x in ('beperkte voorraad','limited stock')):return 'LIMITED_STOCK'
    # Kuldipsingh public webshop uses 'Alleen beschikbaar in de winkels' for
    # locally available store products. Treat this as commercial availability,
    # never as structural engineering qualification.
    if 'alleen beschikbaar in de winkels' in low:return 'AVAILABLE_TO_ORDER'
    if any(x in low for x in ('beschikbaar','toevoegen','add to cart','select options','bestel')):return 'AVAILABLE_TO_ORDER'
    return 'UNKNOWN'

def _unit(name:str)->str:
    low=str(name or '').casefold()
    m=re.search(r"\b(\d+)\s*kg\b",low)
    if m:return f"bag_{m.group(1)}kg"
    if 'm3' in low or 'm³' in low:return 'm3'
    return 'piece'

def _flatten_jsonld(obj:Any)->list[dict[str,Any]]:
    out=[]
    if isinstance(obj,list):
        for x in obj:out.extend(_flatten_jsonld(x))
    elif isinstance(obj,dict):
        typ=str(obj.get('@type') or '').lower()
        if typ=='product':out.append(obj)
        for key in ('@graph','itemListElement','mainEntity'):
            if key in obj:out.extend(_flatten_jsonld(obj[key]))
    return out

def extract_products(raw:bytes,provider:dict[str,Any],acquired_at:str)->list[dict[str,Any]]:
    text,jsonlds=visible_text(raw)
    rows=[]
    seen=set()
    currency=str(provider.get('currency') or 'SRD').upper()

    # Prefer structured Product JSON-LD when available.
    for block in jsonlds:
        for product in _flatten_jsonld(block):
            name=str(product.get('name') or '').strip()
            offers=product.get('offers') or {}
            if isinstance(offers,list):offers=offers[0] if offers else {}
            price=_money(str(offers.get('price') or '')) if isinstance(offers,dict) else None
            cur=str((offers or {}).get('priceCurrency') or currency).upper() if isinstance(offers,dict) else currency
            if not name or price is None:continue
            key=(name.casefold(),price,cur)
            if key in seen:continue
            seen.add(key)
            family=_family(name);tech=_technical(name,family)
            rows.append({'name':name,'price':price,'currency':cur,'availability':'AVAILABLE_TO_ORDER','family':family,'technical':tech,'unit':_unit(name),'source_segment':'JSON_LD'})

    # Generic visible-text parser: deliberately limited to explicit currency-price pairs.
    cur_pat=r"(?:SRD|US\$|USD|\$)"
    pattern=re.compile(rf"(?P<name>[A-Za-zÀ-ÿ0-9][A-Za-zÀ-ÿ0-9#/'\"().&+\- xX]{{2,100}}?)\s*(?P<cur>{cur_pat})\s*(?P<price>\d[\d.,]*)",re.I)
    matches=list(pattern.finditer(text))
    for idx,m in enumerate(matches):
        name=re.sub(r"\s+"," ",m.group('name')).strip(' -–|')
        # Trim common category prefixes without discarding the actual title.
        for prefix in ('Cement & Beton ','Bouwstenen & Blokken ','Wapening & Metaal ','Hout ','Zand & Grind '):
            if name.startswith(prefix) and len(name)>len(prefix)+2:name=name[len(prefix):]
        price=_money(m.group('price'))
        cur=m.group('cur').upper().replace('US$','USD').replace('$','USD')
        if price is None or not name:continue
        end=matches[idx+1].start() if idx+1<len(matches) else min(len(text),m.end()+100)
        segment=text[m.start():end]
        key=(name.casefold(),price,cur)
        if key in seen:continue
        seen.add(key)
        family=_family(name);tech=_technical(name,family)
        rows.append({'name':name,'price':price,'currency':cur,'availability':_availability(segment),'family':family,'technical':tech,'unit':_unit(name),'source_segment':segment[:180]})

    # Provider-declared capability records are accepted only after the public evidence URL fetched successfully.
    for cap in provider.get('capability_records',[]):
        if not isinstance(cap,dict):continue
        name=str(cap.get('description') or cap.get('product_id') or '').strip()
        if not name:continue
        rows.append({
            'name':name,'price':None,'currency':str(cap.get('currency') or currency).upper(),
            'availability':str(cap.get('availability_status') or 'AVAILABLE_TO_ORDER').upper(),
            'family':str(cap.get('material_family') or 'other'),
            'technical':cap.get('technical_properties') if isinstance(cap.get('technical_properties'),dict) else {},
            'unit':str(cap.get('unit') or 'project_quote'),
            'source_segment':'CONFIGURED_CAPABILITY_FROM_FETCHED_PUBLIC_EVIDENCE',
            'capability_record':cap,
        })
    return rows

def normalize_material_catalog(raw:bytes,provider:dict[str,Any],acquired_at:str)->dict[str,Any]:
    rows=extract_products(raw,provider,acquired_at)
    md={
        'catalog_id':provider.get('provider_id'),
        'supplier_id':provider.get('supplier_id') or provider.get('provider_id'),
        'supplier_name':provider.get('supplier_name') or provider.get('source_name') or provider.get('provider_id'),
        'country_code':provider.get('country_code') or 'SR',
        'region_name':provider.get('region_name') or 'Paramaribo',
        'city':provider.get('municipality') or 'Paramaribo',
        'currency':provider.get('currency') or 'SRD',
        'source_name':provider.get('source_name') or provider.get('provider_id'),
        'source_url':provider.get('url'),
        'confidence':provider.get('confidence') or 'MEDIUM',
        'availability_verified_date':acquired_at[:10],
        'availability_valid_until':None,
        'market_scope':'LOCAL',
    }
    products=[]
    for i,row in enumerate(rows,1):
        cap=row.get('capability_record') or {}
        tech=dict(row.get('technical') or {})
        engineering_id=cap.get('engineering_material_id')
        products.append({
            'product_id':cap.get('product_id') or f"{provider.get('provider_id')}-P{i:04d}",
            'supplier_product_code':cap.get('supplier_product_code'),
            'manufacturer':cap.get('manufacturer'),
            'description':row['name'],
            'material_family':row['family'],
            'engineering_material_id':engineering_id,
            'technical_properties':tech,
            'availability_status':row['availability'],
            'availability_verified_date':acquired_at[:10],
            'unit':row['unit'],
            'unit_price':row['price'],
            'currency':row['currency'],
            'price_date':acquired_at[:10] if row['price'] is not None else None,
            'source_evidence_excerpt':row.get('source_segment'),
            'confidence':provider.get('confidence') or 'MEDIUM',
        })
    return {'metadata':md,'products':products}

def normalize_market_ratebook(raw:bytes,provider:dict[str,Any],acquired_at:str)->dict[str,Any]:
    rows=extract_products(raw,provider,acquired_at)
    required_currency=str(provider.get('currency') or 'SRD').upper()
    prices=[]
    for i,row in enumerate(rows,1):
        if row.get('price') is None or row.get('currency')!=required_currency:continue
        prices.append({
            'item_code':f"{provider.get('provider_id')}-{i:04d}",
            'description':row['name'],'unit':row['unit'],'unit_price':row['price'],
            'material_family':row['family'],'availability_status':row['availability'],
        })
    return {
        'metadata':{
            'ratebook_id':provider.get('provider_id'),
            'title':provider.get('title') or provider.get('source_name') or provider.get('provider_id'),
            'country_code':provider.get('country_code') or 'SR','region_name':provider.get('region_name') or 'Paramaribo',
            'city':provider.get('municipality') or 'Paramaribo','currency':required_currency,
            'effective_date':acquired_at[:10],'source_name':provider.get('source_name') or provider.get('provider_id'),
            'source_url':provider.get('url'),'taxes_included':provider.get('taxes_included'),
            'transport_included':provider.get('transport_included'),
            'confidence':provider.get('confidence') or 'MEDIUM',
        },
        'prices':prices,
    }
