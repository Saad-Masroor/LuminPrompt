import json
from channels.generic.websocket import AsyncWebsocketConsumer

class RoomConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        # Extract room slug from URL route (e.g. /ws/rooms/<slug>/)
        self.room_slug = self.scope['url_route']['kwargs']['slug']
        self.room_group_name = f'room_{self.room_slug}'

        self.user = self.scope['user']
        if not self.user.is_authenticated:
            # Reject connection if user is not authenticated
            await self.close()
        else:
            # Join room group
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            await self.accept()

            # Broadcast join message to room group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_join',
                    'username': self.user.username,
                }
            )

    async def disconnect(self, close_code):
        if not hasattr(self, 'room_group_name'):
            return
        # Send leave message to room group first  
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_leave',
                'username': self.user.username,
            }
        )
        # Then leave the room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        # parse incoming message
        data = json.loads(text_data)
        message_type = data.get('type')

        if message_type == 'chat_message':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': data.get('message'),
                    'username': self.user.username,
                }
            )
        elif message_type == 'transcript':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'transcript',
                    'text': data.get('text'),
                    'username': self.user.username,
                    'is_final': data.get('is_final', False)
                }
            )
        elif message_type == 'send_to_ai':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'ai_thinking',
                    'username': self.user.username,
                    'transcript': data.get('transcript', [])
                }
            )
        elif message_type == 'start_recording':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'recording_started',
                    'username': self.user.username,
                    'timestamp': data.get('timestamp'),
                    'recording_id': data.get('recording_id'),
                    'is_recording': True
                }
            )
        elif message_type == 'stop_recording':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'recording_stopped',
                    'username': self.user.username,
                    'timestamp': data.get('timestamp'),
                    'recording_id': data.get('recording_id'),
                    'is_recording': False
                }
            )
    async def recording_started(self, event):
        # Send recording started message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'recording_started',
            'username': event['username'],
            'timestamp': event['timestamp'],
            'recording_id': event['recording_id'],
            'is_recording': event['is_recording']
        }))

    async def recording_stopped(self, event):
        # Send recording stopped message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'recording_stopped',
            'username': event['username'],
            'timestamp': event['timestamp'],
            'recording_id': event['recording_id'],
            'is_recording': event['is_recording']
        }))

    async def chat_message(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message'],
            'username': event['username'],
        }))

    async def user_join(self, event):
        # Send join notification to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'user_join',
            'username': event['username'],
        }))

    async def user_leave(self, event):
        # Send Leave Notification to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'user_leave',
            'username': event['username']
        }))

    async def transcript(self, event):
        # Send trascript message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'transcript',
            'text': event['text'],
            'username': event['username'],
            'is_final': event['is_final']
        }))

    async def ai_thinking(self, event):
        # Send AI thinking message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'ai_thinking',
            'username': event['username'],
            'transcript': event['transcript']
        }))