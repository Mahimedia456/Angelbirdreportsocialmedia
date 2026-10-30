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
