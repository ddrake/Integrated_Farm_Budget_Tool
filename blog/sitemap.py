from django.contrib.sitemaps import Sitemap
from blog.models import BlogPost


class BlogSitemap(Sitemap):
    changefreq = "never"
    priority = 0.5

    def items(self):
        return BlogPost.objects.filter(published__isnull=False)

    def lastmod(self, obj):
        return obj.published
