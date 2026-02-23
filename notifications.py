"""
notifications.py - Sistema de notificaciones privadas del bot SALLY-E
Envía mensajes directos al usuario con detección automática de idioma.

Tipos de notificaciones:
  - Bienvenida al unirse al canal
  - Depósito confirmado
  - Retiro procesado / rechazado
  - Plan activado
  - Referido validado (al referidor)
  - Mensaje genérico al enviar cualquier mensaje al bot
"""

import os
import logging
import asyncio
import aiohttp
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

logger = logging.getLogger(__name__)

BOT_TOKEN  = os.environ.get('BOT_TOKEN', '')
WEBAPP_URL = os.environ.get('WEBAPP_URL', 'https://M22.pythonanywhere.com')
BOT_USERNAME = os.environ.get('BOT_USERNAME', 'SallyEbot')

# ──────────────────────────────────────────────
#  IDIOMAS  (detectados por language_code de Telegram)
# ──────────────────────────────────────────────

# Mapa language_code → clave de idioma soportado
LANG_MAP = {
    # Español / Latinoamérica
    'es': 'es', 'es-419': 'es', 'es-ar': 'es', 'es-bo': 'es', 'es-cl': 'es',
    'es-co': 'es', 'es-cr': 'es', 'es-cu': 'es', 'es-do': 'es', 'es-ec': 'es',
    'es-sv': 'es', 'es-gt': 'es', 'es-hn': 'es', 'es-mx': 'es', 'es-ni': 'es',
    'es-pa': 'es', 'es-py': 'es', 'es-pe': 'es', 'es-pr': 'es', 'es-uy': 'es',
    'es-ve': 'es',
    # Portugués
    'pt': 'pt', 'pt-br': 'pt', 'pt-pt': 'pt',
    # Francés
    'fr': 'fr',
    # Inglés (fallback principal)
    'en': 'en', 'en-us': 'en', 'en-gb': 'en',
}

def detect_lang(language_code: str | None) -> str:
    """Detecta el idioma a partir del language_code de Telegram."""
    if not language_code:
        return 'es'  # Mayoría de usuarios son hispanohablantes
    lc = language_code.lower()
    # Primero intento exacto, luego prefijo de 2 letras
    return LANG_MAP.get(lc) or LANG_MAP.get(lc[:2]) or 'en'


# ──────────────────────────────────────────────
#  TEXTOS DE NOTIFICACIONES
# ──────────────────────────────────────────────

