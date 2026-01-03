# MCP Server Integration Guide

## Voice Agent Integration for Beyond The Club

This document describes how to integrate a Voice Agent application with the Beyond The Club MCP (Model Context Protocol) Server.

---

## Overview

The MCP Server provides a secure interface for voice agents to interact with the Beyond The Club booking system. It uses:

- **SSE (Server-Sent Events)** for real-time communication
- **Session-based authentication** with API key validation
- **Phone-based user identification** (caller ID)

---

## Base URL

| Environment | URL |
|-------------|-----|
| Production | `https://beyond.agentclub.io/mcp` |
| Direct (internal) | `http://localhost:8001` |

---

## Authentication Flow

### Step 1: Create Session

Before accessing MCP endpoints, the voice agent must create a session using the API key.

**Request:**
```http
POST /mcp/auth/session
Content-Type: application/json
X-API-Key: <MCP_API_KEY>

{
  "caller_id": "+5511999999999"
}
```

**Response (200 OK):**
```json
{
  "session_token": "sess_abc123def456...",
  "expires_in": 600,
  "user": {
    "phone": "+5511999999999",
    "name": "Rafael Silva",
    "has_beyond_token": true,
    "member_ids": [12345, 12346]
  }
}
```

**Error Responses:**
- `401 Unauthorized`: Invalid or missing API key
- `400 Bad Request`: Missing caller_id

### Step 2: Use Session Token

Include the session token in all subsequent requests:

```http
Authorization: Bearer sess_abc123def456...
```

---

## Endpoints

### Health Check

Check server status (no auth required).

```http
GET /mcp/health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "mcp-server",
  "active_sessions": 5
}
```

### Validate Session

Check if a session token is valid.

```http
GET /mcp/auth/validate
Authorization: Bearer <session_token>
```

**Response (valid):**
```json
{
  "valid": true,
  "user": {
    "phone": "+5511999999999",
    "name": "Rafael Silva",
    "has_beyond_token": true,
    "member_ids": [12345]
  }
}
```

**Response (invalid):**
```json
{
  "valid": false,
  "error": "Invalid or expired session"
}
```

### Logout

Invalidate a session.

```http
POST /mcp/auth/logout
Authorization: Bearer <session_token>
```

**Response:**
```json
{
  "success": true
}
```

### SSE Connection

Establish SSE connection for MCP protocol.

```http
GET /mcp/sse
Authorization: Bearer <session_token>
```

This endpoint streams Server-Sent Events for the MCP protocol.

### Send Messages

Send MCP protocol messages.

```http
POST /mcp/messages/
Authorization: Bearer <session_token>
Content-Type: application/json

{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/list"
}
```

---

## Available MCP Tools

The server exposes the following tools via MCP:

| Tool | Description |
|------|-------------|
| `get_members` | List all members linked to the user |
| `get_member_preferences` | Get booking preferences for a member |
| `set_member_preferences` | Update booking preferences |
| `get_availability` | Check session availability |
| `book_session` | Book an available session |
| `cancel_booking` | Cancel an existing booking |
| `get_bookings` | List active bookings |

---

## Session Lifecycle

```
┌─────────────────┐
│   Voice Call    │
│    Incoming     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Create Session │ POST /mcp/auth/session
│  (with API Key) │ X-API-Key: <key>
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Get Session   │ session_token: sess_xxx
│     Token       │ expires_in: 600s
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Connect SSE    │ GET /mcp/sse
│  (with Bearer)  │ Authorization: Bearer sess_xxx
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Send Messages  │ POST /mcp/messages/
│  (MCP Protocol) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Call Ends or   │
│  Session Expires│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│     Logout      │ POST /mcp/auth/logout
│   (optional)    │
└─────────────────┘
```

---

## Phone Number Format

Phone numbers must be in E.164 format:

| Format | Example | Valid |
|--------|---------|-------|
| E.164 (preferred) | `+5511999999999` | Yes |
| Without + | `5511999999999` | Yes (auto-normalized) |
| Local format | `(11) 99999-9999` | Yes (auto-normalized) |
| Invalid | `99999999` | No (too short) |

