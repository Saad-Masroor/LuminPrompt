#rooms/serializers.py

from rest_framework import serializers
from .models import Room

class RoomSerializer(serializers.ModelSerializer):
    is_owner = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()

    class Meta:
        model = Room
        fields = ['id', 'name', 'slug', 'is_owner', 'member_count', 'role']

    def get_is_owner(self, obj):
        request = self.context['request']
        return obj.created_by == request.user

    def get_member_count(self, obj):
        return obj.members.count()

    def get_role(self, obj):
        request = self.context['request']
        membership = obj.memberships.filter(user=request.user).first()
        return membership.role if membership else None