# BeyondTheClub - Sport Session Booking System

Sistema automatizado para monitorar e reservar sessões de esportes no Beyond The Club, com suporte a CLI, API REST, aplicação Web e integração com AI Agents via MCP.

## Arquitetura

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Beyond The Club                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐             │
│  │    CLI      │    │   Web UI    │    │ AI Agents   │             │
│  │  (main.py)  │    │  (Next.js)  │    │   (Claude)  │             │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘             │
│         │                  │                  │                     │
│         │           ┌──────▼──────┐    ┌──────▼──────┐             │
│         │           │  REST API   │    │ MCP Server  │             │
│         │           │  (FastAPI)  │    │   (stdio)   │             │
│         │           └──────┬──────┘    └──────┬──────┘             │
│         │                  │                  │                     │
│         └──────────────────┼──────────────────┘                     │
│                            │                                        │
│                   ┌────────▼────────┐                               │
│                   │    Services     │                               │
│                   │  (Python Core)  │                               │
│                   └────────┬────────┘                               │
│                            │                                        │
│         ┌──────────────────┼──────────────────┐                     │
│         │                  │                  │                     │
│  ┌──────▼──────┐    ┌──────▼──────┐    ┌──────▼──────┐             │
│  │ Beyond API  │    │   Cache     │    │   Graph     │             │
│  │  (Firebase) │    │   (JSON)    │    │  (NetworkX) │             │
│  └─────────────┘    └─────────────┘    └─────────────┘             │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

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

### Usando Docker (Recomendado)

```bash
# Clone o repositório
git clone <repo-url>
cd beyond-the-club

# Configure as variáveis de ambiente
cp .env.example .env
# Edite .env com suas configurações

# Inicie API + Web
docker-compose up -d

# Acesse
# - Web UI: http://localhost:3000
# - API Docs: http://localhost:8000/docs
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
# Edite o arquivo .env com suas configurações
```

---

## Componentes

### 1. CLI (main.py)

Interface de linha de comando para operações manuais e scripts.

```bash
# Listar membros
python main.py --list-members

# Configurar preferências
python main.py --configure

# Monitorar sessões
python main.py --member rafael

# Ver ajuda completa
python main.py --help
```

### 2. API REST (FastAPI)

API RESTful completa para integração com aplicações.

- **Base URL**: `http://localhost:8000/api/v1`
- **Documentação**: `http://localhost:8000/docs` (Swagger UI)
- **OpenAPI**: `http://localhost:8000/openapi.json`

### 3. Web UI (Next.js)

Interface web moderna para gerenciamento visual.

- **URL**: `http://localhost:3000`
- **Stack**: Next.js 14, React 18, Tailwind CSS, Zustand

### 4. MCP Server

Servidor MCP para integração com AI Agents (Claude).

```bash
# Iniciar MCP Server standalone
cd mcp && python -m mcp.server
```

---

## API REST - Endpoints

### Autenticação (`/api/v1/auth`)

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/register` | Registrar novo usuário |
| POST | `/login` | Login com telefone e senha |
| POST | `/login/phone` | Login apenas com telefone (voice agent) |
| POST | `/refresh` | Renovar access token |
| GET | `/me` | Obter dados do usuário atual |
| POST | `/link-member/{member_id}` | Vincular membro Beyond à conta |
| POST | `/beyond/request-sms` | Solicitar SMS para autenticação Beyond |
| POST | `/beyond/verify-sms` | Verificar código SMS do Beyond |
| GET | `/beyond/status` | Status da autenticação Beyond |

### Membros (`/api/v1/members`)

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/` | Listar todos os membros |
| GET | `/{member_id}` | Detalhes de um membro |
| GET | `/{member_id}/preferences` | Preferências do membro |
| PUT | `/{member_id}/preferences` | Atualizar preferências |
| DELETE | `/{member_id}/preferences` | Remover preferências |
| GET | `/{member_id}/graph-summary` | Resumo do graph do membro |

### Disponibilidade (`/api/v1/availability`)

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/` | Slots disponíveis (cache) |
| POST | `/scan` | Forçar scan de disponibilidade |
| GET | `/dates` | Datas com disponibilidade |
| GET | `/for-member/{member_id}` | Slots para preferências do membro |

### Reservas (`/api/v1/bookings`)

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/` | Listar reservas ativas |
| POST | `/` | Criar nova reserva |
| GET | `/{voucher_code}` | Detalhes da reserva |
| DELETE | `/{voucher_code}` | Cancelar reserva |
| POST | `/{voucher_code}/swap` | Trocar membro da reserva |
| GET | `/by-date/{date}` | Reservas por data |

