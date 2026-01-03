# BeyondTheClub - Sport Session Booking System

Sistema automatizado para monitorar e reservar sessões de esportes no Beyond The Club, com suporte a CLI, API REST, Web UI e integração com **Voice Agents** (Twilio) e **AI Agents** (Claude) via **MCP Server com SSE**.

---

## Arquitetura

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           Beyond The Club                                     │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐      │
│   │    CLI      │   │   Web UI    │   │ Voice Agent │   │  AI Agent   │      │
│   │  (main.py)  │   │  (Next.js)  │   │  (Twilio)   │   │  (Claude)   │      │
│   └──────┬──────┘   └──────┬──────┘   └──────┬──────┘   └──────┬──────┘      │
│          │                 │                 │                 │              │
│          │          ┌──────▼──────┐   ┌──────▼─────────────────▼──────┐      │
│          │          │  REST API   │   │       MCP Server (SSE)        │      │
│          │          │  (FastAPI)  │   │       http://host:8001        │      │
│          │          │  :8000      │   └──────────────┬────────────────┘      │
│          │          └──────┬──────┘                  │                       │
│          │                 │                         │                       │
│          └─────────────────┼─────────────────────────┘                       │
│                            │                                                  │
│                   ┌────────▼────────┐                                         │
│                   │    Services     │                                         │
│                   │  (Python Core)  │                                         │
│                   └────────┬────────┘                                         │
│                            │                                                  │
│         ┌──────────────────┼──────────────────┐                              │
│         │                  │                  │                              │
│  ┌──────▼──────┐    ┌──────▼──────┐    ┌──────▼──────┐                       │
│  │ Beyond API  │    │   Cache     │    │   Graph     │                       │
│  │  (Firebase) │    │   (JSON)    │    │  (NetworkX) │                       │
│  └─────────────┘    └─────────────┘    └─────────────┘                       │
│                                                                               │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Componentes Principais

| Componente | Porta | Descrição |
|------------|-------|-----------|
| **REST API** | 8000 | FastAPI backend para Web UI e integrações |
| **MCP Server** | 8001 | SSE transport para Voice Agents e AI Agents |
| **Web UI** | 3000 | Interface Next.js para usuários |
| **CLI** | - | Interface de linha de comando |

---

## Esportes Suportados

| Esporte | Argumento | Atributos |
|---------|-----------|-----------|
| Surf | `surf` (padrão) | Nível + Lado da onda |
| Tennis | `tennis` | Quadra |

### Níveis de Surf
- `Iniciante1`, `Iniciante2`
- `Intermediario1`, `Intermediario2`
- `Avançado1`, `Avançado2`

### Lados da Onda
- `Lado_esquerdo`, `Lado_direito`

---

## Quick Start

### Docker (Recomendado)

```bash
# Clone o repositório
git clone <repo-url>
cd beyond-the-club

# Configure as variáveis de ambiente
cp .env.example .env
# Edite .env com suas configurações

# Inicie todos os serviços
docker-compose --profile mcp up -d

# Acesse:
# - Web UI:     http://localhost:3000
# - API Docs:   http://localhost:8000/docs
# - MCP Server: http://localhost:8001/sse
```

### Instalação Local

```bash
# Criar ambiente virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt

# Configurar
cp .env.example .env
```

---

## MCP Server - Voice Agents & AI Integration

O servidor MCP usa **SSE (Server-Sent Events)** para permitir integração com:
- **Voice Agents** (Twilio, VAPI, etc.)
- **AI Agents** (Claude, GPT, etc.)
- Qualquer cliente HTTP remoto

### Endpoints SSE

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `http://localhost:8001/sse` | Conexão SSE (stream de eventos) |
| POST | `http://localhost:8001/messages/` | Envio de mensagens para o servidor |

### Configuração para Voice Agent (Twilio)

```bash
# URL do MCP Server
MCP_URL=http://your-server:8001/sse

# O voice agent conecta via SSE e envia comandos via POST
```

### Iniciando o MCP Server

```bash
# Com Docker Compose
docker-compose --profile mcp up -d

# Ver logs
docker-compose --profile mcp logs -f mcp

# Parar
docker-compose --profile mcp down
```

