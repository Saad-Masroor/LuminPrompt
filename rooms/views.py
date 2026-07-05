# rooms/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Room, ChatMessage, TranscriptLine
from .forms import RoomCreateForm


@login_required
def rooms_list_view(request):
    created_rooms = Room.objects.filter(created_by=request.user)
    joined_rooms = request.user.joined_rooms.exclude(created_by=request.user)
    return render(request, 'rooms/list.html', {
        'created_rooms': created_rooms,
        'joined_rooms': joined_rooms,
    })


@login_required
def room_create_view(request):
    if request.method == 'POST':
        form = RoomCreateForm(request.POST)
        if form.is_valid():
            room = form.save(commit=False)
            room.created_by = request.user
            room.save()
            room.members.add(request.user)
            messages.success(request, f'Room "{room.name}" created!')
            return redirect('room_detail', slug=room.slug)
    else:
        form = RoomCreateForm()
    return render(request, 'rooms/create.html', {'form': form})


@login_required
def room_detail_view(request, slug):
    room = get_object_or_404(Room, slug=slug, is_active=True)

    if request.user not in room.members.all():
        messages.error(request, 'You are not a member of this room.')
        return redirect('rooms_list')

    recent_chat = ChatMessage.objects.filter(room=room).select_related('sender').order_by('created_at')[:50]
    recent_transcript_qs = TranscriptLine.objects.filter(room=room).select_related('speaker').order_by('created_at')[:100]
    recent_transcript = [{'username': t.speaker.username, 'text': t.text} for t in recent_transcript_qs]

    return render(request, 'rooms/detail.html', {
        'room': room,
        'members': room.members.all(),
        'is_owner': request.user == room.created_by,
        'recent_chat': recent_chat,
        'recent_transcript': recent_transcript,
    })


@login_required
def room_join_view(request, slug):
    room = get_object_or_404(Room, slug=slug, is_active=True)

    # Checked before anything else: someone kicked from this room shouldn't
    # be able to just click the invite link again and walk back in.
    if room.banned_members.filter(id=request.user.id).exists():
        messages.error(request, "You've been removed from this room and can't rejoin using this link.")
        return redirect('rooms_list')

    if request.user in room.members.all():
        return redirect('room_detail', slug=room.slug)
    room.members.add(request.user)
    messages.success(request, f'You joined "{room.name}"!')
    return redirect('room_detail', slug=room.slug)


@login_required
def room_leave_view(request, slug):
    room = get_object_or_404(Room, slug=slug, is_active=True)
    if request.user == room.created_by:
        messages.error(request, "As the owner, you can't leave your own room.")
        return redirect('room_detail', slug=slug)
    room.members.remove(request.user)
    messages.info(request, f'You left "{room.name}".')
    return redirect('rooms_list')


@login_required
def room_kicked_notice(request):
    """
    A tiny landing page for someone who was just kicked. It exists so we
    can show a real, visible message (via Django's messages framework)
    instead of a JS alert() — and so the redirect target isn't hardcoded
    inside the WebSocket JavaScript.
    """
    messages.error(request, "You were removed from that room by its owner.")
    return redirect('rooms_list')