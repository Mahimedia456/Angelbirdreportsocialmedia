from pydantic import BaseModel, Field, HttpUrl, field_validator
from typing import Literal
from datetime import date

class Finding(BaseModel):
    title: str
    platform: str
    url: str
    author: str = ''
    published_date: str = ''
    date_evidence: str = ''
    summary: str = ''
    sentiment: Literal['Positive','Negative','Neutral','Question','Not applicable'] = 'Neutral'
    priority: Literal['Urgent','High','Medium','Low','Watch'] = 'Low'
    status: Literal['verified','unverified','older','retail'] = 'verified'
    image_url: str = ''
    product: str = ''
    details: str = ''

    @field_validator('url')
    @classmethod
    def check_url(cls, value):
        if not value.startswith(('https://','http://')):
            raise ValueError('Evidence URL must be http(s)')
        return value

class Coverage(BaseModel):
    platform: str
    summary: str
    checked: bool = True

class ResearchReport(BaseModel):
    report_date: str
    generated_at_pkt: str = ''
    status: str = 'Evening monitoring run'
    headline: str = ''
    today_findings: list[Finding] = Field(default_factory=list)
    retail_observations: list[Finding] = Field(default_factory=list)
    unverified_leads: list[Finding] = Field(default_factory=list)
    older_leads: list[Finding] = Field(default_factory=list)
    coverage: list[Coverage] = Field(default_factory=list)
    visibility_gaps: list[str] = Field(default_factory=list)
    methodology: str = ''

    @field_validator('report_date')
    @classmethod
    def check_date(cls, value):
        date.fromisoformat(value)
        return value

    def enforce_date_guardrails(self):
        good=[]
        for item in self.today_findings:
            if item.status=='verified' and item.published_date == self.report_date and item.date_evidence.strip():
                good.append(item)
            else:
                item.status='unverified'
                self.unverified_leads.append(item)
        # Deterministically collapse duplicate first-party URLs across sweeps.
        seen=set()
        unique=[]
        for item in good:
            key=item.url.rstrip("/").lower()
            if key not in seen:
                seen.add(key)
                unique.append(item)
        self.today_findings=unique
        retail=[]
        for item in self.retail_observations:
            item.status='retail'
            retail.append(item)
        seen_retail=set()
        self.retail_observations=[]
        for item in retail:
            key=item.url.rstrip("/").lower()
            if key not in seen_retail:
                seen_retail.add(key)
                self.retail_observations.append(item)
        return self
