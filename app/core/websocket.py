import socketio
from typing import Dict, Set
import logging

logger = logging.getLogger(__name__)

# Create Socket.IO server
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*',
    logger=True,
    engineio_logger=True
)

# Store active connections: user_id -> set of session_ids
active_connections: Dict[str, Set[str]] = {}


@sio.event
async def connect(sid, environ, auth):
    """Handle client connection"""
    try:
        # Auth should contain the JWT token
        if not auth or 'token' not in auth:
            logger.warning(f"Connection attempt without token: {sid}")
            return False
        
        # TODO: Verify JWT token and get user_id
        # For now, we'll accept the connection
        logger.info(f"Client connected: {sid}")
        return True
        
    except Exception as e:
        logger.error(f"Error during connection: {e}")
        return False


@sio.event
async def disconnect(sid):
    """Handle client disconnection"""
    try:
        # Remove from active connections
        for user_id, sessions in list(active_connections.items()):
            if sid in sessions:
                sessions.discard(sid)
                if not sessions:
                    del active_connections[user_id]
                logger.info(f"Client disconnected: {sid} (user: {user_id})")
                break
        else:
            logger.info(f"Client disconnected: {sid}")
            
    except Exception as e:
        logger.error(f"Error during disconnection: {e}")


@sio.event
async def authenticate(sid, data):
    """Authenticate user and register their connection"""
    try:
        user_id = data.get('user_id')
        if not user_id:
            await sio.emit('error', {'message': 'Missing user_id'}, room=sid)
            return
        
        # Register this session for the user
        if user_id not in active_connections:
            active_connections[user_id] = set()
        active_connections[user_id].add(sid)
        
        logger.info(f"User authenticated: {user_id} (session: {sid})")
        await sio.emit('authenticated', {'status': 'success'}, room=sid)
        
    except Exception as e:
        logger.error(f"Error during authentication: {e}")
        await sio.emit('error', {'message': 'Authentication failed'}, room=sid)


async def notify_new_message(user_id: str, message_data: dict):
    """Notify a user about a new message"""
    try:
        if user_id in active_connections:
            sessions = active_connections[user_id]
            for session_id in sessions:
                await sio.emit('new_message', message_data, room=session_id)
                logger.info(f"Notified user {user_id} (session: {session_id}) about new message")
        else:
            logger.debug(f"User {user_id} not connected, notification skipped")
            
    except Exception as e:
        logger.error(f"Error notifying user {user_id}: {e}")


async def notify_message_read(user_id: str, message_id: str):
    """Notify a user that their sent message was read"""
    try:
        if user_id in active_connections:
            sessions = active_connections[user_id]
            for session_id in sessions:
                await sio.emit('message_read', {'message_id': message_id}, room=session_id)
                logger.info(f"Notified user {user_id} about message read: {message_id}")
                
    except Exception as e:
        logger.error(f"Error notifying user {user_id} about read message: {e}")


def get_socket_app():
    """Get the Socket.IO ASGI application"""
    return socketio.ASGIApp(sio)
