# rooms/urls.py
from django.urls import path
from . import views
from rest_framework.routers import DefaultRouter
router = DefaultRouter()
router.register(r'', views.RoomViewSet, basename='room-api')
urlpatterns = [
    path('', views.rooms_list_view, name='rooms_list'),
    path('create/', views.room_create_view, name='room_create'),
    path('<uuid:slug>/', views.room_detail_view, name='room_detail'),
    path('<uuid:slug>/join/', views.room_join_view, name='room_join'),
]

api_urlpatterns = router.urls