### Monitor (`/api/v1/monitor`)

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/start` | Iniciar monitoramento automático |
| GET | `/{monitor_id}/status` | Status do monitoramento |
| POST | `/{monitor_id}/stop` | Parar monitoramento |
| GET | `/` | Listar monitores ativos |
| WebSocket | `/ws/{monitor_id}` | Atualizações em tempo real |

### Esportes (`/api/v1/sports`)

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/` | Listar esportes disponíveis |
| GET | `/{sport}` | Configuração do esporte |
| GET | `/{sport}/levels` | Níveis disponíveis |
| GET | `/{sport}/wave-sides` | Lados da onda (Surf) |
| GET | `/{sport}/combos` | Combinações válidas |
| GET | `/{sport}/packages` | IDs de pacotes |
| GET | `/{sport}/packages/{combo_key}` | Pacote específico |

### Sistema (`/api/v1/system`)

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/status` | Health check |

---

## MCP Server - Claude Integration

O servidor MCP expõe ferramentas e recursos para que o Claude possa interagir com o sistema de reservas.

### Ferramentas (Tools)

| Ferramenta | Descrição |
|------------|-----------|
| `check_availability` | Verificar slots disponíveis com filtros opcionais |
| `scan_availability` | Forçar atualização do cache de disponibilidade |
| `book_session` | Reservar sessão para um membro |
| `cancel_booking` | Cancelar reserva por código voucher |
| `list_bookings` | Listar reservas ativas |
| `get_members` | Obter lista de membros com status de uso |
| `get_member_preferences` | Obter preferências de um membro |
| `start_auto_monitor` | Iniciar monitoramento automático |
| `check_monitor_status` | Verificar status do monitor |

### Recursos (Resources)

| URI | Descrição |
|-----|-----------|
| `beyond://members` | Lista de membros com status de uso |
| `beyond://bookings` | Reservas ativas |
| `beyond://availability` | Cache de disponibilidade |
| `beyond://preferences` | Preferências de todos os membros |

### Exemplo de Uso com Claude

```
Usuário: "Quero reservar uma aula de surf para o Rafael amanhã às 8h"

Claude usa as ferramentas:
1. get_members() - Encontra o membro Rafael
2. check_availability(date="2025-12-25", level="Intermediario2") - Verifica slots
3. book_session(member_name="Rafael", date="2025-12-25", time="08:00") - Faz a reserva
```

---

## Knowledge Graph - AI Agents

O sistema mantém um grafo de conhecimento para análises semânticas e recomendações.

### Tipos de Nós

| Tipo | Descrição |
|------|-----------|
| `User` | Usuários do sistema (identificados por telefone) |
| `Member` | Membros Beyond com nome e status |
| `Sport` | Esportes (surf, tennis) |
| `Preference` | Preferências de sessão com prioridade |
| `Level` | Níveis de skill (Surf) |
| `WaveSide` | Lados da onda (Surf) |
| `Court` | Quadras (Tennis) |
| `TimeSlot` | Horários preferidos |
| `Booking` | Reservas com voucher/access code |
| `Slot` | Slots de sessão disponíveis |
| `Date` | Datas de sessão |

### Tipos de Arestas

| Tipo | Relação |
|------|---------|
| `HAS_MEMBER` | User → Member |
| `HAS_PREFERENCE` | Member → Preference |
| `FOR_SPORT` | Preference → Sport |
| `PREFERS_LEVEL` | Preference → Level |
| `PREFERS_WAVE_SIDE` | Preference → WaveSide |
| `PREFERS_COURT` | Preference → Court |
| `PREFERS_HOUR` | Member → TimeSlot |
| `BOOKED` | Member → Booking |
| `FOR_SLOT` | Booking → Slot |
| `ON_DATE` | Slot → Date |
| `HAS_LEVEL` | Slot → Level |
| `HAS_WAVE_SIDE` | Slot → WaveSide |
| `HAS_COURT` | Slot → Court |

### Queries Semânticas

O GraphService oferece consultas semânticas para AI Agents:

```python
# Encontrar slot ótimo baseado em preferências
graph_service.find_optimal_slot(member_id=12869, sport="surf")

# Encontrar membros com preferências similares
graph_service.find_similar_members(member_id=12869, sport="surf")

# Histórico de reservas do membro
graph_service.get_member_booking_history(member_id=12869)

# Combinações mais populares
graph_service.get_popular_combos(sport="surf", limit=5)

# Resumo completo do membro
graph_service.get_member_summary(member_id=12869)
```

### Endpoint do Graph

```http
GET /api/v1/members/{member_id}/graph-summary
```

