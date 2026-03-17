# rooms/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Room, RoomMembership
from .forms import RoomCreateForm
from rest_framework import viewsets, permissions
from rest_framework.response import Response
from .serializers import RoomSerializer

@login_required
def rooms_list_view(request):
    """
    Shows two lists:
    - Rooms the user created
    - Rooms the user has joined
    """
    created_rooms = Room.objects.filter(created_by=request.user)
    joined_rooms  = request.user.joined_rooms.exclude(created_by=request.user)

    return render(request, 'rooms/list.html', {
        'created_rooms': created_rooms,
        'joined_rooms': joined_rooms,
    })


@login_required
def room_create_view(request):
    """Creates a new room and adds creator as a member."""
    if request.method == 'POST':
        form = RoomCreateForm(request.POST)
        if form.is_valid():
            room = form.save(commit=False)
            room.created_by = request.user
            room.save()
            RoomMembership.objects.create(
                user= request.user,
                room= room,
                role= 'owner'
            )
            messages.success(request, f'Room "{room.name}" created!')
            return redirect('room_detail', slug=room.slug)
    else:
        form = RoomCreateForm()

    return render(request, 'rooms/create.html', {'form': form})


@login_required
def room_detail_view(request, slug):
    """
    The main room page.
    Only accessible to members.
    This is where WebSockets will live in Step 4.
    """
    room = get_object_or_404(Room, slug=slug, is_active=True)

    membership = RoomMembership.objects.filter(user=request.user, room=room).first()
    # Only members can view the room
    if not membership:
        messages.error(request, 'You are not a member of this room.')
        return redirect('rooms_list')

    return render(request, 'rooms/detail.html', {
        'room': room,
        'members': room.members.all(),
        'is_owner': membership.role == 'owner',
        'membership': membership
    })


@login_required
def room_join_view(request, slug):
    """
    Handles joining a room via invite link.
    Anyone with the link can join.
    """
    room = get_object_or_404(Room, slug=slug, is_active=True)

    membership = RoomMembership.objects.filter(user=request.user, room=room).first()

    if membership:
        # Already a member — just go to the room
        return redirect('room_detail', slug=room.slug)

    # Join as member
    RoomMembership.objects.create(
        user=request.user,
        room=room,
        role='member'
    )

    messages.success(request, f'You joined "{room.name}"!')
    return redirect('room_detail', slug=room.slug)

class RoomViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        rooms = Room.objects.filter(members=request.user)

        serializer = RoomSerializer(rooms, many= True, context = {'request':request})
        return Response(serializer.data)