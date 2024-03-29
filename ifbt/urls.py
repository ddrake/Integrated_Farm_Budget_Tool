"""
URL configuration for ifbt project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from django.conf.urls.static import static
from django.conf import settings
from django.contrib.sitemaps.views import sitemap
from blog.sitemap import BlogSitemap
from main.sitemap import StaticViewSitemap

sitemaps = {
    'blog': BlogSitemap,
    'static': StaticViewSitemap,
}

urlpatterns = [
    path('', include('main.urls')),
    path('admin/', admin.site.urls),
    path('', include("django.contrib.auth.urls")),
    path('', include('account.urls')),
    path('', include('construction.urls')),
    path('impersonate/', include('impersonate.urls')),
    path('__reload__/', include('django_browser_reload.urls')),
    path('ckeditor/', include('ckeditor_uploader.urls')),
    path('', include('blog.urls')),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps},
         name="django.contrib.sitemaps.views.sitemap",),
]
if settings.DEBUG:
    # We need these to be able to see ckeditor uploaded images
    # and load content.css in develeopment
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