Retorna:
- Preferências do membro
- Horários preferidos
- Histórico de reservas
- Membros similares

---

## Estrutura do Projeto

```
beyond-the-club/
├── api/                          # FastAPI REST API
│   ├── main.py                   # Aplicação FastAPI + APScheduler
│   ├── deps.py                   # Injeção de dependências
│   └── v1/                       # Endpoints v1
│       ├── auth.py               # Autenticação
│       ├── availability.py       # Disponibilidade
│       ├── bookings.py           # Reservas
│       ├── members.py            # Membros
│       ├── monitor.py            # Monitor WebSocket
│       ├── sports.py             # Configuração de esportes
│       └── system.py             # Health check
│
├── web/                          # Next.js Frontend
│   ├── src/app/                  # Pages (App Router)
│   ├── src/components/           # Componentes React
│   ├── src/hooks/                # Custom hooks
│   └── src/types/                # TypeScript types
│
├── mcp/                          # MCP Server (Claude)
│   ├── server.py                 # Servidor MCP principal
│   ├── context.py                # Inicialização de serviços
│   ├── tools/                    # Ferramentas MCP
│   └── resources/                # Recursos MCP
│
├── src/                          # Core Python
│   ├── bot.py                    # Orquestração principal
│   ├── beyond_api.py             # Cliente HTTP Beyond
│   ├── session_monitor.py        # Lógica de monitoramento
│   ├── config.py                 # Configurações
│   ├── packages.py               # Mapeamento de pacotes
│   ├── graph/                    # Knowledge Graph
│   │   ├── schema.py             # Definições de nós/arestas
│   │   ├── store.py              # Persistência NetworkX
│   │   └── queries.py            # Queries semânticas
│   ├── services/                 # Camada de serviços
│   │   ├── auth_service.py       # Autenticação Firebase
│   │   ├── user_auth_service.py  # Autenticação JWT
│   │   ├── member_service.py     # Operações de membros
│   │   ├── availability_service.py # Cache de disponibilidade
│   │   ├── booking_service.py    # Operações de reserva
│   │   ├── monitor_service.py    # Auto-monitor
│   │   ├── beyond_token_service.py # Cache de tokens
│   │   └── graph_service.py      # Operações do graph
│   └── auth/                     # Utilitários de autenticação
│       ├── users.py              # Model/CRUD de usuários
│       ├── jwt_handler.py        # Manipulação JWT
│       └── password.py           # Hash de senhas
│
├── main.py                       # CLI Entry point
├── docker-compose.yml            # Orquestração Docker
├── Dockerfile.api                # Container API
├── Dockerfile.web                # Container Web
├── Dockerfile.mcp                # Container MCP
└── requirements.txt              # Dependências Python
```

---

## Arquivos de Cache

O sistema mantém caches JSON para performance:

| Arquivo | Descrição |
|---------|-----------|
| `.beyondtheclub_tokens.json` | Tokens Firebase/Beyond |
| `.beyondtheclub_members.json` | Lista de membros |
| `.beyondtheclub_availability.json` | Cache de slots |
| `.beyondtheclub_preferences.json` | Preferências separadas |
| `data/graph.json` | Knowledge Graph persistido |
| `data/users.json` | Usuários do sistema |

### Estrutura do Cache de Membros

```json
{
  "members": [
    {
      "member_id": 12869,
      "name": "RAFAEL VINICIUS DE SIQUEIRA",
      "social_name": "RAFAEL",
      "is_titular": true,
      "usage": 0,
      "limit": 1
    }
  ],
  "last_updated": "2025-12-24T10:30:00"
}
```

### Estrutura de Preferências

```json
{
  "12869": {
    "surf": {
      "sessions": [
        {"attributes": {"level": "Intermediario2", "wave_side": "Lado_direito"}}
      ],
      "target_hours": ["08:00", "09:00"],
      "target_dates": []
    }
  }
}
```

---

## Deploy com Docker

### Desenvolvimento

```bash
# API + Web
docker-compose up -d

# Com MCP Server
docker-compose --profile mcp up -d

# Ver logs
docker-compose logs -f api
docker-compose logs -f web
```

### Produção

```bash
# Com nginx reverse proxy
docker-compose --profile production up -d
```

### Volumes Persistidos

- `./data` → `/app/data` (graph, users)
- `./.beyondtheclub_*.json` → Caches

---

## Configuração

### Variáveis de Ambiente

```bash
# Credenciais admin Beyond
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=sua_senha

# Telefone para SMS
PHONE_NUMBER=+5511999999999

# JWT Secret (produção)
JWT_SECRET_KEY=your-secret-key

# Database
DATABASE_URL=sqlite:///./data/beyond.db
```

