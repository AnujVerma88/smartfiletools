from django.urls import path
from django.http import HttpResponse

def index(request):
    return HttpResponse('OK')

urlpatterns = [
    path('', index, name='index'),
]
