# accounts/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import RegisterForm, LoginForm


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