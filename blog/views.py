from django.views.generic import DetailView, ListView
from django.http import Http404
from .models import BlogPost


class PostDetailView(DetailView):
    model = BlogPost
    template_name = 'blog/post_detail.html'

    def get(self, request, *args, **kwargs):
        post = self.get_object()
        if post.published is None and not request.user.is_staff:
            raise Http404
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['posts'] = BlogPost.objects.all()
        return context


class PostsView(ListView):
    template_name = 'blog/post_list.html'

    def get_queryset(self):
        return BlogPost.objects.all()
