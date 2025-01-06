from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
import os
from dotenv import load_dotenv
import boto3
import asyncio
import base64
from amazon_transcribe.client import TranscribeStreamingClient
from amazon_transcribe.handlers import TranscriptResultStreamHandler
from amazon_transcribe.model import TranscriptEvent

# Initialize Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', os.urandom(24))

# Initialize SocketIO with configuration for Railway
socketio = SocketIO(app, 
                   cors_allowed_origins="*", 
                   async_mode='eventlet',
                   ping_timeout=60,
                   ping_interval=25,
                   engineio_logger=True)

# Load environment variables
load_dotenv()

# Configure AWS credentials
boto3.setup_default_session(
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name=os.getenv('AWS_DEFAULT_REGION', 'us-west-2')
)

class TranscriptHandler(TranscriptResultStreamHandler):
    def __init__(self, output_stream, socket_id):
        super().__init__(output_stream)
        self.socket_id = socket_id
        self.last_text = ""

    async def handle_transcript_event(self, transcript_event: TranscriptEvent):
        results = transcript_event.transcript.results
        for result in results:
            if len(result.alternatives) > 0:
                transcript = result.alternatives[0].transcript.strip()
                if transcript:
                    self.last_text = transcript
                    # Emit the transcript through WebSocket
                    socketio.emit('transcript', 
                                {'text': transcript, 'is_partial': result.is_partial}, 
                                room=self.socket_id)
                    if not result.is_partial:
                        return transcript
        return None

async def process_audio(audio_data, socket_id):
    client = TranscribeStreamingClient(region=os.getenv('AWS_DEFAULT_REGION', 'us-west-2'))
    
    stream = await client.start_stream_transcription(
        language_code="en-US",
        media_sample_rate_hz=44100,
        media_encoding="pcm",
    )
    
    async def write_chunks():
        await stream.input_stream.send_audio_event(audio_chunk=audio_data)
        await stream.input_stream.end_stream()

    handler = TranscriptHandler(stream.output_stream, socket_id)
    
    await asyncio.gather(write_chunks(), handler.handle_events())
    
    return handler.last_text

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    app.logger.info(f"Client connected: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    app.logger.info(f"Client disconnected: {request.sid}")

@socketio.on('audio_data')
def handle_audio_data(data):
    try:
        # Decode base64 audio data
        audio_data = base64.b64decode(data['audio'].split(',')[1])
        
        # Process the audio using asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(process_audio(audio_data, request.sid))
        finally:
            loop.close()
    except Exception as e:
        app.logger.error(f"Error processing audio: {str(e)}")
        socketio.emit('error', {'message': str(e)}, room=request.sid)

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port) 