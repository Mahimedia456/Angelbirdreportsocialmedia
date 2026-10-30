"""Research evidence data contract and conservative AI-output normalization."""
import json
from datetime import date
import re
from typing import Literal
from urllib.parse import urlparse
from pydantic import BaseModel, Field, field_validator, model_validator

def text_value(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)

class Finding(BaseModel):
    title: str = ''
    platform: str = ''
    url: str
    author: str = ''
    published_date: str = ''
    date_evidence: str = ''
    summary: str = ''
    sentiment: Literal['Positive','Negative','Neutral','Question','Not applicable'] = 'Not applicable'
    priority: Literal['Urgent','High','Medium','Low','Watch'] = 'Watch'
    status: Literal['verified','unverified','older','retail'] = 'unverified'
    image_url: str = ''
    product: str = ''
    details: str = ''
    source_excerpt: str = ''
    response_action: str = ''
    impact: str = ''
    verification_note: str = ''
    reference_date: str = ''
    engagement: dict = Field(default_factory=dict)
    images: list[str] = Field(default_factory=list)

    @model_validator(mode='before')
    @classmethod
    def normalize_ai_fields(cls, data):
        if not isinstance(data, dict):
            raise ValueError('Finding must be an object')
        d = dict(data)
        for key in ('title','platform','url','author','published_date','date_evidence','summary','image_url','product','details','source_excerpt','response_action','impact','verification_note','reference_date'):
            if key in d:
                d[key] = text_value(d[key])
        if isinstance(d.get('published_date'), str) and d['published_date'].lower() in ('none','null','unknown','undated','n/a'):
            d['published_date'] = ''
        if not isinstance(d.get('engagement'),dict): d['engagement']={}
        if not isinstance(d.get('images'),list): d['images']=[]
        d['images']=[text_value(u) for u in d['images'] if text_value(u).startswith(('https://','http://'))]
        raw_sent = text_value(d.get('sentiment')).lower()
        sentiments = {x.lower():x for x in ('Positive','Negative','Neutral','Question','Not applicable')}
        # Composite/unclear sentiments must NOT silently become positive or negative.
        d['sentiment'] = sentiments.get(raw_sent, 'Not applicable')
        raw_priority = text_value(d.get('priority')).lower()
        priorities = {x.lower():x for x in ('Urgent','High','Medium','Low','Watch')}
        d['priority'] = priorities.get(raw_priority, 'Watch')
        raw_status = text_value(d.get('status')).lower()
        # Never promote AI-provided prose statuses to a verified claim.
        d['status'] = raw_status if raw_status in ('verified','unverified','older','retail') else 'unverified'
        return d

    @field_validator('url')
    @classmethod
    def check_url(cls, value):
        parsed = urlparse(value)
        if parsed.scheme not in ('http','https') or not parsed.netloc:
            raise ValueError('Evidence URL must be http(s)')
        return value

class Coverage(BaseModel):
    platform: str = ''
    summary: str = ''
    checked: bool = False

    @model_validator(mode='before')
    @classmethod
    def normalize_coverage(cls, value):
        if not isinstance(value, dict):
            return {'platform':text_value(value),'summary':'Coverage detail not supplied','checked':False}
        d=dict(value)
        d['platform']=text_value(d.get('platform'))
        d['summary']=text_value(d.get('summary'))
        d['checked']=d.get('checked') is True
        return d

class ResearchReport(BaseModel):
    report_date: str
    generated_at_pkt: str = ''
    status: str = 'Evening monitoring run'
    headline: str = ''
    today_findings: list[Finding] = Field(default_factory=list)
    retail_observations: list[Finding] = Field(default_factory=list)
    unverified_leads: list[Finding] = Field(default_factory=list)
    older_leads: list[Finding] = Field(default_factory=list)
    historical_findings: list[Finding] = Field(default_factory=list)
    historical_retail: list[Finding] = Field(default_factory=list)
    report_period_start: str = ''
    report_period_end: str = ''
    coverage: list[Coverage] = Field(default_factory=list)
    visibility_gaps: list[str] = Field(default_factory=list)
    methodology: str = ''

    @model_validator(mode='before')
    @classmethod
    def normalize_report(cls, data):
        if not isinstance(data, dict):
            raise ValueError('Report must be a JSON object')
        d=dict(data)
        for key in ('report_date','generated_at_pkt','status','headline','methodology','report_period_start','report_period_end'):
            if key in d: d[key]=text_value(d[key])
        # LLMs sometimes return source coverage as a {platform: summary} map.
        # Preserve it as unverified index-search notes, not proof of direct platform reads.
        if isinstance(d.get('coverage'), dict):
            d['coverage']=[{'platform':str(k),'summary':text_value(v),'checked':False}
                           for k,v in d['coverage'].items()]
        if isinstance(d.get('visibility_gaps'), str):
            d['visibility_gaps']=[d['visibility_gaps']]
        for bucket in ('today_findings','retail_observations','unverified_leads','older_leads','historical_findings','historical_retail','coverage','visibility_gaps'):
            if not isinstance(d.get(bucket), list): d[bucket]=[]
        # Invalid or missing source URLs are not evidence. Keep summary note, not a fabricated record.
        rejected=0
        for bucket in ('today_findings','retail_observations','unverified_leads','older_leads','historical_findings','historical_retail'):
            kept=[]
            for item in d[bucket]:
                # Pydantic also accepts already constructed Finding instances.
                # Do not silently discard valid typed records during revalidation.
                url = item.url if isinstance(item, Finding) else item.get('url') if isinstance(item, dict) else ''
                parsed = urlparse(text_value(url))
                if parsed.scheme in ('http', 'https') and parsed.netloc:
                    kept.append(item)
                else:
                    rejected+=1
            d[bucket]=kept
        if rejected:
            gaps=d['visibility_gaps']
            gaps.append(f'{rejected} candidate records without valid original URLs excluded from report.')
        d['visibility_gaps']=[text_value(x) for x in d['visibility_gaps']]
        return d

    @field_validator('report_date')
    @classmethod
    def check_date(cls, value):
        date.fromisoformat(value)
        return value

    def enforce_date_guardrails(self):
        verified=[]
        exclusions=0
        for item in self.today_findings:
            # A generic platform article is NOT an Angelbird mention. An excerpt
            # of the actual source wording is required before the verified KPI.
            excerpt=item.source_excerpt or ''
            direct=bool(re.search(r'\bangelbird\b|\bav[ -]?pro\b',excerpt,re.I))
            if not direct:
                exclusions+=1
                continue
            if (item.status=='verified' and item.published_date==self.report_date
                and len(item.date_evidence.strip())>=12):
                verified.append(item)
            else:
                item.status='unverified'
                self.unverified_leads.append(item)
        if exclusions:
            self.visibility_gaps.append(f'{exclusions} candidate items excluded: no direct Angelbird mention in original-source excerpt.')
        seen=set()
        self.today_findings=[]
        for item in verified:
            key=item.url.rstrip('/').lower()
            if key not in seen:
                seen.add(key); self.today_findings.append(item)
        seen_retail=set()
        distinct=[]
        for item in self.retail_observations:
            item.status='retail'
            # Retail offers are not social sentiment, regardless of AI labels.
            item.sentiment='Not applicable'
            key=item.url.rstrip('/').lower()
            if key not in seen_retail:
                seen_retail.add(key); distinct.append(item)
        self.retail_observations=distinct
        for item in self.older_leads:
            item.status='older'
        for item in self.unverified_leads:
            item.status='unverified'
        return self
