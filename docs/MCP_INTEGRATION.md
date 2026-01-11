# MCP Server Integration Guide

## Voice Agent Integration for Beyond The Club

This document describes how to integrate a Voice Agent application with the Beyond The Club MCP (Model Context Protocol) Server.

---

## Overview

The MCP Server provides a secure interface for voice agents to interact with the Beyond The Club booking system. It uses:

- **SSE (Server-Sent Events)** for real-time communication
- **Session-based authentication** with API key validation
- **Phone-based user identification** (caller ID)
- **Knowledge Graph** for intelligent recommendations

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

The server exposes the following tools via MCP, organized by category:

### Authentication Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `check_auth_status` | Check if phone has valid Beyond API auth | `phone`: string |
| `request_beyond_sms` | Request SMS verification code | `phone`: string |
| `verify_beyond_sms` | Verify SMS code and complete auth | `phone`: string, `code`: string, `session_info?`: string |
| `get_authenticated_phone` | List all phones with valid auth | - |

### Member Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `get_members` | List all members with usage status | `sport?`: string (default: "surf") |
| `get_member_preferences` | Get booking preferences for a member | `member_name`: string, `sport?`: string |
| `set_member_preferences` | Update booking preferences | `member_name`: string, `sessions`: array, `target_hours?`: array, `target_dates?`: array, `sport?`: string |
| `delete_member_preferences` | Remove all preferences for a member | `member_name`: string, `sport?`: string |

### Availability Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `check_availability` | Check available slots (uses cache) | `sport?`: string, `date?`: string, `level?`: string, `wave_side?`: string |
| `scan_availability` | Force fresh availability scan | `sport?`: string |

### Booking Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `book_session` | Book a session for a member | `member_name`: string, `date`: string, `time`: string, `level?`: string, `wave_side?`: string, `sport?`: string |
| `cancel_booking` | Cancel booking by voucher | `voucher_code`: string |
| `swap_booking` | Transfer booking to different member | `voucher_code`: string, `new_member_name`: string, `sport?`: string |
| `list_bookings` | List active bookings | `member_name?`: string, `sport?`: string |

### Monitor Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `get_session_options` | Get available levels and hours | - |
| `check_session_availability` | Check availability (single check) | `member_name`: string, `level`: string, `target_date`: string, `wave_side?`: string, `target_hour?`: string, `sport?`: string |
| `search_session` | Monitor and book specific session | `member_name`: string, `level`: string, `target_date`: string, `target_hour?`: string, `wave_side?`: string, `auto_book?`: bool, `duration_minutes?`: int, `sport?`: string |
| `book_specific_slot` | Book a slot directly (no monitoring) | `member_name`: string, `level`: string, `wave_side`: string, `target_date`: string, `target_hour`: string, `sport?`: string |
| `start_auto_monitor` | Start auto-monitoring with preferences | `member_names?`: array, `target_dates?`: array, `duration_minutes?`: int, `sport?`: string |
| `check_monitor_status` | Check current monitor status | - |

---

## Tool Details

### Sessions Configuration (set_member_preferences)

The `sessions` parameter is an array of session preferences:

```json
{
  "sessions": [
    {"level": "Avançado2", "wave_side": "Lado_direito"},
    {"level": "Avançado1", "wave_side": "Lado_esquerdo"}
  ],
  "target_hours": ["08:00", "09:00"],
  "target_dates": ["2025-01-15", "2025-01-16"]
}
```

### Session Levels and Fixed Hours

Each level has specific valid hours:

| Level | Valid Hours |
|-------|-------------|
| Iniciante1 | 10:00, 14:00, 16:00 |
| Iniciante2 | 08:00, 11:00, 15:00, 17:00 |
| Intermediario1 | 09:00, 12:00, 14:00, 16:00 |
| Intermediario2 | 08:00, 10:00, 13:00, 15:00, 17:00 |
| Avançado1 | 08:00, 09:00, 11:00, 14:00, 16:00 |
| Avançado2 | 08:00, 09:00, 10:00, 12:00, 15:00, 17:00 |

### Wave Sides

- `Lado_esquerdo` (Left side)
- `Lado_direito` (Right side)

---

## MCP Resources

Resources provide structured data context for agents:

| Resource URI | Description |
|--------------|-------------|
| `btc://auth` | Authentication status for all phones |
| `btc://members` | All members with preferences |
| `btc://bookings` | Active bookings with details |
| `btc://availability` | Cached availability slots |
| `btc://preferences` | All member preferences by sport |