NOTIF_TEXTS = {

    # ── 1. BIENVENIDA (cuando se unen al canal/bot) ──────────────
    'welcome': {
        'es': (
            "👋 <b>¡Bienvenido/a a SALLY-E, {name}!</b>\n\n"
            "🎉 Ya formas parte de nuestra comunidad.\n\n"
            "💰 Gana tokens minando automáticamente\n"
            "✅ Completa tareas y obtén recompensas\n"
            "👥 Invita amigos y gana comisiones\n"
            "💸 Retira en USDT, DOGE o TON\n\n"
            "👇 <b>Presiona el botón para abrir la app:</b>"
        ),
        'en': (
            "👋 <b>Welcome to SALLY-E, {name}!</b>\n\n"
            "🎉 You are now part of our community.\n\n"
            "💰 Earn tokens by auto-mining\n"
            "✅ Complete tasks and get rewards\n"
            "👥 Invite friends and earn commissions\n"
            "💸 Withdraw in USDT, DOGE or TON\n\n"
            "👇 <b>Press the button to open the app:</b>"
        ),
        'pt': (
            "👋 <b>Bem-vindo(a) ao SALLY-E, {name}!</b>\n\n"
            "🎉 Você agora faz parte da nossa comunidade.\n\n"
            "💰 Ganhe tokens com mineração automática\n"
            "✅ Complete tarefas e receba recompensas\n"
            "👥 Convide amigos e ganhe comissões\n"
            "💸 Saque em USDT, DOGE ou TON\n\n"
            "👇 <b>Pressione o botão para abrir o app:</b>"
        ),
        'fr': (
            "👋 <b>Bienvenue sur SALLY-E, {name}!</b>\n\n"
            "🎉 Vous faites maintenant partie de notre communauté.\n\n"
            "💰 Gagnez des tokens par le minage automatique\n"
            "✅ Complétez des tâches pour obtenir des récompenses\n"
            "👥 Invitez des amis et gagnez des commissions\n"
            "💸 Retirez en USDT, DOGE ou TON\n\n"
            "👇 <b>Appuyez sur le bouton pour ouvrir l'app:</b>"
        ),
    },

    # ── 2. DEPÓSITO CONFIRMADO ───────────────────────────────────
    'deposit_confirmed': {
        'es': (
            "✅ <b>¡Depósito Confirmado!</b>\n\n"
            "💵 <b>Monto:</b> {amount} {currency}\n"
            "🪙 <b>Crédito recibido:</b> {credited} S-E\n"
            "🕐 <b>Fecha:</b> {date}\n"
            "🆔 <b>ID depósito:</b> <code>{deposit_id}</code>\n\n"
            "Tu saldo ha sido actualizado. ¡Sigue minando! ⛏️"
        ),
        'en': (
            "✅ <b>Deposit Confirmed!</b>\n\n"
            "💵 <b>Amount:</b> {amount} {currency}\n"
            "🪙 <b>Credited:</b> {credited} S-E\n"
            "🕐 <b>Date:</b> {date}\n"
            "🆔 <b>Deposit ID:</b> <code>{deposit_id}</code>\n\n"
            "Your balance has been updated. Keep mining! ⛏️"
        ),
        'pt': (
            "✅ <b>Depósito Confirmado!</b>\n\n"
            "💵 <b>Valor:</b> {amount} {currency}\n"
            "🪙 <b>Creditado:</b> {credited} S-E\n"
            "🕐 <b>Data:</b> {date}\n"
            "🆔 <b>ID depósito:</b> <code>{deposit_id}</code>\n\n"
            "Seu saldo foi atualizado. Continue minerando! ⛏️"
        ),
        'fr': (
            "✅ <b>Dépôt Confirmé!</b>\n\n"
            "💵 <b>Montant:</b> {amount} {currency}\n"
            "🪙 <b>Crédité:</b> {credited} S-E\n"
            "🕐 <b>Date:</b> {date}\n"
            "🆔 <b>ID dépôt:</b> <code>{deposit_id}</code>\n\n"
            "Votre solde a été mis à jour. Continuez à miner! ⛏️"
        ),
    },

    # ── 3. RETIRO PROCESADO (aprobado) ──────────────────────────
    'withdrawal_approved': {
        'es': (
            "💸 <b>¡Retiro Procesado!</b>\n\n"
            "✅ Tu retiro ha sido aprobado y enviado.\n\n"
            "💵 <b>Monto:</b> {amount} {currency}\n"
            "📬 <b>Dirección:</b> <code>{wallet}</code>\n"
            "🕐 <b>Fecha:</b> {date}\n"
            "🆔 <b>ID retiro:</b> <code>{withdrawal_id}</code>\n\n"
            "El pago puede tardar unos minutos en reflejarse. 🙌"
        ),
        'en': (
            "💸 <b>Withdrawal Processed!</b>\n\n"
            "✅ Your withdrawal has been approved and sent.\n\n"
            "💵 <b>Amount:</b> {amount} {currency}\n"
            "📬 <b>Address:</b> <code>{wallet}</code>\n"
            "🕐 <b>Date:</b> {date}\n"
            "🆔 <b>Withdrawal ID:</b> <code>{withdrawal_id}</code>\n\n"
            "Payment may take a few minutes to reflect. 🙌"
        ),
        'pt': (
            "💸 <b>Saque Processado!</b>\n\n"
            "✅ Seu saque foi aprovado e enviado.\n\n"
            "💵 <b>Valor:</b> {amount} {currency}\n"
            "📬 <b>Endereço:</b> <code>{wallet}</code>\n"
            "🕐 <b>Data:</b> {date}\n"
            "🆔 <b>ID saque:</b> <code>{withdrawal_id}</code>\n\n"
            "O pagamento pode levar alguns minutos. 🙌"
        ),
        'fr': (
            "💸 <b>Retrait Traité!</b>\n\n"
            "✅ Votre retrait a été approuvé et envoyé.\n\n"
            "💵 <b>Montant:</b> {amount} {currency}\n"
            "📬 <b>Adresse:</b> <code>{wallet}</code>\n"
            "🕐 <b>Date:</b> {date}\n"
            "🆔 <b>ID retrait:</b> <code>{withdrawal_id}</code>\n\n"
            "Le paiement peut prendre quelques minutes. 🙌"
        ),
    },

    # ── 4. RETIRO RECHAZADO ──────────────────────────────────────
    'withdrawal_rejected': {
        'es': (
            "❌ <b>Retiro Rechazado</b>\n\n"
            "Tu solicitud de retiro no pudo ser procesada.\n\n"
            "💵 <b>Monto:</b> {amount} {currency}\n"
            "🆔 <b>ID retiro:</b> <code>{withdrawal_id}</code>\n"
            "📋 <b>Motivo:</b> {reason}\n\n"
            "El monto ha sido devuelto a tu saldo. Si tienes preguntas, "
            "contacta al soporte. 🤝"
        ),
        'en': (
            "❌ <b>Withdrawal Rejected</b>\n\n"
            "Your withdrawal request could not be processed.\n\n"
            "💵 <b>Amount:</b> {amount} {currency}\n"
            "🆔 <b>Withdrawal ID:</b> <code>{withdrawal_id}</code>\n"
            "📋 <b>Reason:</b> {reason}\n\n"
            "The amount has been returned to your balance. "
            "Contact support if you have questions. 🤝"
        ),
        'pt': (
            "❌ <b>Saque Rejeitado</b>\n\n"
            "Sua solicitação de saque não pôde ser processada.\n\n"
            "💵 <b>Valor:</b> {amount} {currency}\n"
            "🆔 <b>ID saque:</b> <code>{withdrawal_id}</code>\n"
            "📋 <b>Motivo:</b> {reason}\n\n"
            "O valor foi devolvido ao seu saldo. "
            "Entre em contato com o suporte se tiver dúvidas. 🤝"
        ),
        'fr': (
            "❌ <b>Retrait Rejeté</b>\n\n"
            "Votre demande de retrait n'a pas pu être traitée.\n\n"
            "💵 <b>Montant:</b> {amount} {currency}\n"
            "🆔 <b>ID retrait:</b> <code>{withdrawal_id}</code>\n"
            "📋 <b>Motif:</b> {reason}\n\n"
            "Le montant a été restitué à votre solde. "
            "Contactez le support si vous avez des questions. 🤝"
        ),
    },

    # ── 5. PLAN ACTIVADO ─────────────────────────────────────────
    'plan_activated': {
        'es': (
            "⛏️ <b>¡Plan Activado!</b>\n\n"
            "🚀 Tu plan de minería ha sido activado exitosamente.\n\n"
            "📦 <b>Plan:</b> {plan_name}\n"
            "💰 <b>Ganancia/hora:</b> {ton_per_hour} TON\n"
            "📅 <b>Vence:</b> {expires}\n\n"
            "Tu equipo está minando automáticamente. ¡A ganar! 💎"
        ),
        'en': (
            "⛏️ <b>Plan Activated!</b>\n\n"
            "🚀 Your mining plan has been successfully activated.\n\n"
            "📦 <b>Plan:</b> {plan_name}\n"
            "💰 <b>Earnings/hour:</b> {ton_per_hour} TON\n"
            "📅 <b>Expires:</b> {expires}\n\n"
            "Your rig is mining automatically. Let's earn! 💎"
        ),
        'pt': (
            "⛏️ <b>Plano Ativado!</b>\n\n"
            "🚀 Seu plano de mineração foi ativado com sucesso.\n\n"
            "📦 <b>Plano:</b> {plan_name}\n"
            "💰 <b>Ganhos/hora:</b> {ton_per_hour} TON\n"
            "📅 <b>Expira:</b> {expires}\n\n"
            "Seu equipamento está minerando automaticamente. Vamos ganhar! 💎"
        ),
        'fr': (
            "⛏️ <b>Plan Activé!</b>\n\n"
            "🚀 Votre plan de minage a été activé avec succès.\n\n"
            "📦 <b>Plan:</b> {plan_name}\n"
            "💰 <b>Gains/heure:</b> {ton_per_hour} TON\n"
            "📅 <b>Expire:</b> {expires}\n\n"
            "Votre rig mine automatiquement. En avant! 💎"
        ),
    },

    # ── 6. REFERIDO VALIDADO (notificación al referidor) ─────────
    'referral_validated': {
        'es': (
            "🎉 <b>¡Nuevo Referido Validado!</b>\n\n"
            "👤 <b>Tu referido:</b> {referred_name}\n"
            "💎 <b>Recompensa recibida:</b> +{reward} S-E\n\n"
            "Tu amigo completó su primera tarea y activó un plan. "
            "¡Sigue invitando para ganar más! 🚀"
        ),
        'en': (
            "🎉 <b>New Validated Referral!</b>\n\n"
            "👤 <b>Your referral:</b> {referred_name}\n"
            "💎 <b>Reward received:</b> +{reward} S-E\n\n"
            "Your friend completed their first task and activated a plan. "
            "Keep inviting to earn more! 🚀"
        ),
        'pt': (
            "🎉 <b>Novo Indicado Validado!</b>\n\n"
            "👤 <b>Seu indicado:</b> {referred_name}\n"
            "💎 <b>Recompensa recebida:</b> +{reward} S-E\n\n"
            "Seu amigo completou a primeira tarefa e ativou um plano. "
            "Continue convidando para ganhar mais! 🚀"
        ),
        'fr': (
            "🎉 <b>Nouveau Filleul Validé!</b>\n\n"
            "👤 <b>Votre filleul:</b> {referred_name}\n"
            "💎 <b>Récompense reçue:</b> +{reward} S-E\n\n"
            "Votre ami a complété sa première tâche et activé un plan. "
            "Continuez à inviter pour gagner plus! 🚀"
        ),
    },

    # ── 7. MENSAJE GENÉRICO cuando el usuario escribe al bot ─────
    'generic_reply': {
        'es': (
            "👋 <b>¡Hola, {name}!</b>\n\n"
            "Usa el botón de abajo para acceder a la app SALLY-E y "
            "gestionar tu cuenta, minar tokens y retirar ganancias. 👇"
        ),
        'en': (
            "👋 <b>Hi, {name}!</b>\n\n"
            "Use the button below to open the SALLY-E app and "
            "manage your account, mine tokens and withdraw earnings. 👇"
        ),
        'pt': (
            "👋 <b>Olá, {name}!</b>\n\n"
            "Use o botão abaixo para acessar o app SALLY-E e "
            "gerenciar sua conta, minerar tokens e sacar ganhos. 👇"
        ),
        'fr': (
            "👋 <b>Bonjour, {name}!</b>\n\n"
            "Utilisez le bouton ci-dessous pour ouvrir l'app SALLY-E et "
            "gérer votre compte, miner des tokens et retirer vos gains. 👇"
        ),
    },
}

