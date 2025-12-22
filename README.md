# BeyondTheClub Sport Session Booking Bot

Bot automatizado para monitorar e reservar sessões de esportes no Beyond The Club.

## Esportes Suportados

| Esporte | Argumento | Atributos |
|---------|-----------|-----------|
| Surf | `--sport surf` (padrão) | Nível + Lado da onda |
| Tennis | `--sport tennis` | Quadra |

## Funcionalidades

- **Multi-esporte**: Suporte a surf, tennis e outros esportes
- **Multi-membro**: Monitorar e reservar para múltiplos membros do mesmo título
- **Preferências individuais**: Cada membro pode ter suas próprias preferências por esporte
- **Priorização**: Sessões são buscadas na ordem de prioridade configurada
- **Cache inteligente**: Cache de tokens e membros para performance
- Suporte a múltiplos níveis de surf: Iniciante1, Iniciante2, Intermediario1, Intermediario2, Avançado1, Avançado2
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

# Esportes disponíveis
SPORTS=surf,tennis

# Configurações de Surf
SURF_LEVELS=Iniciante1,Iniciante2,Intermediario1,Intermediario2,Avançado1,Avançado2
SURF_WAVE_SIDES=Lado_esquerdo,Lado_direito

# Configurações de Tennis
TENNIS_COURTS=Quadra_Saibro

# Configurações do bot
CHECK_INTERVAL_SECONDS=60
AUTO_BOOK=true
```

---

## Comandos CLI

### Comandos de Consulta

| Comando | Descrição |
|---------|-----------|
| `--sport <surf\|tennis>` | Seleciona o esporte (padrão: surf) |
| `--list-members` | Lista todos os membros disponíveis no título |
| `--refresh-members` | Força atualização da lista de membros da API |
| `--check-status` | Verifica status do sistema do esporte selecionado |
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
# Surf (padrão)
python main.py --list-members

# Tennis
python main.py --sport tennis --list-members

# Força refresh da API
python main.py --list-members --refresh-members
```

Saída:
```
Membros disponíveis (SURF):
  1. [12869] RAFAEL (Titular) - Uso: 0/1 - Prefs: ✓
  2. [16230] GABRIEL - Uso: 0/1 - Prefs: ✗
  3. [14002] JULIA - Uso: 0/1 - Prefs: ✗
```

### 2. Configurar preferências de um membro

```bash
# Surf
python main.py --configure

# Tennis
python main.py --sport tennis --configure
```

#### Exemplo de fluxo para Surf:
```
Membros disponíveis (SURF):
  1. [12869] RAFAEL (Titular) - Uso: 0/1 - Prefs: ✓
  2. [16230] GABRIEL - Uso: 0/1 - Prefs: ✗

Selecione o membro para configurar (número): 1

RAFAEL possui preferências de Surf configuradas:
  1. Iniciante1 / Lado_esquerdo
  2. Iniciante2 / Lado_direito
  Horários: 08:00, 09:00

Deseja manter estas preferências? (s/n): n
Apagando preferências anteriores...

Configurando preferências de Surf para RAFAEL...

Adicionar sessão de interesse:
  Nível disponíveis:
    1. Iniciante1
    2. Iniciante2
    3. Intermediario1
    4. Intermediario2
    5. Avançado1
    6. Avançado2
  Nível (número): 1
  Lado disponíveis:
    1. Lado_esquerdo
    2. Lado_direito
  Lado (número): 1
  Adicionado: Iniciante1 / Lado_esquerdo

Adicionar outra? (s/n): s
...

Horários preferidos (ex: 08:00,09:00 ou Enter para todos): 08:00,09:00
Datas específicas (ex: 2025-01-15,2025-01-16 ou Enter para todas):

Preferências de Surf salvas para RAFAEL:
  1. Iniciante1 / Lado_esquerdo (prioridade 1)
  2. Iniciante2 / Lado_direito (prioridade 2)
  Horários: 08:00, 09:00
```

#### Exemplo de fluxo para Tennis:
```bash
$ python main.py --sport tennis --configure

Membros disponíveis (TENNIS):
  1. [12869] RAFAEL (Titular) - Uso: 0/1 - Prefs: ✗

Selecione o membro para configurar (número): 1

Configurando preferências de Tennis para RAFAEL...

Adicionar sessão de interesse:
  Quadra disponíveis:
    1. Quadra_Saibro
  Quadra (número): 1
  Adicionado: Quadra_Saibro

Adicionar outra? (s/n): n

Horários preferidos (ex: 08:00,09:00 ou Enter para todos): 10:00,14:00

Preferências de Tennis salvas para RAFAEL:
  1. Quadra_Saibro (prioridade 1)
  Horários: 10:00, 14:00
```

