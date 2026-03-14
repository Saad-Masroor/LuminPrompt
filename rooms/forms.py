# rooms/forms.py
from django import forms
from .models import Room


class RoomCreateForm(forms.ModelForm):
    """
    Simple form to create a room.
    Only name and description — everything else is auto-set.
    """
    class Meta:
        model = Room
        fields = ('name', 'description')
        widgets = {
            'name': forms.TextInput(attrs={
                'placeholder': 'e.g. Project Brainstorm',
                'autofocus': True,
            }),
            'description': forms.Textarea(attrs={
                'placeholder': 'What is this room for?',
                'rows': 3,
            }),
        }