# Botones de apertura de la app según idioma
OPEN_APP_BUTTON = {
    'es': '🚀 Abrir SALLY-E',
    'en': '🚀 Open SALLY-E',
    'pt': '🚀 Abrir SALLY-E',
    'fr': '🚀 Ouvrir SALLY-E',
}


# ──────────────────────────────────────────────
#  UTILIDADES
# ──────────────────────────────────────────────

def _get_text(notif_type: str, lang: str, **kwargs) -> str:
    """Obtiene el texto de notificación localizado."""
    texts = NOTIF_TEXTS.get(notif_type, {})
    template = texts.get(lang) or texts.get('es') or texts.get('en', '')
    try:
        return template.format(**kwargs)
    except KeyError as e:
        logger.warning(f"Missing key {e} in notification '{notif_type}' lang='{lang}'")
        return template


def _make_app_keyboard(user_id: int, lang: str) -> dict:
    """Genera el inline keyboard con el botón de apertura de la app."""
    webapp_url = f"{WEBAPP_URL}?user_id={user_id}"
    btn_text = OPEN_APP_BUTTON.get(lang, '🚀 Open SALLY-E')
    return {
        "inline_keyboard": [[
            {"text": btn_text, "web_app": {"url": webapp_url}}
        ]]
    }


async def _send_telegram_message(chat_id: int, text: str, reply_markup: dict | None = None):
    """Envía mensaje vía Telegram Bot API usando aiohttp."""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN not set – cannot send notification")
        return False

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    if reply_markup:
        import json
        payload["reply_markup"] = json.dumps(reply_markup)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                data = await resp.json()
                if data.get('ok'):
                    return True
                else:
                    logger.warning(f"Telegram API error for chat {chat_id}: {data}")
                    return False
    except Exception as e:
        logger.error(f"Failed to send notification to {chat_id}: {e}")
        return False


