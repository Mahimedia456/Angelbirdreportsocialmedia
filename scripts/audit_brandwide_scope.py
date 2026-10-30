"""Small offline contract checks for brand-wide query and catalog behavior."""
import json
from pathlib import Path
from src.social_search_queries import BRAND,GROUPS

ROOT=Path(__file__).resolve().parents[1]
REQUIRED=('Facebook','Instagram','LinkedIn','X / Twitter','Reddit',
          'YouTube','Camera forums','Industry articles','Retailers')
def main():
    missing=[x for x in REQUIRED if x not in GROUPS]
    if missing:raise AssertionError('Missing discovery platform: '+str(missing))
    for platform in REQUIRED:
        queries=GROUPS[platform]
        if len(queries)<3:raise AssertionError('Not enough broad queries: '+platform)
        for q in queries[:2]:
            if BRAND.lower() not in q.lower():raise AssertionError('Brand missing: '+platform)
            try:q.format(date='2026-10-31',year=2026,month='October')
            except Exception as e:raise AssertionError(platform) from e
    if BRAND=='Atomos':
        from src.brand_scope import is_atomos_equipment
        for text in ('Atomos customer support and warranty experience',
                     'Atomos new audio product launch',
                     'Atomos cloud service account issue'):
            assert is_atomos_equipment(text),text
        assert not is_atomos_equipment('FFXIV Atomos server raid')
    print(json.dumps({'brand':BRAND,'platforms':len(REQUIRED),
                      'platform_search_query_count':sum(map(len,GROUPS.values())),
                      'scope':'all products and company-level mentions'}))
if __name__=='__main__':main()
