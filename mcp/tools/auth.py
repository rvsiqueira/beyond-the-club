"""
Authentication tools for MCP.

Handles Beyond API (Firebase) authentication for voice agents and other clients.
The flow is:
1. Agent calls check_auth_status(phone) to see if user is authenticated
2. If not, agent calls request_beyond_sms(phone) to send SMS code
3. Agent asks user for the SMS code
4. Agent calls verify_beyond_sms(phone, code, session_info) to complete auth
5. Now agent can call other tools (bookings, members, etc.)
"""

import logging
from typing import Optional

from ..context import get_services

logger = logging.getLogger(__name__)

# Store session info temporarily (in-memory for MCP session)
_pending_sessions = {}


async def check_auth_status(phone: str) -> str:
    """
    Check if a phone number has valid Beyond API authentication.

    Use this BEFORE calling other tools to verify the user is authenticated.
    If not authenticated, the agent should initiate the SMS flow.

    Args:
        phone: Phone number to check (e.g., '+5511999999999')

    Returns:
        Authentication status and instructions
    """
    services = get_services()

    # Check if user has valid Beyond token
    has_token = services.beyond_tokens.has_valid_token(phone)
    token = services.beyond_tokens.get_token(phone)

    if has_token:
        # Get expiration info
        import time
        expires_in = int(token.expires_at - time.time()) if token else 0
        expires_min = expires_in // 60

        return f"""✅ Autenticado!

📱 Telefone: {phone}
⏱️ Token válido por: {expires_min} minutos

Você pode usar as ferramentas de booking, members, availability, etc."""

    elif token:
        # Has token but expired
        return f"""⚠️ Token expirado!

📱 Telefone: {phone}

O token Beyond expirou. Para renovar:
1. Chame request_beyond_sms(phone="{phone}")
2. Peça ao usuário o código SMS recebido
3. Chame verify_beyond_sms(phone="{phone}", code="XXXXXX", session_info="...")"""

    else:
        # No token at all
        return f"""❌ Não autenticado!

📱 Telefone: {phone}

Este telefone não possui autenticação Beyond configurada.

Para autenticar:
1. Chame request_beyond_sms(phone="{phone}")
2. Peça ao usuário o código SMS de 6 dígitos recebido
3. Chame verify_beyond_sms(phone="{phone}", code="XXXXXX", session_info="...")

Após autenticação, você poderá usar as ferramentas de booking, members, etc."""


async def request_beyond_sms(phone: str) -> str:
    """
    Request an SMS verification code for Beyond API authentication.

    This will send an SMS to the specified phone number with a 6-digit code.
    Save the session_info returned - it's needed for verify_beyond_sms.

    Args:
        phone: Phone number to send SMS to (e.g., '+5511999999999')

    Returns:
        Session info needed for verification, or error message
    """
    services = get_services()

    try:
        # Request SMS
        session_info = services.beyond_tokens.request_sms(phone)

        # Store session for later
        _pending_sessions[phone] = session_info

        return f"""📱 SMS enviado com sucesso!

📞 Telefone: {phone}
🔑 Session: {session_info}

Próximo passo:
Peça ao usuário o código de 6 dígitos que ele recebeu por SMS.
Depois chame:
  verify_beyond_sms(phone="{phone}", code="XXXXXX", session_info="{session_info}")"""

    except Exception as e:
        return f"""❌ Erro ao enviar SMS!

📞 Telefone: {phone}
⚠️ Erro: {str(e)}

Possíveis causas:
- Número de telefone inválido
- Telefone não cadastrado no Beyond
- Limite de SMS atingido (tente novamente em alguns minutos)"""


async def verify_beyond_sms(
    phone: str,
    code: str,
    session_info: Optional[str] = None
) -> str:
    """
    Verify the SMS code and complete Beyond API authentication.

    After successful verification, the token is saved and the phone
    can use all Beyond API features (bookings, members, etc.).

    Args:
        phone: Phone number that received the SMS
        code: 6-digit code from SMS
        session_info: Session info from request_beyond_sms (optional, auto-retrieved if not provided)

    Returns:
        Success message or error
    """
    services = get_services()

    # Get session_info from cache if not provided
    if not session_info:
        session_info = _pending_sessions.get(phone)
        if not session_info:
            return f"""❌ Sessão não encontrada!

📞 Telefone: {phone}

Não foi encontrada uma sessão SMS pendente para este telefone.
Por favor, chame request_beyond_sms primeiro para enviar um novo código."""

    try:
        # Verify SMS and get tokens
        services.beyond_tokens.verify_sms(
            beyond_phone=phone,
            code=code,
            session_info=session_info,
            store_for_phone=phone  # Store linked to the same phone
        )

        # Clear pending session
        if phone in _pending_sessions:
            del _pending_sessions[phone]

        # Initialize the API with the new token
        id_token = services.beyond_tokens.get_valid_id_token(phone)
        if id_token:
            # Try to initialize services
            try:
                services.context.initialize_beyond_api(id_token)
            except Exception:
                pass  # API initialization will happen on first use

        return f"""✅ Autenticação concluída com sucesso!

📞 Telefone: {phone}
🔐 Token: Salvo e válido

Agora você pode usar todas as ferramentas:
• get_members() - Ver membros
• list_bookings() - Ver agendamentos
• book_session(...) - Fazer reservas
• check_availability() - Ver disponibilidade
• E mais..."""

    except Exception as e:
        error_msg = str(e)

        # Provide helpful error messages
        if "invalid" in error_msg.lower() or "expired" in error_msg.lower():
            return f"""❌ Código inválido ou expirado!

📞 Telefone: {phone}
🔢 Código informado: {code}

O código SMS é inválido ou expirou.
Códigos expiram após alguns minutos.

Para tentar novamente:
1. Chame request_beyond_sms(phone="{phone}") para enviar novo código
2. Informe o novo código de 6 dígitos"""

        return f"""❌ Erro na verificação!

📞 Telefone: {phone}
⚠️ Erro: {error_msg}

Tente novamente com request_beyond_sms para enviar novo código."""


async def get_authenticated_phone() -> str:
    """
    Get a list of all phones with valid Beyond authentication.

    Useful for checking which users are currently authenticated.

    Returns:
        List of authenticated phones with status
    """
    services = get_services()

    import time

    tokens = services.beyond_tokens._tokens_cache

    if not tokens:
        return "📋 Nenhum telefone autenticado no momento."

    lines = ["📋 Telefones autenticados:\n"]

    for phone, token in tokens.items():
        is_valid = token.expires_at > time.time() + 60
        expires_in = int(token.expires_at - time.time())
        expires_min = max(0, expires_in // 60)

        status = "✅" if is_valid else "⚠️ Expirado"
        lines.append(f"• {phone} {status}")
        if is_valid:
            lines.append(f"  ⏱️ Expira em {expires_min} minutos")
        lines.append("")

    return "\n".join(lines)
