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
        # Make sure nobody's "X is typing…" indicator gets stuck on if this
        # user closes the tab mid-keystroke, before their debounce timer fires.
        await self.channel_layer.group_send(
            self.room_group_name,
            {'type': 'user_typing', 'username': self.user.username, 'is_typing': False}
        )
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
            reply_to_id = data.get('reply_to')
            saved = await self.save_chat_message(message_text, reply_to_id)
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'id': saved['id'],
                    'message': message_text,
                    'username': self.user.username,
                    'reply_to': saved['reply_to'],
                }
            )

        elif message_type == 'transcript':
            text = data.get('text')
            is_final = data.get('is_final', False)
            line_id = None
            if is_final:
                line_id = await self.save_transcript_line(text)
            await self.channel_layer.group_send(
                self.room_group_name,
                {'type': 'transcript', 'id': line_id, 'text': text, 'username': self.user.username, 'is_final': is_final}
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

        elif message_type == 'toggle_hand':
            # Ephemeral, like mute/deafen — nobody needs this to survive a
            # reload, so it's a pure broadcast with nothing saved to the DB.
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'member_hand',
                    'username': self.user.username,
                    'raised': bool(data.get('raised', False)),
                }
            )

        elif message_type == 'typing':
            # Also ephemeral, same reasoning as toggle_hand — nothing saved,
            # just a live "someone's composing a message" signal.
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_typing',
                    'username': self.user.username,
                    'is_typing': bool(data.get('is_typing', False)),
                }
            )

        elif message_type == 'force_mute':
            if not self.is_owner:
                return
            target_username = data.get('target_username')
            if target_username == self.user.username:
                return
            await self.channel_layer.group_send(
                self.room_group_name,
                {'type': 'member_force_muted', 'target_username': target_username}
            )

        elif message_type == 'delete_message':
            kind = data.get('message_type')  # 'chat' or 'transcript'
            msg_id = data.get('id')
            allowed = await self.mark_deleted(kind, msg_id)
            if allowed:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {'type': 'message_deleted', 'message_type': kind, 'id': msg_id}
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
    def save_chat_message(self, message_text, reply_to_id):
        reply_to = None
        reply_preview = None
        if reply_to_id:
            try:
                reply_to = ChatMessage.objects.get(id=reply_to_id, room=self.room, is_deleted=False)
                reply_preview = {
                    'id': reply_to.id,
                    'username': reply_to.sender.username,
                    'snippet': reply_to.message[:80],
                }
            except ChatMessage.DoesNotExist:
                reply_to = None

        msg = ChatMessage.objects.create(
            room=self.room, sender=self.user, message=message_text, reply_to=reply_to,
        )
        return {'id': msg.id, 'reply_to': reply_preview}

    @database_sync_to_async
    def save_transcript_line(self, text):
        line = TranscriptLine.objects.create(room=self.room, speaker=self.user, text=text)
        return line.id

    @database_sync_to_async
    def save_interaction(self, transcript, response_text):
        Interaction.objects.create(
            room=self.room, requested_by=self.user,
            transcript_snapshot=transcript, ai_response=response_text,
        )

    @database_sync_to_async
    def mark_deleted(self, kind, msg_id):
        """Returns True if the delete was allowed and applied."""
        model = ChatMessage if kind == 'chat' else TranscriptLine if kind == 'transcript' else None
        if model is None or msg_id is None:
            return False
        try:
            obj = model.objects.get(id=msg_id, room=self.room)
        except model.DoesNotExist:
            return False

        owner_field = obj.sender if kind == 'chat' else obj.speaker
        if owner_field.username != self.user.username and not self.is_owner:
            return False

        obj.is_deleted = True
        obj.save(update_fields=['is_deleted'])
        return True

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
            'type': 'chat_message', 'id': event['id'], 'message': event['message'],
            'username': event['username'], 'reply_to': event['reply_to'],
        }))

    async def user_join(self, event):
        await self.send(text_data=json.dumps({'type': 'user_join', 'username': event['username']}))

    async def user_leave(self, event):
        await self.send(text_data=json.dumps({'type': 'user_leave', 'username': event['username']}))

    async def transcript(self, event):
        await self.send(text_data=json.dumps({
            'type': 'transcript', 'id': event['id'], 'text': event['text'],
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

    async def member_hand(self, event):
        await self.send(text_data=json.dumps({
            'type': 'member_hand', 'username': event['username'], 'raised': event['raised'],
        }))

    async def user_typing(self, event):
        await self.send(text_data=json.dumps({
            'type': 'user_typing', 'username': event['username'], 'is_typing': event['is_typing'],
        }))

    async def member_force_muted(self, event):
        await self.send(text_data=json.dumps({
            'type': 'member_force_muted', 'target_username': event['target_username'],
        }))

    async def message_deleted(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message_deleted', 'message_type': event['message_type'], 'id': event['id'],
        }))

    async def member_kicked(self, event):
        await self.send(text_data=json.dumps({
            'type': 'member_kicked', 'target_username': event['target_username'],
        }))