### Ferramentas MCP (Tools)

| Ferramenta | Parâmetros | Descrição |
|------------|------------|-----------|
| `check_auth_status` | `phone` | Verificar autenticação do telefone |
| `request_beyond_sms` | `phone` | Solicitar SMS de verificação |
| `verify_beyond_sms` | `phone`, `code`, `session_info` | Verificar código SMS |
| `get_authenticated_phones` | - | Listar telefones autenticados |
| `check_availability` | `sport`, `date`, `level`, `wave_side` | Verificar slots disponíveis |
| `scan_availability` | `sport` | Forçar atualização do cache |
| `book_session` | `member_name`, `date`, `time`, `level`, `wave_side`, `sport` | Reservar sessão |
| `cancel_booking` | `voucher_code` | Cancelar reserva |
| `list_bookings` | `member_name`, `sport` | Listar reservas ativas |
| `swap_booking` | `voucher_code`, `new_member_name`, `sport` | Trocar membro da reserva |
| `get_members` | `sport` | Obter lista de membros |
| `get_member_preferences` | `member_name`, `sport` | Preferências do membro |
| `set_member_preferences` | `member_name`, `sessions`, `target_hours`, `target_dates`, `sport` | Definir preferências |
| `delete_member_preferences` | `member_name`, `sport` | Remover preferências |
| `start_auto_monitor` | `member_names`, `target_dates`, `duration_minutes`, `sport` | Iniciar monitoramento |
| `check_monitor_status` | - | Status do monitoramento |

### Recursos MCP (Resources)

| URI | Descrição |
|-----|-----------|
| `beyond://auth` | Status de autenticação |
| `beyond://members` | Lista de membros com status |
| `beyond://bookings` | Reservas ativas |
| `beyond://availability` | Cache de disponibilidade |
| `beyond://preferences` | Preferências de todos os membros |

### Exemplo de Uso com Voice Agent

```
Usuário: "Quero reservar uma aula de surf para o Rafael amanhã às 8h"

Voice Agent usa MCP Tools:
1. get_members(sport="surf")
   → Encontra membro "RAFAEL" (ID: 12869)

2. check_availability(sport="surf", date="2025-12-25")
   → Verifica slots disponíveis

3. book_session(
     member_name="RAFAEL",
     date="2025-12-25",
     time="08:00",
     level="Intermediario2",
     wave_side="Lado_direito",
     sport="surf"
   )
   → Reserva confirmada!
```

---

## REST API

### Base URL
- **Desenvolvimento**: `http://localhost:8000/api/v1`
- **Documentação**: `http://localhost:8000/docs`

### Autenticação (`/auth`)

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/register` | Registrar novo usuário |
| POST | `/login` | Login com telefone e senha |
| POST | `/login/phone` | Login apenas com telefone (voice) |
| POST | `/refresh` | Renovar access token |
| GET | `/me` | Dados do usuário atual |
| POST | `/link-member/{member_id}` | Vincular membro Beyond |
| POST | `/beyond/request-sms` | Solicitar SMS Beyond |
| POST | `/beyond/verify-sms` | Verificar código SMS |
| GET | `/beyond/status` | Status autenticação Beyond |

### Membros (`/members`)

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/` | Listar todos os membros |
| GET | `/{member_id}` | Detalhes do membro |
| GET | `/{member_id}/preferences` | Preferências |
| PUT | `/{member_id}/preferences` | Atualizar preferências |
| DELETE | `/{member_id}/preferences` | Remover preferências |
| GET | `/{member_id}/graph-summary` | Resumo do graph |

### Disponibilidade (`/availability`)

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/` | Slots disponíveis (cache) |
| POST | `/scan` | Forçar scan |
| GET | `/dates` | Datas com disponibilidade |
| GET | `/for-member/{member_id}` | Slots para preferências |

### Reservas (`/bookings`)

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/` | Listar reservas ativas |
| POST | `/` | Criar nova reserva |
| GET | `/{voucher_code}` | Detalhes da reserva |
| DELETE | `/{voucher_code}` | Cancelar reserva |
| POST | `/{voucher_code}/swap` | Trocar membro |
| GET | `/by-date/{date}` | Reservas por data |

