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
