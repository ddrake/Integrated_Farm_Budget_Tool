from django.shortcuts import reverse, redirect
from datetime import datetime


class MaintenanceMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.META.get('PATH_INFO', "")
        query = request.META.get('QUERY_STRING', "")
        now = datetime.now()
        maintstart = datetime(now.year, 12, 31, 15, 0, 0)
        maintend = datetime(now.year, 12, 31, 23, 59, 59)

        if 'bypass' in query:
            request.session['bypass_maintenance'] = True

        if (maintstart <= now <= maintend and path != reverse("maintenance") and
                not request.session.get('bypass_maintenance', False)):
            response = redirect(reverse("maintenance"))
            return response
        else:
            response = self.get_response(request)
            return response