---

## Error Handling

All errors follow this format:

```json
{
  "error": "Error description",
  "code": "ERROR_CODE"
}
```

| HTTP Status | Error Code | Description |
|-------------|------------|-------------|
| 400 | `MISSING_CALLER_ID` | caller_id not provided |
| 401 | `INVALID_API_KEY` | API key invalid or missing |
| 401 | `INVALID_SESSION` | Session token invalid or expired |
| 401 | `MISSING_TOKEN` | Authorization header missing |
| 500 | `INTERNAL_ERROR` | Server error |

---

## Rate Limits

| Endpoint | Rate Limit |
|----------|------------|
| `/mcp/auth/session` | 10 requests/minute per IP |
| `/mcp/sse` | 1 connection per session |
| `/mcp/messages/` | 60 requests/minute per session |

---

## Example Integration (Python)

```python
import httpx
import json

MCP_URL = "https://beyond.agentclub.io/mcp"
API_KEY = "your_mcp_api_key_here"

async def create_session(caller_id: str) -> dict:
    """Create a new MCP session for a caller."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{MCP_URL}/auth/session",
            headers={"X-API-Key": API_KEY},
            json={"caller_id": caller_id}
        )
        response.raise_for_status()
        return response.json()

async def list_tools(session_token: str) -> dict:
    """List available MCP tools."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{MCP_URL}/messages/",
            headers={"Authorization": f"Bearer {session_token}"},
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list"
            }
        )
        response.raise_for_status()
        return response.json()

async def call_tool(session_token: str, tool_name: str, arguments: dict) -> dict:
    """Call an MCP tool."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{MCP_URL}/messages/",
            headers={"Authorization": f"Bearer {session_token}"},
            json={
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }
        )
        response.raise_for_status()
        return response.json()

# Usage example
async def handle_voice_call(caller_phone: str):
    # 1. Create session
    session = await create_session(caller_phone)
    token = session["session_token"]
    user = session["user"]

    print(f"Session created for {user['name']}")

    # 2. List available tools
    tools = await list_tools(token)
    print(f"Available tools: {tools}")

    # 3. Get member's bookings
    if user["member_ids"]:
        result = await call_tool(
            token,
            "get_bookings",
            {"member_id": user["member_ids"][0]}
        )
        print(f"Bookings: {result}")
```

---

## Example Integration (Node.js)

```javascript
const axios = require('axios');

const MCP_URL = 'https://beyond.agentclub.io/mcp';
const API_KEY = 'your_mcp_api_key_here';

async function createSession(callerId) {
  const response = await axios.post(
    `${MCP_URL}/auth/session`,
    { caller_id: callerId },
    { headers: { 'X-API-Key': API_KEY } }
  );
  return response.data;
}

async function callTool(sessionToken, toolName, args) {
  const response = await axios.post(
    `${MCP_URL}/messages/`,
    {
      jsonrpc: '2.0',
      id: Date.now(),
      method: 'tools/call',
      params: { name: toolName, arguments: args }
    },
    { headers: { 'Authorization': `Bearer ${sessionToken}` } }
  );
  return response.data;
}

// Usage
async function handleVoiceCall(callerPhone) {
  const session = await createSession(callerPhone);
  console.log(`Session for: ${session.user.name}`);

  const bookings = await callTool(
    session.session_token,
    'get_bookings',
    { member_id: session.user.member_ids[0] }
  );
  console.log('Bookings:', bookings);
}
```

---

## Security Considerations

1. **API Key**: Keep `MCP_API_KEY` secret. Never expose in client-side code.
2. **Session Tokens**: Expire after 10 minutes. Create new session if expired.
3. **HTTPS**: Always use HTTPS in production.
4. **Caller ID**: Validate caller ID before creating session.

---

## Support

For integration support, contact the development team or open an issue on the repository.
