import unittest
from unittest.mock import Mock
from src.public_research import PublicResearch

class TestFreeDiscovery(unittest.TestCase):
    def test_gdelt_records_only_real_publisher_urls(self):
        collector=PublicResearch('2026-10-30')
        fake=Mock()
        fake.json.return_value={'articles':[
            {'url':'https://newsshooter.com/2026/10/30/angelbird-test/',
             'title':'Angelbird AV PRO media checked on location',
             'seendate':'20261030T101000Z'},
            {'url':'https://www.reddit.com/r/camera/comments/abc/x',
             'title':'Angelbird reply'},
            {'url':'https://unrelated.example/post',
             'title':'Generic tech story'}]}
        collector.get=lambda *args,**kwargs: (fake,'OK')
        collector.free_gdelt_news()
        self.assertIn('https://newsshooter.com/2026/10/30/angelbird-test/',
                      collector.candidates)
        self.assertNotIn('https://www.reddit.com/r/camera/comments/abc/x',
                         collector.candidates)
        self.assertNotIn('https://unrelated.example/post',collector.candidates)
        self.assertEqual(collector.counts['Industry articles.gdelt_queries'],1)

if __name__=='__main__':
    unittest.main()