### Monitor (`/monitor`)

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/start` | Iniciar monitoramento |
| GET | `/{monitor_id}/status` | Status |
| POST | `/{monitor_id}/stop` | Parar |
| GET | `/` | Listar monitores ativos |
| WebSocket | `/ws/{monitor_id}` | Updates em tempo real |

### Esportes (`/sports`)

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/` | Listar esportes |
| GET | `/{sport}` | Configuração |
| GET | `/{sport}/levels` | Níveis |
| GET | `/{sport}/wave-sides` | Lados da onda |
| GET | `/{sport}/combos` | Combinações válidas |
| GET | `/{sport}/packages` | IDs de pacotes |

---

## Estrutura do Projeto

```
beyond-the-club/
├── api/                          # FastAPI REST API
│   ├── main.py                   # App + APScheduler
│   ├── deps.py                   # Injeção de dependências
│   └── v1/                       # Endpoints v1
│       ├── auth.py
│       ├── availability.py
│       ├── bookings.py
│       ├── members.py
│       ├── monitor.py
│       ├── sports.py
│       └── system.py
│
├── mcp/                          # MCP Server (SSE)
│   ├── server.py                 # Server com SSE transport
│   ├── context.py                # Inicialização de serviços
│   ├── tools/                    # Ferramentas MCP
│   │   ├── auth.py
│   │   ├── availability.py
│   │   ├── booking.py
│   │   ├── members.py
│   │   └── monitor.py
│   └── resources/                # Recursos MCP
│       └── context.py
│
├── web/                          # Next.js Frontend
│   ├── src/app/                  # Pages (App Router)
│   ├── src/components/           # Componentes React
│   ├── src/hooks/                # Custom hooks
│   └── src/types/                # TypeScript types
│
├── src/                          # Core Python
│   ├── config.py                 # Configurações
│   ├── packages.py               # Mapeamento de pacotes
│   ├── beyond_api.py             # Cliente HTTP Beyond
│   ├── services/                 # Camada de serviços
│   │   ├── auth_service.py
│   │   ├── user_auth_service.py
│   │   ├── member_service.py
│   │   ├── availability_service.py
│   │   ├── booking_service.py
│   │   ├── monitor_service.py
│   │   ├── beyond_token_service.py
│   │   └── graph_service.py
│   ├── graph/                    # Knowledge Graph
│   │   ├── schema.py
│   │   ├── store.py
│   │   └── queries.py
│   └── auth/                     # Autenticação
│       ├── users.py
│       ├── jwt_handler.py
│       └── password.py
│
├── scripts/                      # Scripts utilitários
│   ├── start-mcp.sh              # Iniciar MCP Server
│   ├── start-dev.sh
│   ├── start-prod.sh
│   └── build.sh
│
├── main.py                       # CLI Entry point
├── docker-compose.yml            # Orquestração Docker
├── Dockerfile.api                # Container API
├── Dockerfile.mcp                # Container MCP
├── Dockerfile.web                # Container Web
└── requirements.txt              # Dependências Python
```

---

## Deploy com Docker

### Serviços

```yaml
api:      # FastAPI - Porta 8000
web:      # Next.js - Porta 3000
mcp:      # MCP SSE - Porta 8001 (profile: mcp)
nginx:    # Reverse proxy (profile: production)
```

### Comandos

```bash
# Desenvolvimento (API + Web)
docker-compose up -d

# Com MCP Server
docker-compose --profile mcp up -d

# Produção (com nginx)
docker-compose --profile production --profile mcp up -d

# Logs
docker-compose logs -f api
docker-compose logs -f mcp

# Rebuild
docker-compose build --no-cache

# Parar tudo
docker-compose --profile mcp down
```

### Health Checks

| Serviço | Endpoint |
|---------|----------|
| API | `GET /api/v1/system/status` |
| MCP | `GET /sse` (timeout 5s) |
| Web | `GET /` |

---

## Configuração

### Variáveis de Ambiente (.env)

