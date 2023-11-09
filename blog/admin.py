from django.contrib import admin

from .models import Blog
from .models import BlogPost


# Once created, can remove from admin
class BlogAdmin(admin.ModelAdmin):
    pass


class BlogPostAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ["title"]}


admin.site.register(Blog, BlogAdmin)
admin.site.register(BlogPost, BlogPostAdmin)
