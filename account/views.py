from django.shortcuts import render, redirect
from django.views.generic import CreateView, TemplateView, RedirectView
from django.views import View
from django.contrib.auth import login
from django.urls import reverse_lazy, reverse
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str  # force_text on older versions of Django

from .forms import RegistrationForm, token_generator, user_model
from main.models.util import has_farm_years


class RegistrationView(CreateView):
    form_class = RegistrationForm
    template_name = 'account/register.html'
    success_url = reverse_lazy('check_email')

    def form_valid(self, form):
        to_return = super().form_valid(form)

        user = form.save()
        user.is_active = False
        user.save()

        form.send_activation_email(self.request, user)

        return to_return

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = context['view'].request.user
        hasfarmyears = has_farm_years(user)
        context['has_farm_years'] = hasfarmyears
        return context


class ActivateView(RedirectView):

    url = reverse_lazy('farmyears')

    # Custom get method
    def get(self, request, uidb64, token):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = user_model.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, user_model.DoesNotExist):
            user = None

        if user is not None and token_generator.check_token(user, token):
            user.is_active = True
            user.save()
            login(request, user)
            return super().get(request, uidb64, token)
        else:
            return render(request, 'account/activate_account_invalid.html')


class CheckEmailView(TemplateView):
    template_name = 'account/check_email.html'


class DeleteAccountView(View):
    template_name = "account/confirm_delete.html"

    def get(self, request, *args, **kwargs):
        print(f'{request.user=}')
        print(f'{has_farm_years(request.user)=}')
        return render(request, self.template_name,
                      {'has_farm_years': has_farm_years(request.user)})

    def post(self, request, *args, **kwargs):
        request.user.delete()
        return redirect(reverse('index'))
