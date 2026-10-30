"""Automatic public discovery queries. No supplied example links become findings.
All search hits still require original-source evidence before verified KPI inclusion.
"""
BRAND="Angelbird"
GROUPS={
 'Facebook':[
    'site:facebook.com/posts/ "Angelbird" {date}',
    'site:facebook.com "Angelbird" camera creator tagged mentions {month} {year}',
    'site:facebook.com/reel/ "Angelbird" video production {month} {year}'],
 'Instagram':[
    'site:instagram.com/p/ "Angelbird" {month} {year}',
    'site:instagram.com/reel/ "Angelbird" {month} {year}',
    'site:instagram.com/stories/ "Angelbird" {month} {year}',
    'site:instagram.com "Angelbird" hashtag mention tagged creator {date}'],
 'LinkedIn':[
    'site:linkedin.com/posts/ "Angelbird" {date}',
    'site:linkedin.com/feed/update/ "Angelbird" {month} {year}'],
 'X / Twitter':[
    'site:x.com/status/ "Angelbird" {date}',
    'site:twitter.com "Angelbird" review mention {month} {year}'],
 'Reddit':[
    'site:reddit.com/r/ "Angelbird" {date}',
    'site:reddit.com/r/ "Angelbird" camera product problems {month} {year}'],
 'YouTube':['site:youtube.com/watch "Angelbird" {date}'],
 'Camera forums':[
    'site:dpreview.com/forums "Angelbird" {date}',
    '"Angelbird" hands-on camera production forum {month} {year}'],
 'Industry articles':[
    'site:newsshooter.com "Angelbird" {month} {year}',
    'site:cined.com "Angelbird" {month} {year}',
    '"Angelbird" video production review article {date}'],
 'Retailers':[
    'site:bhphotovideo.com "Angelbird" {month} {year}',
    'site:cvp.com "Angelbird" {month} {year}']
}

# Extra device-level public discovery. Candidates remain unverified until original-source validation.
for _group,_queries in {"Facebook":["site:facebook.com \"Angelbird\" \"CFexpress\" {month} {year}","site:facebook.com \"AV PRO\" \"Angelbird\" {month} {year}","site:facebook.com/groups/ \"Angelbird\" \"card\" {month} {year}"],"Instagram":["site:instagram.com/p/ \"angelbird\" \"CFexpress\" {month} {year}","site:instagram.com/reel/ \"angelbird\" \"SSD\" {month} {year}","site:instagram.com \"angelbirdmedia\" \"{month}\" \"{year}\""],"LinkedIn":["site:linkedin.com/posts/ \"Angelbird\" \"CFexpress\" {month} {year}","site:linkedin.com/posts/ \"Angelbird\" \"AV PRO\" {month} {year}"],"X / Twitter":["site:x.com/ \"Angelbird\" \"CFexpress\" {month} {year}","site:x.com/ \"Angelbird\" \"AV PRO\" {month} {year}"],"Camera forums":["site:dpreview.com/forums \"Angelbird\" \"card\" {month} {year}","site:forum.blackmagicdesign.com \"Angelbird\" \"{month}\" \"{year}\"","site:reddit.com/r/cinematography \"Angelbird\" {month} {year}"]}.items():
    GROUPS[_group].extend(_queries)

# Additional source-discovery queries: public Meta content requires original-source proof.
GROUPS['Facebook'].extend([
  "site:facebook.com \"Angelbird\" \"CFexpress\" {month} {year}",
  "site:facebook.com \"Angelbird\" \"AV PRO\" {month} {year}",
  "site:facebook.com \"Angelbird\" \"CFast\" {month} {year}",
  "site:facebook.com \"Angelbird\" \"SSD2GO\" {month} {year}",
  "site:facebook.com/angelbirdmedia/posts/ {month} {year}",
  "site:facebook.com/AngelbirdTechnologies/posts/ {month} {year}",
  "site:facebook.com/reel/ \"Angelbird\" {month} {year}",
  "site:facebook.com/groups/ \"Angelbird\" \"card\" {month} {year}",
  "site:facebook.com/photo/ \"Angelbird\" {month} {year}",
  "\"Angelbird\" Facebook filmmaker review {month} {year}"
])