### 3. Monitorar sessões

```bash
# Surf (padrão)
python main.py --member rafael

# Tennis
python main.py --sport tennis --member rafael

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

# Tennis
python main.py --sport tennis --member rafael --once
```

### 5. Ver inscrições

```bash
# Surf
python main.py --inscriptions

# Tennis
python main.py --sport tennis --inscriptions
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

### `.beyondtheclub_members.json`

Cache de membros e suas preferências (separadas por esporte).

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
  "preferences": {
    "12869": {
      "surf": {
        "sessions": [
          {"attributes": {"level": "Iniciante1", "wave_side": "Lado_esquerdo"}},
          {"attributes": {"level": "Avançado1", "wave_side": "Lado_direito"}}
        ],
        "target_hours": ["08:00", "09:00"],
        "target_dates": []
      },
      "tennis": {
        "sessions": [
          {"attributes": {"court": "Quadra_Saibro"}}
        ],
        "target_hours": ["10:00", "14:00"],
        "target_dates": []
      }
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
| `{sport}` | object | Preferências separadas por esporte (surf, tennis) |
| `{sport}.sessions` | array | Lista de preferências de sessão em ordem de prioridade |
| `{sport}.sessions[].attributes` | object | Atributos da sessão (varia por esporte) |
| `{sport}.target_hours` | array | Horários preferidos (ex: ["08:00", "09:00"]) |
| `{sport}.target_dates` | array | Datas específicas (ex: ["2025-01-15"]) |

#### Atributos por Esporte

| Esporte | Atributos |
|---------|-----------|
| surf | `level`, `wave_side` |
| tennis | `court` |

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
1. Selecionar esporte (--sport)
2. Carregar membros (cache ou API)
3. Selecionar membro(s) para monitorar
4. Validar/configurar preferências de cada membro para o esporte
5. Para cada membro:
   a. Para cada preferência (em ordem de prioridade):
      - Buscar datas disponíveis
      - Para cada data:
        - Buscar sessões disponíveis
        - Filtrar por horário (se configurado)
        - Filtrar por data (se configurado)
   b. Se encontrar sessão disponível:
      - Reservar (passando member_id)
      - Registrar no cache de sessões reservadas
6. Aguardar intervalo e repetir (se não for --once)
```

---

## Logs

Os logs são salvos em arquivos diários: `beyondtheclub_YYYYMMDD.log`

Exemplo de log durante monitoramento:
```
2025-12-22 10:30:00 | INFO     | Checking sessions for RAFAEL...
2025-12-22 10:30:01 | INFO     | [RAFAEL] Checking Iniciante1 / Lado_esquerdo
2025-12-22 10:30:02 | INFO     | [RAFAEL] Found 3 dates for Iniciante1 / Lado_esquerdo
2025-12-22 10:30:03 | INFO     | [RAFAEL] Found: 2025-12-28 08:00 (Iniciante1 / Lado_esquerdo) - 2 spots
2025-12-22 10:30:03 | INFO     | [RAFAEL] Booking: 2025-12-28 08:00 (Iniciante1 / Lado_esquerdo)
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
    ├── config.py                    # Dataclasses de configuração + SportConfig
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
| `bot.py` | Orquestração, cache de membros/tokens, preferências por esporte |
| `session_monitor.py` | Busca de sessões, booking, filtros (genérico por esporte) |
| `beyond_api.py` | Chamadas HTTP à API do Beyond (parametrizadas por esporte) |
| `firebase_auth.py` | Autenticação e refresh de tokens Firebase |
| `sms_auth.py` | Fluxo de autenticação via SMS |
| `config.py` | Carregamento de configurações do .env + SportConfig |

---

## API Endpoints Utilizados

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/schedules/{sport}/status` | GET | Lista membros e uso de sessões |
| `/schedules/{sport}/dates` | GET | Datas disponíveis para atributos |
| `/schedules/{sport}/times` | GET | Horários disponíveis para data/atributos |
| `/schedules/{sport}/book` | POST | Reservar sessão |
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

### Esporte incorreto
Verifique se está usando o argumento `--sport` correto:
```bash
# Para tennis
python main.py --sport tennis --configure
```