### APScheduler (API)

A API executa tarefas agendadas:

- **Hourly**: Refresh de disponibilidade (minuto :00)
- **Admin Phone**: `+5511972741849` para tasks agendadas

---

## Autenticação

### Dois Níveis de Autenticação

1. **Aplicação (JWT)**
   - Registro com telefone + senha
   - Login retorna access_token + refresh_token
   - Tokens armazenados no browser/app

2. **Beyond API (Firebase)**
   - SMS enviado para telefone
   - Código verificado troca por Firebase tokens
   - Tokens cacheados por usuário

### Fluxo de Autenticação

```
1. Usuário faz login na aplicação (JWT)
2. Usuário solicita SMS do Beyond
3. Usuário insere código SMS
4. Sistema armazena tokens Beyond linkados ao usuário
5. Todas as operações usam os tokens do usuário
```

---

## CLI - Comandos

### Consulta

| Comando | Descrição |
|---------|-----------|
| `--sport <surf\|tennis>` | Seleciona o esporte |
| `--list-members` | Lista membros disponíveis |
| `--refresh-members` | Força refresh da API |
| `--check-status` | Status do sistema |
| `--inscriptions` | Inscrições do usuário |

### Configuração

| Comando | Descrição |
|---------|-----------|
| `--configure` | Configura preferências interativamente |

### Monitoramento

| Comando | Descrição |
|---------|-----------|
| `--member <ids>` | Membros para monitorar |
| `--once` | Verificação única |
| `--no-auto-book` | Apenas verificar, não reservar |

### Autenticação

| Comando | Descrição |
|---------|-----------|
| `--sms-code <código>` | Código SMS direto |
| `--no-cache` | Força re-autenticação |

### Debug

| Comando | Descrição |
|---------|-----------|
| `-v, --verbose` | Logs detalhados |

---

## Troubleshooting

### Token Beyond Expirado

```bash
# CLI
python main.py --no-cache

# Web UI
Dashboard > Settings > Verificar Beyond > Solicitar novo SMS
```

### Cache Desatualizado

```bash
# Membros
python main.py --list-members --refresh-members

# Disponibilidade via API
curl -X POST http://localhost:8000/api/v1/availability/scan
```

### Membro Não Encontrado

- Verifique nome (case insensitive) ou use ID numérico
- Faça refresh: `--refresh-members`

### WebSocket Não Conecta

- Verifique se Beyond está autenticado
- Use HTTPS em produção

---

## Logs

Logs são salvos em: `beyondtheclub_YYYYMMDD.log`

```
2025-12-24 10:30:00 | INFO | Checking sessions for RAFAEL...
2025-12-24 10:30:01 | INFO | [RAFAEL] Found: 2025-12-28 08:00 (Intermediario2 / Lado_direito)
2025-12-24 10:30:02 | INFO | [RAFAEL] Successfully booked session!
```

---

## Desenvolvimento

### Testes

```bash
# Unit tests
pytest tests/

# Com coverage
pytest --cov=src tests/
```

### Linting

```bash
# Python
ruff check .
black --check .

# TypeScript
cd web && npm run lint
```

### Build

```bash
# Docker images
docker-compose build

# Web standalone
cd web && npm run build
```

---

## Impacto para AI Agents

### MCP - O que os Agentes Podem Fazer

1. **Consultar Disponibilidade**: Verificar slots disponíveis com filtros
2. **Fazer Reservas**: Reservar sessões para membros
3. **Gerenciar Reservas**: Cancelar ou trocar membros
4. **Consultar Membros**: Ver status de uso e preferências
5. **Monitoramento Automático**: Iniciar/parar monitores

### Graph - Insights para Agentes

1. **Recomendações**: Slots ótimos baseados em preferências
2. **Similaridade**: Membros com gostos parecidos
3. **Histórico**: Padrões de reservas passadas
4. **Analytics**: Combinações mais populares

### Integração Sugerida

```python
# Agente pode usar GraphService para decisões inteligentes
optimal_slot = graph_service.find_optimal_slot(member_id, "surf")
similar = graph_service.find_similar_members(member_id)

# E MCP Tools para ações
mcp_tools.book_session(member_name, date, time)
```

---

## Contribuição

1. Fork o repositório
2. Crie branch: `git checkout -b feature/nova-feature`
3. Commit: `git commit -m 'Add nova feature'`
4. Push: `git push origin feature/nova-feature`
5. Abra Pull Request

---

## Licença

MIT License - veja LICENSE para detalhes.
