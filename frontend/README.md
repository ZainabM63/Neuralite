# Neuralite Flutter Frontend

A minimal Flutter frontend application that connects to the Neuralite backend API.

## Features

- **Chat Interface**: Clean, responsive chat UI with message bubbles
- **Backend Integration**: Connects to backend `/process` endpoint
- **Message Display**: Shows user and assistant messages with emotion and intent metadata
- **Input Handling**: Text input with send button and loading states
- **Error Handling**: Graceful error handling for network issues

## Project Structure

```
lib/
├── main.dart              # Application entry point
├── models/
│   └── message.dart       # Message data model
├── screens/
│   └── chat_screen.dart   # Main chat interface
├── services/
│   └── api_service.dart   # HTTP client for backend communication
└── widgets/
    ├── input_area.dart    # Text input and send button
    └── message_bubble.dart # Individual message display
```

## Backend Configuration

The API base URL is configured in `lib/services/api_service.dart`:

```dart
static const String _baseUrl = 'http://localhost:8000';
```

**To change the backend URL:**
1. Edit the `_baseUrl` constant in `api_service.dart`
2. Ensure the backend server is running on the specified host and port

## Security Features

- ✅ No sensitive data hardcoded
- ✅ Configurable base URL
- ✅ No files outside frontend/ folder touched
- ✅ Future-ready for authentication

## Future Enhancements (Ready for Implementation)

The codebase includes placeholders for future features:

- **Voice Input**: Microphone button in input area (commented TODO)
- **TTS Output**: Ready for text-to-speech integration
- **RAG Context Display**: Metadata display ready for RAG enhancements

## Running the Application

1. **Install Dependencies:**
   ```bash
   cd frontend/app
   flutter pub get
   ```

2. **Run the App:**
   ```bash
   flutter run
   ```

3. **Ensure Backend is Running:**
   ```bash
   # In the backend directory
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

## API Integration

The frontend sends messages to the backend via POST request to `/process` endpoint:

**Request Format:**
```json
{
  "message": "User input text"
}
```

**Response Format:**
```json
{
  "reply": "Assistant response",
  "emotion": "detected emotion",
  "intent": "detected intent"
}
```

## Development Notes

- Uses Flutter Material 3 design
- Supports both light and dark themes
- Mobile-first responsive design
- Clean separation of concerns with service layer
- Error handling for network failures
- Loading states during API calls

## Testing

Widget tests are included in `test/widget_test.dart` to verify the application loads correctly.