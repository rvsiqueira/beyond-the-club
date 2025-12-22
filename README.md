# BeyondTheClub Surf Session Booking Bot

Bot automatizado para monitorar e reservar sessões de surf no Beyond The Club.

## Funcionalidades

- **Multi-membro**: Monitorar e reservar para múltiplos membros do mesmo título
- **Preferências individuais**: Cada membro pode ter suas próprias preferências de sessão
- **Priorização**: Sessões são buscadas na ordem de prioridade configurada
- **Cache inteligente**: Cache de tokens e membros para performance
- Suporte a múltiplos níveis: Iniciante1, Iniciante2, Intermediario1, Intermediario2, Avançado1, Avançado2
- Suporte a ambos lados da onda: Lado_esquerdo, Lado_direito
- Filtro por horários específicos
- Filtro por datas específicas
- Reserva automática quando sessão disponível

## Instalação

```bash
# Criar ambiente virtual
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Instalar dependências
pip install -r requirements.txt

# Configurar
cp .env.example .env
# Edite o arquivo .env com suas configurações
```

## Configuração

Edite o arquivo `.env` com suas credenciais:

```bash
# Credenciais admin
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=sua_senha

# Seu telefone
PHONE_NUMBER=+5511999999999

# Configurações globais (fallback se não usar preferências por membro)
SESSION_LEVELS=Iniciante1,Iniciante2
WAVE_SIDES=Lado_esquerdo,Lado_direito
TARGET_HOURS=08:00,10:00,14:00
TARGET_DATES=2024-01-15,2024-01-20

# Configurações do bot
CHECK_INTERVAL_SECONDS=60
AUTO_BOOK=true
```

---

## Comandos CLI

### Comandos de Consulta

| Comando | Descrição |
|---------|-----------|
| `--list-members` | Lista todos os membros disponíveis no título |
| `--refresh-members` | Força atualização da lista de membros da API |
| `--check-status` | Verifica status do sistema de surf |
| `--inscriptions` | Mostra inscrições do usuário |

### Comandos de Configuração

| Comando | Descrição |
|---------|-----------|
| `--configure` | Configura preferências de sessão para um membro |

### Comandos de Monitoramento

| Comando | Descrição |
|---------|-----------|
| `--member <ids>` | Seleciona membro(s) para monitorar (ID, nome ou lista separada por vírgula) |
| `--once` | Executa verificação única (não fica em loop) |
| `--no-auto-book` | Apenas verifica disponibilidade, não reserva |

### Comandos de Autenticação

| Comando | Descrição |
|---------|-----------|
| `--sms-code <código>` | Fornece código SMS diretamente (pula prompt) |
| `--no-cache` | Força re-autenticação (ignora tokens em cache) |

### Outros

| Comando | Descrição |
|---------|-----------|
| `-v, --verbose` | Habilita logs detalhados (debug) |

---

## Uso

### 1. Listar membros disponíveis

```bash
# Usa cache (rápido)
python main.py --list-members

# Força refresh da API
python main.py --list-members --refresh-members
```

Saída:
```
Membros disponíveis:
  1. [12869] RAFAEL (Titular) - Uso: 0/1 - Prefs: ✓
  2. [16230] GABRIEL - Uso: 0/1 - Prefs: ✗
  3. [14002] JULIA - Uso: 0/1 - Prefs: ✗
```

### 2. Configurar preferências de um membro

```bash
python main.py --configure
```