### Reading Resources

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "resources/read",
  "params": { "uri": "btc://members" }
}
```

---

## Knowledge Graph Ontology

The MCP server uses a semantic knowledge graph to provide intelligent recommendations and track user preferences. The agent can leverage this ontology for smarter interactions.

### Graph Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        KNOWLEDGE GRAPH ONTOLOGY                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────┐  HAS_MEMBER   ┌────────┐  HAS_PREFERENCE  ┌────────────┐          │
│  │ User │──────────────▶│ Member │─────────────────▶│ Preference │          │
│  └──────┘               └────────┘                  └────────────┘          │
│     │                      │  │                          │                   │
│     │                      │  │                          │                   │
│     │                      │  │     ┌────────────────────┼──────────────┐   │
│     │                      │  │     │         │          │              │   │
│     │                      │  │     ▼         ▼          ▼              ▼   │
│     │                      │  │  ┌───────┐ ┌────────┐ ┌──────────┐ ┌───────┐│
│     │                      │  │  │ Sport │ │ Level  │ │ WaveSide │ │ Court ││
│     │                      │  │  └───────┘ └────────┘ └──────────┘ └───────┘│
│     │                      │  │                (Surf)     (Surf)   (Tennis) │
│     │                      │  │                                              │
│     │                      │  └──────────┐                                   │
│     │                      │             │                                   │
│     │              BOOKED  ▼     FOR_SLOT▼                                   │
│     │                 ┌─────────┐   ┌────────┐   ON_DATE   ┌────────┐       │
│     │                 │ Booking │───│  Slot  │────────────▶│  Date  │       │
│     │                 └─────────┘   └────────┘             └────────┘       │
│     │                                    │                                   │
│     │                                    │ HAS_LEVEL / HAS_WAVE_SIDE        │
│     │                                    ▼                                   │
│     │                    ┌───────────────┴───────────────┐                  │
│     │                    │                               │                  │
│     │                    ▼                               ▼                  │
│     │               ┌────────┐                    ┌──────────┐              │
│     │               │ Level  │                    │ WaveSide │              │
│     │               └────────┘                    └──────────┘              │
│     │                                                                        │
│     │  PREFERS_HOUR                                                          │
│     └───────────────────────────────────────────┐                           │
│                                                 ▼                           │
│                                           ┌──────────┐                      │
│                                           │ TimeSlot │                      │
│                                           └──────────┘                      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Node Types

| Node Type | Description | Key Properties |
|-----------|-------------|----------------|
| `User` | App user (by phone) | `phone`, `name` |
| `Member` | Beyond club member | `member_id`, `name`, `social_name`, `is_titular` |
| `Sport` | Sport type | `name` (surf, tennis) |
| `Preference` | Booking preference | `sport`, `priority`, `attributes` |
| `Level` | Surf skill level | `name` (Iniciante1, Intermediario2, Avançado1, etc.) |
| `WaveSide` | Surf wave side | `name` (Lado_esquerdo, Lado_direito) |
| `Court` | Tennis court | `name` (Quadra_Saibro) |
| `TimeSlot` | Preferred hour | `hour` (08:00, 09:00, etc.) |
| `Booking` | Active/past booking | `voucher`, `access_code`, `status`, `created_at`, `cancelled_at` |
| `Slot` | Available session slot | `date`, `interval`, `available`, `max_quantity`, `level`, `wave_side` |
| `Date` | Calendar date | `value` (YYYY-MM-DD), `day_of_week` |

### Edge Types (Relationships)

| Edge Type | From → To | Description |
|-----------|-----------|-------------|
| `HAS_MEMBER` | User → Member | User owns member(s) |
| `HAS_PREFERENCE` | Member → Preference | Member's booking preference (with `priority`) |
| `FOR_SPORT` | Preference → Sport | Preference is for sport |
| `PREFERS_LEVEL` | Preference → Level | Preferred surf level |
| `PREFERS_WAVE_SIDE` | Preference → WaveSide | Preferred wave side |
| `PREFERS_COURT` | Preference → Court | Preferred tennis court |
| `PREFERS_HOUR` | Member → TimeSlot | Preferred booking hours |
| `BOOKED` | Member → Booking | Member made booking (with `booked_at`) |
| `FOR_SLOT` | Booking → Slot | Booking is for slot |
| `ON_DATE` | Slot → Date | Slot is on date |
| `HAS_LEVEL` | Slot → Level | Slot has level |
| `HAS_WAVE_SIDE` | Slot → WaveSide | Slot has wave side |

### Graph Queries Available

The graph enables intelligent queries:

| Query Method | Description | Returns |
|--------------|-------------|---------|
| `find_similar_members(member_id, sport)` | Find members with similar preferences | List of similar members with similarity score |
| `find_optimal_slot(member_id, sport, date)` | Best slot based on preferences + hours | Optimal slot recommendation |
| `get_member_booking_history(member_id, limit)` | Past bookings by member | Historical booking data |
| `get_popular_combos(sport, limit)` | Most booked level/wave combinations | Ranked combos |
| `get_member_preferences(member_id, sport)` | Member's stored preferences | Preference data |
| `get_user_members(phone)` | Get members linked to a phone | Member list |
| `get_member_summary(member_id)` | Full graph summary for a member | Complete profile |

### How the Agent Uses Graph Intelligence

```
User: "Quero agendar uma aula de surf"