def send_notification(chat_id: int, notif_type: str, lang: str = 'es', with_app_button: bool = True, **kwargs):
    """
    Función síncrona de conveniencia para enviar notificaciones desde Flask/app.py.
    Crea un event loop temporal si no hay uno activo.
    """
    text = _get_text(notif_type, lang, **kwargs)
    keyboard = _make_app_keyboard(int(chat_id), lang) if with_app_button else None

    async def _run():
        await _send_telegram_message(int(chat_id), text, keyboard)

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Si hay un loop activo (Quart / async Flask) usa create_task
            asyncio.ensure_future(_run())
        else:
            loop.run_until_complete(_run())
    except RuntimeError:
        # No hay loop — crear uno nuevo
        asyncio.run(_run())


# ──────────────────────────────────────────────
#  FUNCIONES PÚBLICAS por tipo de evento
# ──────────────────────────────────────────────

def notify_welcome(user_id: int, first_name: str, language_code: str = None):
    """Notificación de bienvenida al unirse al canal o al bot."""
    lang = detect_lang(language_code)
    send_notification(user_id, 'welcome', lang, name=first_name)


def notify_deposit(user_id: int, amount, currency: str, credited,
                   deposit_id: str, date: str, language_code: str = None):
    """Notificación de depósito confirmado."""
    lang = detect_lang(language_code)
    send_notification(
        user_id, 'deposit_confirmed', lang,
        amount=amount, currency=currency,
        credited=credited, deposit_id=deposit_id, date=date,
    )