Fluxo interativo:
```
Membros disponíveis:
  1. [12869] RAFAEL (Titular) - Uso: 0/1 - Prefs: ✓
  2. [16230] GABRIEL - Uso: 0/1 - Prefs: ✗

Selecione o membro para configurar (número): 1

RAFAEL já possui preferências configuradas:
  1. Iniciante1 / Lado_esquerdo
  2. Iniciante2 / Lado_direito
  Horários: 08:00, 09:00

Deseja manter estas preferências? (s/n): n
Apagando preferências anteriores...

Configurando preferências para RAFAEL...

Adicionar sessão de interesse:
  Níveis disponíveis:
    1. Iniciante1
    2. Iniciante2
    3. Intermediario1
    4. Intermediario2
    5. Avançado1
    6. Avançado2
  Nível (número): 1
  Lados disponíveis:
    1. Lado_esquerdo
    2. Lado_direito
  Lado (número): 1
  Adicionado: Iniciante1 / Lado_esquerdo

Adicionar outra? (s/n): s
...

Horários preferidos (ex: 08:00,09:00 ou Enter para todos): 08:00,09:00
Datas específicas (ex: 2025-01-15,2025-01-16 ou Enter para todas):

Preferências salvas para RAFAEL:
  1. Iniciante1 / Lado_esquerdo (prioridade 1)
  2. Iniciante2 / Lado_direito (prioridade 2)
  Horários: 08:00, 09:00
```

### 3. Monitorar sessões

```bash
# Um membro por ID
python main.py --member 12869

# Um membro por nome (case insensitive)
python main.py --member rafael

# Múltiplos membros
python main.py --member rafael,gabriel,julia

# Interativo (se não passar --member)
python main.py
> Selecione o(s) membro(s) para monitorar (ex: 1,2,3 ou "todos"): 1,2
> Monitorando para RAFAEL, GABRIEL...
```

### 4. Verificação única

```bash
# Uma verificação e sai
python main.py --member rafael --once

# Sem reservar automaticamente
python main.py --member rafael --once --no-auto-book
```

### 5. Ver inscrições

```bash
python main.py --inscriptions
```

Saída:
```
Found 5 inscription(s):
  1. 2025-11-25 - RAFAEL - Direito a 1 Swell cortesia
     Usos: 0/1 - Usado
  2. 2025-12-15 - RAFAEL - Direito a 1 Swell cortesia
     Usos: 1/1 - Disponível
```

---

## Arquivos de Cache

O bot mantém dois arquivos de cache na raiz do projeto:

### `.beyondtheclub_tokens.json`

Cache de tokens de autenticação Firebase.

```json
{
  "id_token": "eyJhbGciOiJSUzI1NiIs...",
  "refresh_token": "AMf-vBw...",
  "expires_at": 1703123456.789
}
```

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id_token` | string | Token JWT do Firebase |
| `refresh_token` | string | Token para renovação |
| `expires_at` | float | Timestamp Unix de expiração |

### `.beyondtheclub_members.json`

Cache de membros e suas preferências.

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
    },
    {
      "member_id": 16230,
      "name": "GABRIEL NEVES SIQUEIRA",
      "social_name": "GABRIEL",
      "is_titular": false,
      "usage": 0,
      "limit": 1
    }
  ],
  "preferences": {
    "12869": {
      "sessions": [
        {"level": "Iniciante1", "wave_side": "Lado_esquerdo"},
        {"level": "Iniciante2", "wave_side": "Lado_direito"}
      ],
      "target_hours": ["08:00", "09:00"],
      "target_dates": []
    }
  },
  "last_updated": "2025-12-22T10:30:00.123456"
}
```

#### Estrutura `members[]`

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `member_id` | int | ID único do membro na API |
| `name` | string | Nome completo |
| `social_name` | string | Nome social (apelido) |
| `is_titular` | bool | Se é o titular do título |
| `usage` | int | Sessões já usadas no período |
| `limit` | int | Limite de sessões no período |

#### Estrutura `preferences{}`

Chave: `member_id` como string

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `sessions` | array | Lista de preferências de sessão em ordem de prioridade |
| `sessions[].level` | string | Nível: Iniciante1, Iniciante2, Intermediario1, Intermediario2, Avançado1, Avançado2 |
| `sessions[].wave_side` | string | Lado: Lado_esquerdo, Lado_direito |
| `target_hours` | array | Horários preferidos (ex: ["08:00", "09:00"]) |
| `target_dates` | array | Datas específicas (ex: ["2025-01-15"]) |

---

## Fluxo de Autenticação