Agent workflow:
  1. Get member preferences from graph
     → Member prefers Avançado2/Lado_direito
  2. Check similar members' booking patterns
     → Similar users book at 08:00 and 09:00
  3. Find optimal slot matching preferences + preferred hours
     → Found: 2025-01-15 08:00 Avançado2/Lado_direito
  4. Suggest with context:
     "Vi que você prefere Avançado2 lado direito.
      Tem vaga amanhã às 8h - mesmo horário que você geralmente agenda."
```

### Semantic Queries Examples

| Query | Description | Use Case |
|-------|-------------|----------|
| Find similar members | Members with matching preferences | "Others who surf like you also book at 8am" |
| Optimal slot | Best slot based on preferences + hours | "I found a perfect slot for you" |
| Booking history | Past bookings by member | "You usually book Avançado2 on weekends" |
| Popular combos | Most booked level/wave combinations | "Intermediario2/Lado_direito is popular" |
| Preference patterns | Cross-member preference analysis | "Most Avançado users prefer morning slots" |

---

## Domain Model

### Surf Session Levels (Progression)

```
Iniciante1 → Iniciante2 → Intermediario1 → Intermediario2 → Avançado1 → Avançado2
```

### Wave Sides

| Internal Name | Display Name |
|---------------|--------------|
| `Lado_esquerdo` | Left Side |
| `Lado_direito` | Right Side |

### Member Properties

| Property | Description |
|----------|-------------|
| `member_id` | Unique Beyond API ID |
| `name` | Full registered name |
| `social_name` | Display name |
| `is_titular` | Primary account holder |
| `usage` | Sessions used this period |
| `limit` | Maximum sessions allowed |

### Booking Properties

| Property | Description |
|----------|-------------|
| `voucher_code` | Unique booking identifier |
| `access_code` | Entry code for the session |
| `status` | `AccessReady`, `Cancelled`, `Used` |
| `date` | Session date (YYYY-MM-DD) |
| `interval` | Session time (HH:MM) |

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

    # 2. Check if Beyond auth is valid
    auth_status = await call_tool(token, "check_auth_status", {"phone": caller_phone})
    print(f"Auth status: {auth_status}")

    # 3. If authenticated, get members
    if user["has_beyond_token"]:
        members = await call_tool(token, "get_members", {"sport": "surf"})
        print(f"Members: {members}")

        # 4. Check availability for a specific session
        availability = await call_tool(
            token,
            "check_session_availability",
            {
                "member_name": "Rafael",
                "level": "Avançado2",
                "target_date": "2025-01-15"
            }
        )
        print(f"Availability: {availability}")
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

  // Check availability and book
  const result = await callTool(
    session.session_token,
    'search_session',
    {
      member_name: 'Rafael',
      level: 'Avançado2',
      target_date: '2025-01-15',
      target_hour: '08:00',
      wave_side: 'Lado_direito',
      auto_book: true
    }
  );
  console.log('Booking result:', result);
}
```

---

## Typical Voice Agent Conversation Flow

```
Agent: "Olá! Bem-vindo ao Beyond The Club. Como posso ajudar?"

User: "Quero agendar uma aula de surf"

Agent: [calls get_members]
       "Vi que você tem 2 membros cadastrados: Rafael e Maria.
        Para quem você quer agendar?"

User: "Para o Rafael"

Agent: [calls get_member_preferences]
       "Rafael prefere Avançado2 lado direito, geralmente às 8h.
        Qual data você prefere?"

User: "Amanhã"

Agent: [calls check_session_availability]
       "Encontrei essas opções para amanhã:
        - 08:00 lado direito (2 vagas)
        - 09:00 lado esquerdo (4 vagas)
        Qual você prefere?"

User: "8h lado direito"

Agent: [calls book_specific_slot]
       "Reservado! Rafael está confirmado para amanhã às 8h,
        Avançado2 lado direito. Código de acesso: ABC123"
```

---

## Security Considerations

1. **API Key**: Keep `MCP_API_KEY` secret. Never expose in client-side code.
2. **Session Tokens**: Expire after 10 minutes. Create new session if expired.
3. **HTTPS**: Always use HTTPS in production.
4. **Caller ID**: Validate caller ID before creating session.
5. **Beyond Tokens**: Stored securely, auto-refresh when needed.

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MCP_API_KEY` | Voice Agent authentication key | Required |
| `MCP_SESSION_EXPIRY_SECONDS` | Session timeout | 600 |
| `MCP_HOST` | Server host | 0.0.0.0 |
| `MCP_PORT` | Server port | 8001 |
| `BEYOND_API_URL` | Beyond API endpoint | Required |

---

## Support

For integration support, contact the development team or open an issue on the repository.
