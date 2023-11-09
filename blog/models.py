from django.db import models
# from django.db.models import F
from django.contrib.auth.models import User
from django.urls import reverse
from django.conf import settings
from ckeditor_uploader.fields import RichTextUploadingField


class Blog(models.Model):
    title = models.CharField(max_length=60)

    def __str__(self):
        return self.title


class BlogPost(models.Model):
    blog = models.ForeignKey(Blog, on_delete=models.CASCADE, related_name='posts',
                             default=settings.BLOG_ID)
    author = models.ForeignKey(User, on_delete=models.CASCADE,
                               default=settings.BLOG_AUTHOR_ID)
    title = models.CharField(max_length=60)
    slug = models.SlugField(max_length=60)
    content = RichTextUploadingField(config_name='custom')
    published = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('post', kwargs={'pk': self.pk, 'slug': self.slug})

    class Meta:
        # ordering = [F("published").desc(nulls_last=False)]
        ordering = ['-published']