def notify_withdrawal_approved(user_id: int, amount, currency: str, wallet: str,
                               withdrawal_id: str, date: str, language_code: str = None):
    """Notificación de retiro aprobado."""
    lang = detect_lang(language_code)
    send_notification(
        user_id, 'withdrawal_approved', lang,
        amount=amount, currency=currency,
        wallet=wallet, withdrawal_id=withdrawal_id, date=date,
    )


def notify_withdrawal_rejected(user_id: int, amount, currency: str,
                               withdrawal_id: str, reason: str = 'N/A',
                               language_code: str = None):
    """Notificación de retiro rechazado."""
    lang = detect_lang(language_code)
    send_notification(
        user_id, 'withdrawal_rejected', lang,
        amount=amount, currency=currency,
        withdrawal_id=withdrawal_id, reason=reason,
    )


def notify_plan_activated(user_id: int, plan_name: str, ton_per_hour,
                          expires: str, language_code: str = None):
    """Notificación de plan activado."""
    lang = detect_lang(language_code)
    send_notification(
        user_id, 'plan_activated', lang,
        plan_name=plan_name, ton_per_hour=ton_per_hour, expires=expires,
    )


def notify_referral_validated(referrer_id: int, referred_name: str,
                              reward, language_code: str = None):
    """Notificación al referidor cuando su referido valida."""
    lang = detect_lang(language_code)
    send_notification(
        referrer_id, 'referral_validated', lang,
        referred_name=referred_name, reward=reward,
    )


def notify_generic(user_id: int, first_name: str, language_code: str = None):
    """Respuesta automática cuando el usuario envía cualquier mensaje al bot."""
    lang = detect_lang(language_code)
    send_notification(user_id, 'generic_reply', lang, name=first_name)
