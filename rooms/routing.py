# rooms/routing.py
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # match: ws://127.0.0.1:8000/ws/room/<slug>/
    re_path(r'ws/rooms/(?P<slug>[^/]+)/$', consumers.RoomConsumer.as_asgi()),
]