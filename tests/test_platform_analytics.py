import unittest
from unittest.mock import Mock
from src.platform_analytics import PLATFORMS, category, analytics_rows, metric_summary, platform_summary
from src.schema import Finding
from src.public_research import PublicResearch

def item(url, platform=''):
    return Finding(url=url, title='Angelbird media',platform=platform,
                   source_excerpt='Angelbird memory cards',published_date='2026-10-30',
                   date_evidence='Original page publication timestamp',status='verified')

class TestPlatformAnalytics(unittest.TestCase):
    def test_sections_group_all_networks(self):
        sources=[
            ('https://facebook.com/creator/posts/123','Facebook'),
            ('https://www.instagram.com/p/AbCdEF/','Instagram'),
            ('https://x.com/author/status/123','X / Twitter'),
            ('https://www.linkedin.com/posts/author_abc','LinkedIn'),
            ('https://reddit.com/r/cameras/comments/abc','Reddit'),
            ('https://www.youtube.com/watch?v=qAl9K4dgiTc','YouTube'),
            ('https://www.dpreview.com/forums/thread/222','Camera Forums'),
            ('https://www.newsshooter.com/article','Google / News / Articles'),
            ('https://www.bhphotovideo.com/c/product/123','Retailers'),
        ]
        records=[item(url) for url,section in sources]
        groups=platform_summary(records)
        self.assertEqual(tuple(groups),PLATFORMS)
        for _, section in sources:self.assertEqual(len(groups[section]),1)
    def test_missing_engagement_is_unknown_not_zero(self):
        a=item('https://www.instagram.com/p/test/')
        b=item('https://www.youtube.com/watch?v=qAl9K4dgiTc')
        b.engagement={'views':2040,'likes':140,'comments':0}
        b.engagement_source='YouTube Data API videos.list statistics'
        metrics=metric_summary([a,b])
        self.assertEqual(metrics['totals']['views'],2040)
        self.assertIn('comments',metrics['available'])
        self.assertNotIn('shares',metrics['available'])
        self.assertEqual(metrics['posts_with_public_metrics'],1)
        self.assertEqual(metrics['posts_total'],2)
    def test_textual_estimate_not_exact_traffic(self):
        f=item('https://x.com/creator/status/44')
        f.engagement={'views':'about 1.2K','impressions':123456,'likes':'1,245'}
        m=metric_summary([f])
        self.assertNotIn('views',m['available'])
        self.assertNotIn('impressions',m['totals'])
        self.assertEqual(m['totals']['likes'],1245)
    def test_youtube_public_video_metrics_are_source_backed(self):
        c=PublicResearch('2026-10-30')
        def fake_get(url,params=None,**kw):
            result=Mock()
            if url.endswith('/search'):
                result.json.return_value={'items':[{
                    'id':{'videoId':'qAl9K4dgiTc'},
                    'snippet':{'title':'Angelbird Raven Black camera review',
                               'description':'Angelbird card field notes',
                               'publishedAt':'2026-10-30T12:00:00Z',
                               'channelTitle':'Camera Reviewer',
                               'thumbnails':{'medium':{'url':'https://i.ytimg.com/test.jpg'}}}
                }]}
            elif url.endswith('/videos'):
                result.json.return_value={'items':[{'id':'qAl9K4dgiTc',
                    'statistics':{'viewCount':'2412','likeCount':'71','commentCount':'9'}}]}
            else:
                result.json.return_value={'items':[]}
            return result,'OK'
        c.get=fake_get
        import os
        from unittest.mock import patch
        with patch.dict(os.environ,{'YOUTUBE_API_KEY':'mock-key',
                                    'YT_MAX_COMMENT_VIDEOS':'1'}):
            c.youtube()
        self.assertEqual(len(c.findings),1)
        self.assertEqual(c.counts['YouTube.api_searches'],1)
        self.assertEqual(c.counts['YouTube.statistics_calls'],1)
        self.assertEqual(c.counts['YouTube.comments_calls'],1)
        self.assertEqual(c.findings[0].engagement['views'],2412)
        self.assertEqual(c.findings[0].engagement['likes'],71)
        self.assertEqual(c.findings[0].engagement['comments'],9)
        self.assertEqual(c.findings[0].engagement_source,
                         'YouTube Data API videos.list statistics')

    def test_original_author_and_publisher(self):
        c=PublicResearch('2026-10-30')
        html='<html><head><meta property="article:published_time" content="2026-10-30T10:00:00Z"><meta property="og:site_name" content="Cine News"><meta name="author" content="Journalist A"><meta property="og:image" content="/media/photo.jpg"></head><body><article>Angelbird AV PRO V90 card tested by author.</article></body></html>'
        response=Mock()
        response.url='https://cinenews.example.com/story'
        response.text=html
        response.headers={'content-type':'text/html'}
        c.get=lambda *args,**kwargs:(response,'OK')
        c.page({'url':response.url,'group':'Industry articles'})
        self.assertEqual(c.findings[0].author,'Journalist A')
        self.assertEqual(c.findings[0].publisher,'Cine News')
        self.assertEqual(c.findings[0].image_url,'https://cinenews.example.com/media/photo.jpg')

if __name__=='__main__':
    unittest.main()
