from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model
from .models import UserProfile
from django import forms


User = get_user_model()

class RegisterForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

class LoginForm(AuthenticationForm):
    """Fine for now, we can just use Django's built-in AuthenticationForm without modification."""
    pass

class UserSettingsForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ('bio', 'accent_color', 'mute_mic_on_join', 'notification_sound')
        widgets = {
            'bio': forms.TextInput(attrs={'placeholder': 'A short line about you', 'maxlength': 200}),
        }
 