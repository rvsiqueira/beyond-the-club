# BeyondTheClub Surf Session Booking Bot

Bot automatizado para monitorar e reservar sessões de surf no Beyond The Club.

## Funcionalidades

- Monitoramento automático a cada 1 minuto
- Suporte a múltiplos níveis: Iniciante1, Iniciante2, Intermediario1
- Suporte a ambos lados da onda: Lado_esquerdo, Lado_direito
- Filtro por horários específicos
- Filtro por datas específicas
- Reserva automática quando sessão disponível
- Cache de tokens para evitar re-autenticação

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

Edite o arquivo `.env` com suas preferências:

```bash
# Seu telefone
PHONE_NUMBER=+5511999999999

# Níveis que você quer monitorar
SESSION_LEVELS=Iniciante1,Iniciante2

# Lados da onda
WAVE_SIDES=Lado_esquerdo,Lado_direito

# Horários específicos (opcional)
TARGET_HOURS=08:00,10:00,14:00

# Datas específicas (opcional)
TARGET_DATES=2024-01-15,2024-01-20
```

## Uso

### Modo contínuo (padrão)
```bash
python main.py
```

### Verificação única
```bash
python main.py --once
```

### Apenas verificar disponibilidade (sem reservar)
```bash
python main.py --no-auto-book
```

### Com código SMS já em mãos
```bash
python main.py --sms-code 123456
```

### Forçar re-autenticação
```bash
python main.py --no-cache
```

### Verificar status do sistema
```bash
python main.py --check-status
```

## Fluxo de Autenticação

1. O bot autentica com credenciais admin no Firebase
2. Envia SMS para seu número de telefone
3. Você digita o código SMS recebido
4. O bot troca o código por tokens de acesso
5. Tokens são salvos em cache para uso futuro

## Logs

Os logs são salvos em arquivos diários: `beyondtheclub_YYYYMMDD.log`

## Estrutura do Projeto

```
BeyondTheClub/
├── main.py              # Script principal
├── requirements.txt     # Dependências
├── .env.example        # Exemplo de configuração
├── .gitignore
└── src/
    ├── __init__.py
    ├── config.py        # Configurações
    ├── firebase_auth.py # Autenticação Firebase
    ├── sms_auth.py      # Autenticação SMS
    ├── beyond_api.py    # Cliente da API
    ├── session_monitor.py # Monitor de sessões
    └── bot.py           # Orquestrador principal
```
