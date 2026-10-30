"""Enforce single-date reporting and exclude archived or undated evidence from KPIs."""
from .schema import ResearchReport

def scope_to_day(report: ResearchReport):
    day=report.report_date
    report=report.enforce_date_guardrails()
    report.today_findings=[f for f in report.today_findings
                           if f.published_date==day and f.status=='verified']
    # A retail listing is a DAY snapshot only when its snapshot observation date
    # explicitly matches the chosen day; modification dates aren't new posts.
    report.retail_observations=[f for f in report.retail_observations
                                if f.reference_date==day]
    # Leads without proven source dates may be surfaced only when specifically
    # observed on this reporting day, clearly labelled as unverified.
    report.unverified_leads=[f for f in report.unverified_leads
                             if f.reference_date==day]
    # Do not add previous-day archives anywhere in the dated PDF or JSON.
    report.historical_findings=[]
    report.historical_retail=[]
    report.older_leads=[]
    report.report_period_start=day
    report.report_period_end=day
    return report
