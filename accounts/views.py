# accounts/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import RegisterForm, LoginForm
from rooms.models import Room
from .forms import UserSettingsForm
from .models import get_or_create_profile
from django.contrib import messages
from django.contrib.auth import get_user_model



class RegisterView:
    """Handles user registration."""

    @staticmethod
    def get(request):
        form = RegisterForm()
        return render(request, 'accounts/register.html', {'form': form})

    @staticmethod
    def post(request):
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # log them in immediately after register
            messages.success(request, f'Welcome, {user.username}!')
            return redirect('home')  # we'll create this URL soon
        return render(request, 'accounts/register.html', {'form': form})


def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    view = RegisterView()
    if request.method == 'POST':
        return view.post(request)
    return view.get(request)


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            return redirect('home')
    else:
        form = LoginForm()
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('login')


@login_required
def home_view(request):
    """
    Temporary home view — just confirms auth works.
    We'll replace this with the rooms list in Step 3.
    """
    return render(request, 'home.html')


@login_required
def profile_view(request, username):
    User = get_user_model()
    profile_user = get_object_or_404(User, username=username)
    profile = get_or_create_profile(profile_user)
 
    # Only show rooms both the viewer and the profile owner can already see
    # each other in — i.e. rooms they're both members of — rather than
    # exposing someone's full room list to any logged-in visitor.
    shared_rooms = Room.objects.filter(members=profile_user).filter(members=request.user).distinct()
 
    return render(request, 'accounts/profile.html', {
        'profile_user': profile_user,
        'profile': profile,
        'shared_rooms': shared_rooms,
        'is_own_profile': profile_user == request.user,
    })
 
 
@login_required
def settings_view(request):
    profile = get_or_create_profile(request.user)
 
    if request.method == 'POST':
        form = UserSettingsForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Settings saved.')
            return redirect('user_settings')
    else:
        form = UserSettingsForm(instance=profile)
 
    return render(request, 'accounts/settings.html', {'form': form})