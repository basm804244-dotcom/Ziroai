# AetherAI API Documentation

## Authentication
All API requests require a Bearer token in the Authorization header.

```
Authorization: Bearer <your_token>
```

## Endpoints

### Auth
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login
- `POST /api/v1/auth/refresh` - Refresh token
- `GET /api/v1/auth/me` - Get current user

### Chat
- `POST /api/v1/chat/conversations` - Create conversation
- `GET /api/v1/chat/conversations` - List conversations
- `POST /api/v1/chat/conversations/{id}/messages` - Send message
- `POST /api/v1/chat/conversations/{id}/generate` - Generate response
- `POST /api/v1/chat/conversations/{id}/generate/stream` - Stream response

### Agents
- `GET /api/v1/agents/templates` - List templates
- `POST /api/v1/agents` - Create agent
- `GET /api/v1/agents` - List agents
- `POST /api/v1/agents/{id}/execute` - Execute agent

### Models
- `GET /api/v1/models` - List models
- `POST /api/v1/models/chat` - Chat completion
- `POST /api/v1/models/chat/stream` - Streaming chat

### Memory
- `POST /api/v1/memory` - Store memory
- `GET /api/v1/memory/{id}` - Get memory
- `POST /api/v1/memory/search` - Search memory

### RAG
- `POST /api/v1/knowledge-bases` - Create KB
- `POST /api/v1/knowledge-bases/{id}/documents` - Upload document
- `POST /api/v1/search` - Search documents