```bash
# Firebase (Beyond The Club)
FIREBASE_API_KEY=AIzaSyBIzRHrTwR6BLZUOhZx3QGz16npuFwqOhs
FIREBASE_PROJECT_ID=beyondtheclub-8bfb3

# Admin Beyond
ADMIN_EMAIL=beyond.adm@beyond.com
ADMIN_PASSWORD=@BeyondGFT
ADMIN_PHONE=+5511972741849

# Seu telefone
PHONE_NUMBER=+5511999999999

# JWT (gerar: openssl rand -hex 32)
JWT_SECRET=your_secret_key
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440

# Esportes
SPORTS=surf,tennis
SURF_LEVELS=Iniciante1,Iniciante2,Intermediario1,Intermediario2,Avançado1,Avançado2
SURF_WAVE_SIDES=Lado_esquerdo,Lado_direito

# Monitoramento
CHECK_INTERVAL_SECONDS=60
AUTO_BOOK=true
```

---

## Autenticação

### Dois Níveis

1. **Aplicação (JWT)**
   - Registro com telefone + senha
   - Access token + Refresh token
   - Header: `Authorization: Bearer <token>`

2. **Beyond API (Firebase)**
   - SMS enviado para telefone
   - Código verificado retorna Firebase tokens
   - Tokens cacheados por usuário

### Fluxo

```
1. Login na aplicação (JWT)
2. Solicitar SMS do Beyond
3. Verificar código SMS
4. Tokens Beyond armazenados
5. Operações usam tokens do usuário
```

---

## Knowledge Graph

O sistema mantém um grafo de conhecimento para análises semânticas.

### Tipos de Nós

| Tipo | Descrição |
|------|-----------|
| `User` | Usuários (telefone) |
| `Member` | Membros Beyond |
| `Sport` | Esportes |
| `Preference` | Preferências de sessão |
| `Level` | Níveis de skill |
| `WaveSide` | Lados da onda |
| `Booking` | Reservas |
| `Slot` | Slots disponíveis |
| `Date` | Datas |

### Queries Semânticas

```python
# Slot ótimo baseado em preferências
graph_service.find_optimal_slot(member_id, "surf")

# Membros com preferências similares
graph_service.find_similar_members(member_id)

# Histórico de reservas
graph_service.get_member_booking_history(member_id)

# Combinações mais populares
graph_service.get_popular_combos("surf", limit=5)
```

---

## CLI

### Comandos Principais

```bash
# Listar membros
python main.py --list-members

# Configurar preferências
python main.py --configure

# Monitorar membro
python main.py --member rafael

# Verificação única
python main.py --member rafael --once

# Sem auto-booking
python main.py --member rafael --no-auto-book

# Código SMS direto
python main.py --sms-code 123456

# Forçar re-autenticação
python main.py --no-cache

# Verbose
python main.py -v
```

---

## Arquivos de Cache

| Arquivo | Descrição |
|---------|-----------|
| `.beyondtheclub_tokens.json` | Tokens Firebase |
| `.beyondtheclub_members.json` | Lista de membros |
| `.beyondtheclub_availability.json` | Cache de slots |
| `.beyondtheclub_preferences.json` | Preferências |
| `data/graph.json` | Knowledge Graph |
| `data/users.json` | Usuários do sistema |

---

## Troubleshooting

### Token Beyond Expirado

```bash
# CLI
python main.py --no-cache

# Via MCP
request_beyond_sms(phone="+55...")
verify_beyond_sms(phone="+55...", code="123456")
```

### Cache Desatualizado

```bash
# Membros
python main.py --refresh-members

# Disponibilidade
curl -X POST http://localhost:8000/api/v1/availability/scan
```

### MCP Server Não Conecta

```bash
# Verificar se está rodando
docker-compose --profile mcp ps

# Ver logs
docker-compose --profile mcp logs -f mcp

# Testar endpoint SSE
curl -N http://localhost:8001/sse
```

---

## Desenvolvimento

### Testes

```bash
pytest tests/
pytest --cov=src tests/
```

### Linting

```bash
ruff check .
black --check .
cd web && npm run lint
```

### Build

```bash
docker-compose build
cd web && npm run build
```

---

## Licença

MIT License
