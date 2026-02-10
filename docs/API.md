# API Documentation

## Overview

GPT PANELIN V3.2 interfaces with GPT models to provide an interactive chat experience.

## Configuration

API configuration is managed through environment variables. See `.env.example` for available options.

## Client-Side API Integration

### API Client

The application uses Axios for HTTP requests. The API client is configured in `src/utils/api.js`.

```javascript
import apiClient from './utils/api';

// Example usage
const response = await apiClient.post('/chat', { message: 'Hello' });
```

### Request Structure

```javascript
{
  "message": "User message",
  "model": "gpt-3.5-turbo",
  "maxTokens": 2000
}
```

### Response Structure

```javascript
{
  "success": true,
  "data": {
    "message": "AI response",
    "tokens": 150
  }
}
```

## OpenAI Integration

### Direct Integration

To integrate directly with OpenAI API:

1. Set your API key in `.env`:
```
VITE_OPENAI_API_KEY=your_key_here
```

2. Update the chat logic in `src/components/ChatPanel.jsx` to call OpenAI API

### Proxy Server (Recommended)

For production, use a backend proxy server to:
- Protect API keys
- Implement rate limiting
- Add caching
- Monitor usage

## Endpoints

### POST /api/chat

Send a message to the GPT model.

**Request:**
```json
{
  "message": "Hello, how are you?",
  "conversationId": "optional-conversation-id"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "message": "I'm doing well, thank you!",
    "conversationId": "conversation-id",
    "tokens": 25
  }
}
```

### GET /api/conversations

Get conversation history.

**Response:**
```json
{
  "success": true,
  "data": {
    "conversations": [
      {
        "id": "conv-1",
        "messages": [...],
        "createdAt": "2026-02-10T00:00:00Z"
      }
    ]
  }
}
```

## Error Handling

All errors follow this format:

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message"
  }
}
```

### Common Error Codes

- `INVALID_API_KEY`: API key is missing or invalid
- `RATE_LIMIT_EXCEEDED`: Too many requests
- `INVALID_REQUEST`: Malformed request
- `MODEL_ERROR`: Error from GPT model
- `SERVER_ERROR`: Internal server error

## Rate Limiting

Default rate limits:
- 100 requests per minute per IP
- 1000 requests per hour per API key

## Best Practices

1. **Always validate input** before sending to API
2. **Implement retry logic** with exponential backoff
3. **Cache responses** when appropriate
4. **Handle errors gracefully** with user-friendly messages
5. **Monitor API usage** to avoid unexpected costs
6. **Use streaming** for long responses (if supported)

## Security

- Never expose API keys in client-side code
- Use HTTPS for all API requests
- Implement authentication and authorization
- Validate and sanitize all inputs
- Use CORS appropriately
