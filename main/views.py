from django.shortcuts import HttpResponse, render


def index(request):
    return HttpResponse('Welcome to the Integrated Farm Budget Tool!')
