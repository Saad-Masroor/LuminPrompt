import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.conf import settings
from django.contrib.auth import get_user_model
from groq import AsyncGroq

from .models import Room, Interaction, ChatMessage, TranscriptLine

groq_client = AsyncGroq(api_key=settings.GROQ_API_KEY)


class RoomConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.room_slug = self.scope['url_route']['kwargs']['slug']
        self.room_group_name = f'room_{self.room_slug}'
        self.user = self.scope['user']

        if not self.user.is_authenticated:
            await self.close()
            return

        self.room = await self.get_room()

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        await self.channel_layer.group_send(
            self.room_group_name,
            {'type': 'user_join', 'username': self.user.username}
        )

    async def disconnect(self, close_code):
        if not hasattr(self, 'room_group_name'):
            return
        await self.channel_layer.group_send(
            self.room_group_name,
            {'type': 'user_leave', 'username': self.user.username}
        )
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    @property
    def is_owner(self):
        return self.user.username == self.room.created_by.username

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type')

        if message_type == 'chat_message':
            message_text = data.get('message')
            await self.save_chat_message(message_text)
            await self.channel_layer.group_send(
                self.room_group_name,
                {'type': 'chat_message', 'message': message_text, 'username': self.user.username}
            )

        elif message_type == 'transcript':
            text = data.get('text')
            is_final = data.get('is_final', False)
            if is_final:
                await self.save_transcript_line(text)
            await self.channel_layer.group_send(
                self.room_group_name,
                {'type': 'transcript', 'text': text, 'username': self.user.username, 'is_final': is_final}
            )

        elif message_type == 'send_to_ai':
            transcript = data.get('transcript', [])
            await self.channel_layer.group_send(
                self.room_group_name,
                {'type': 'ai_thinking', 'username': self.user.username}
            )
            asyncio.create_task(self.run_ai_response(transcript))

        elif message_type == 'set_status':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'member_status',
                    'username': self.user.username,
                    'muted': bool(data.get('muted', False)),
                    'deafened': bool(data.get('deafened', False)),
                }
            )

        elif message_type == 'kick_member':
            target_username = data.get('target_username')
            if not self.is_owner:
                return
            if target_username == self.user.username:
                return
            await self.ban_member(target_username)
            await self.channel_layer.group_send(
                self.room_group_name,
                {'type': 'member_kicked', 'target_username': target_username}
            )

    # ─── Database reads/writes ─────────────────────────────

    @database_sync_to_async
    def get_room(self):
        return Room.objects.select_related('created_by').get(slug=self.room_slug)

    @database_sync_to_async
    def save_chat_message(self, message_text):
        ChatMessage.objects.create(room=self.room, sender=self.user, message=message_text)

    @database_sync_to_async
    def save_transcript_line(self, text):
        TranscriptLine.objects.create(room=self.room, speaker=self.user, text=text)

    @database_sync_to_async
    def save_interaction(self, transcript, response_text):
        Interaction.objects.create(
            room=self.room, requested_by=self.user,
            transcript_snapshot=transcript, ai_response=response_text,
        )

    @database_sync_to_async
    def ban_member(self, target_username):
        User = get_user_model()
        target = User.objects.get(username=target_username)
        # Both remove membership AND ban — removing alone would let them
        # straight back in via the invite link, since room_join_view only
        # checks "are they already a member," not "were they kicked."
        self.room.members.remove(target)
        self.room.banned_members.add(target)

    # ─── AI logic ──────────────────────────────────────────

    async def run_ai_response(self, transcript):
        prompt_text = "\n".join(
            f"{t.get('username', 'unknown')}: {t.get('text', '')}" for t in transcript
        )
        full_response = ""
        try:
            stream = await groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant responding to a live team conversation. Be concise and useful."
                    },
                    {"role": "user", "content": prompt_text},
                ],
                stream=True,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta.content or ""
                if delta:
                    full_response += delta
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {'type': 'ai_response_chunk', 'delta': delta, 'done': False}
                    )

            await self.channel_layer.group_send(
                self.room_group_name,
                {'type': 'ai_response_chunk', 'delta': '', 'done': True}
            )
            await self.save_interaction(transcript, full_response)

        except Exception as e:
            await self.channel_layer.group_send(
                self.room_group_name,
                {'type': 'ai_response_chunk', 'delta': f"[Error talking to AI: {e}]", 'done': True}
            )

    # ─── Group message handlers ───────────────────────────

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat_message', 'message': event['message'], 'username': event['username'],
        }))

    async def user_join(self, event):
        await self.send(text_data=json.dumps({'type': 'user_join', 'username': event['username']}))

    async def user_leave(self, event):
        await self.send(text_data=json.dumps({'type': 'user_leave', 'username': event['username']}))

    async def transcript(self, event):
        await self.send(text_data=json.dumps({
            'type': 'transcript', 'text': event['text'],
            'username': event['username'], 'is_final': event['is_final'],
        }))

    async def ai_thinking(self, event):
        await self.send(text_data=json.dumps({'type': 'ai_thinking', 'username': event['username']}))

    async def ai_response_chunk(self, event):
        await self.send(text_data=json.dumps({
            'type': 'ai_response_chunk', 'delta': event['delta'], 'done': event['done'],
        }))

    async def member_status(self, event):
        await self.send(text_data=json.dumps({
            'type': 'member_status', 'username': event['username'],
            'muted': event['muted'], 'deafened': event['deafened'],
        }))

    async def member_kicked(self, event):
        await self.send(text_data=json.dumps({
            'type': 'member_kicked', 'target_username': event['target_username'],
        }))