# Brand-first discovery is the foundation. These search themes apply to EVERY
# present, discontinued, new, legacy, accessory and unlisted product, as well
# as company-wide service, firmware, creator and partnership mentions.
# Named model queries elsewhere are optional supplements, never filters.
_BROAD_BRAND_QUERIES={
  "Facebook": [
    "site:facebook.com \"{brand}\" {date}",
    "site:facebook.com \"{brand}\" support OR firmware OR update OR customer {month} {year}",
    "site:facebook.com \"{brand}\" launch OR event OR review OR unboxing {month} {year}",
    "site:facebook.com \"{brand}\" reel OR livestream OR story {month} {year}",
    "site:facebook.com/groups/ \"{brand}\" user experience {month} {year}",
    "site:facebook.com \"{brand}\" seller OR dealer OR reseller {month} {year}"
  ],
  "Instagram": [
    "site:instagram.com \"{brand}\" {date}",
    "site:instagram.com \"{brand}\" tagged creator {month} {year}",
    "site:instagram.com/reel/ \"{brand}\" {month} {year}",
    "site:instagram.com/p/ \"{brand}\" {month} {year}",
    "site:instagram.com \"{brand}\" review OR tutorial OR launch {month} {year}"
  ],
  "LinkedIn": [
    "site:linkedin.com/posts/ \"{brand}\" {month} {year}",
    "site:linkedin.com \"{brand}\" product OR partnership OR event {month} {year}",
    "site:linkedin.com \"{brand}\" dealer OR trade show OR news {date}"
  ],
  "X / Twitter": [
    "site:x.com \"{brand}\" {date}",
    "site:x.com/status/ \"{brand}\" support OR review {month} {year}",
    "site:twitter.com \"{brand}\" announcement OR customer {month} {year}"
  ],
  "Reddit": [
    "site:reddit.com \"{brand}\" {date}",
    "site:reddit.com/r/ \"{brand}\" review OR compatibility {month} {year}",
    "site:reddit.com \"{brand}\" firmware OR problem OR recommendation {month} {year}"
  ],
  "YouTube": [
    "site:youtube.com/watch \"{brand}\" {date}",
    "site:youtube.com \"{brand}\" review OR tutorial {month} {year}",
    "site:youtube.com \"{brand}\" live OR shorts OR first impressions {month} {year}"
  ],
  "Camera forums": [
    "\"{brand}\" camera forum compatibility {month} {year}",
    "site:dpreview.com/forums \"{brand}\" {date}",
    "site:forum.blackmagicdesign.com \"{brand}\" {date}",
    "site:forums.red.com \"{brand}\" {date}",
    "site:community.sony.com \"{brand}\" {month} {year}"
  ],
  "Industry articles": [
    "\"{brand}\" industry news {date}",
    "\"{brand}\" review or release or firmware {month} {year}",
    "site:newsshooter.com \"{brand}\" {month} {year}",
    "site:cined.com \"{brand}\" {month} {year}",
    "site:petapixel.com \"{brand}\" {month} {year}"
  ],
  "Retailers": [
    "\"{brand}\" buy reseller inventory {month} {year}",
    "site:bhphotovideo.com \"{brand}\" {month} {year}",
    "site:cvp.com \"{brand}\" {month} {year}",
    "site:adorama.com \"{brand}\" {month} {year}",
    "site:wexphotovideo.com \"{brand}\" {month} {year}",
    "site:proav.co.uk \"{brand}\" {month} {year}",
    "site:galaxus.com \"{brand}\" {month} {year}"
  ]
}
for _platform,_broad in _BROAD_BRAND_QUERIES.items():
    GROUPS[_platform]=[q.replace('{brand}',BRAND) for q in _broad]+GROUPS.get(_platform,[])