1. O bot autentica com credenciais admin no Firebase
2. Envia SMS para seu número de telefone
3. Você digita o código SMS recebido
4. O bot troca o código por tokens de acesso
5. Tokens são salvos em `.beyondtheclub_tokens.json` para uso futuro

---

## Fluxo de Monitoramento

```
1. Carregar membros (cache ou API)
2. Selecionar membro(s) para monitorar
3. Validar/configurar preferências de cada membro
4. Para cada membro:
   a. Para cada preferência (em ordem de prioridade):
      - Buscar datas disponíveis
      - Para cada data:
        - Buscar sessões disponíveis
        - Filtrar por horário (se configurado)
        - Filtrar por data (se configurado)
   b. Se encontrar sessão disponível:
      - Reservar (passando member_id)
      - Registrar no cache de sessões reservadas
5. Aguardar intervalo e repetir (se não for --once)
```

---

## Logs

Os logs são salvos em arquivos diários: `beyondtheclub_YYYYMMDD.log`

Exemplo de log durante monitoramento:
```
2025-12-22 10:30:00 | INFO     | Checking sessions for RAFAEL...
2025-12-22 10:30:01 | INFO     | [RAFAEL] Checking Iniciante1 / Lado_esquerdo
2025-12-22 10:30:02 | INFO     | [RAFAEL] Found 3 dates for Iniciante1/Lado_esquerdo
2025-12-22 10:30:03 | INFO     | [RAFAEL] Found: 2025-12-28 08:00 (Iniciante1/Lado_esquerdo) - 2 spots
2025-12-22 10:30:03 | INFO     | [RAFAEL] Booking: 2025-12-28 08:00 (Iniciante1/Lado_esquerdo)
2025-12-22 10:30:04 | INFO     | [RAFAEL] Successfully booked session 12345!
```

---

## Estrutura do Projeto

```
BeyondTheClub/
├── main.py                          # Script principal e CLI
├── requirements.txt                 # Dependências Python
├── .env.example                     # Exemplo de configuração
├── .env                             # Configuração (não versionado)
├── .gitignore
├── .beyondtheclub_tokens.json       # Cache de tokens (não versionado)
├── .beyondtheclub_members.json      # Cache de membros (não versionado)
└── src/
    ├── __init__.py
    ├── config.py                    # Dataclasses de configuração
    ├── firebase_auth.py             # Autenticação Firebase
    ├── sms_auth.py                  # Autenticação via SMS
    ├── beyond_api.py                # Cliente HTTP da API Beyond
    ├── session_monitor.py           # Lógica de busca e booking
    └── bot.py                       # Orquestrador e cache de membros
```

### Módulos

| Módulo | Responsabilidade |
|--------|------------------|
| `main.py` | CLI, parsing de argumentos, fluxos interativos |
| `bot.py` | Orquestração, cache de membros/tokens, preferências |
| `session_monitor.py` | Busca de sessões, booking, filtros |
| `beyond_api.py` | Chamadas HTTP à API do Beyond |
| `firebase_auth.py` | Autenticação e refresh de tokens Firebase |
| `sms_auth.py` | Fluxo de autenticação via SMS |
| `config.py` | Carregamento de configurações do .env |

---

## API Endpoints Utilizados

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/schedules/surf/status` | GET | Lista membros e uso de sessões |
| `/schedules/surf/dates` | GET | Datas disponíveis para nível/lado |
| `/schedules/surf/times` | GET | Horários disponíveis para data/nível/lado |
| `/schedules/surf/book` | POST | Reservar sessão |
| `/inscriptions` | GET | Inscrições do usuário |

---

## Troubleshooting

### Token expirado
```bash
python main.py --no-cache
```

### Lista de membros desatualizada
```bash
python main.py --list-members --refresh-members
```

### Membro não encontrado
Verifique se o nome está correto (case insensitive) ou use o ID numérico.

### Preferências não configuradas
O bot obriga configurar preferências antes de iniciar monitoramento. Use `--configure` ou será solicitado automaticamente.
