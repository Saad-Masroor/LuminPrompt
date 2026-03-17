# config/urls.py
from django.contrib import admin
from django.urls import path, include
from accounts.views import home_view
from rooms import urls as rooms_urls

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home_view, name='home'),
    path('accounts/', include('accounts.urls')),
    path('rooms/', include('rooms.urls')),
    path('api/rooms/', include(rooms_urls.api_urlpatterns)),
]
