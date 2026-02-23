"""
main.py - Bot de Telegram para SALLY-E
Maneja comandos, callbacks y WebApp
FIXED VERSION - HTML formatting to avoid parse errors + Multi-channel verification
"""

import os
import re
import logging
import html
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

# Load environment
load_dotenv()

# Configuration
BOT_TOKEN = os.environ.get('BOT_TOKEN', '')
WEBAPP_URL = os.environ.get('WEBAPP_URL', 'https://M22.pythonanywhere.com')
BOT_USERNAME = os.environ.get('BOT_USERNAME', 'SallyEbot')
SUPPORT_GROUP = os.environ.get('SUPPORT_GROUP', 'https://t.me/Soporte_Sally')

# Official channels - comma separated list
OFFICIAL_CHANNELS_STR = os.environ.get('OFFICIAL_CHANNELS', '@SallyE_Comunity')
# Also check single channel config for backwards compatibility
if not OFFICIAL_CHANNELS_STR or OFFICIAL_CHANNELS_STR == '@SallyE_Comunity':
    single_channel = os.environ.get('OFFICIAL_CHANNEL', '@SallyE_Comunity')
    OFFICIAL_CHANNELS_STR = single_channel

# Parse channels into list
OFFICIAL_CHANNELS = [ch.strip() for ch in OFFICIAL_CHANNELS_STR.split(',') if ch.strip()]

# Admin IDs
ADMIN_IDS = os.environ.get('ADMIN_IDS', '5515244003').split(',')

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Import database (try/except for standalone testing)
try:
    from database import (
        get_user, create_user, update_user,
        add_referral, get_referrals, get_validated_referrals_count,
        increment_stat, get_stats
    )
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    logger.warning("Database module not available")

# Import notification helpers
try:
    from notifications import detect_lang, notify_welcome, notify_generic
    NOTIF_AVAILABLE = True
except ImportError:
    NOTIF_AVAILABLE = False
    logger.warning("Notifications module not available")


def escape_html(text):
    """
    Escapes special HTML characters to prevent parsing errors.
    This is CRITICAL for avoiding "Can't parse entities" errors.
    """
    if text is None:
        return ""
    return html.escape(str(text))


def safe_format_message(template, **kwargs):
    """
    Safely formats a message template by escaping all values.
    Returns a message safe for HTML parsing.
    """
    escaped_kwargs = {k: escape_html(v) for k, v in kwargs.items()}
    try:
        return template.format(**escaped_kwargs)
    except Exception as e:
        logger.error(f"Error formatting message: {e}")
        # Return a safe fallback
        return escape_html(str(template))


async def check_channel_membership(user_id: int, channel: str, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Verifica si el usuario es miembro de un canal de Telegram.
    Returns True if member, False otherwise.
    """
    try:
        # Clean channel name
        clean_channel = channel.strip()
        if not clean_channel.startswith('@'):
            clean_channel = f"@{clean_channel}"

        logger.info(f"Checking membership: user {user_id} in channel {clean_channel}")

        member = await context.bot.get_chat_member(clean_channel, user_id)
        is_member = member.status in ['member', 'administrator', 'creator']

        logger.info(f"User {user_id} membership in {clean_channel}: {member.status} -> {is_member}")
        return is_member

    except Exception as e:
        logger.error(f"Error checking channel membership for {user_id} in {channel}: {e}")
        # On error, be permissive to not block users due to API issues
        return True


async def check_all_channels_membership(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> tuple:
    """
    Verifica si el usuario es miembro de TODOS los canales oficiales.
    Returns (is_member_all, list_of_missing_channels)
    """
    missing_channels = []

    for channel in OFFICIAL_CHANNELS:
        if not channel:
            continue

        is_member = await check_channel_membership(user_id, channel, context)
        if not is_member:
            missing_channels.append(channel)

    return (len(missing_channels) == 0, missing_channels)


def get_main_menu_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Genera el teclado del menú principal con WebApp"""
    webapp_url = f"{WEBAPP_URL}?user_id={user_id}"

    # Get first channel for display
    first_channel = OFFICIAL_CHANNELS[0] if OFFICIAL_CHANNELS else 'SallyE_Comunity'
    channel_clean = first_channel.replace('@', '')

    keyboard = [
        [InlineKeyboardButton(
            "🚀 Abrir SALLY-E",
            web_app=WebAppInfo(url=webapp_url)
        )],
        [
            InlineKeyboardButton("👥 Mis Referidos", callback_data="my_referrals"),
            InlineKeyboardButton("📤 Compartir", callback_data="share_referral")
        ],
        [
            InlineKeyboardButton("📢 Canal Oficial", url=f"https://t.me/{channel_clean}"),
            InlineKeyboardButton("💬 Soporte", url=SUPPORT_GROUP)
        ]
    ]

    return InlineKeyboardMarkup(keyboard)


def get_channel_join_keyboard(missing_channels: list) -> InlineKeyboardMarkup:
    """Genera el teclado para unirse a los canales faltantes"""
    keyboard = []

    # Add a button for each missing channel
    for channel in missing_channels[:5]:  # Limit to 5 to avoid telegram limits
        channel_clean = channel.replace('@', '')
        keyboard.append([
            InlineKeyboardButton(f"📢 Unirse a {channel}", url=f"https://t.me/{channel_clean}")
        ])

    # Add verify button
    keyboard.append([
        InlineKeyboardButton("✅ Ya me uní a todos", callback_data="verify_channels")
    ])

    return InlineKeyboardMarkup(keyboard)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start - punto de entrada principal"""
    user = update.effective_user
    user_id = user.id
    username = user.username or ""
    first_name = user.first_name or "Usuario"

    # Escape user data to prevent HTML parsing errors
    safe_first_name = escape_html(first_name)

    # Extract referrer from args (format: ref_USERID)
    referrer_id = None
    if context.args and len(context.args) > 0:
        arg = context.args[0]
        if arg.startswith('ref_'):
            try:
                potential_referrer = arg.replace('ref_', '')
                # Don't let users refer themselves
                if str(potential_referrer) != str(user_id):
                    referrer_id = potential_referrer
            except:
                pass

    # Create or update user in database
    if DB_AVAILABLE:
        existing_user = get_user(user_id)
        is_new_user = existing_user is None
        if existing_user:
            update_user(user_id, username=username, first_name=first_name)
        else:
            # New user - create with pending referrer
            create_user(user_id, username=username, first_name=first_name, referrer_id=referrer_id)

        # Increment stats
        increment_stat('total_starts')
    else:
        is_new_user = False

    # Check ALL channels membership
    is_member_all, missing_channels = await check_all_channels_membership(user_id, context)

    # Detect user language
    language_code = user.language_code if hasattr(user, 'language_code') else None
    lang = detect_lang(language_code) if NOTIF_AVAILABLE else 'es'

    if not is_member_all:
        # Build list of channels for the message
        channels_list = '\n'.join([f"📢 {ch}" for ch in missing_channels])

        # Use HTML formatting - MUCH more reliable than Markdown
        welcome_text = (
            f"👋 <b>Hola {safe_first_name}!</b>\n\n"
            f"🌟 Bienvenido a <b>SALLY-E Bot</b>\n\n"
            f"Para acceder a todas las funciones, debes unirte a nuestros canales oficiales:\n\n"
            f"{channels_list}\n\n"
            f"Una vez que te unas a todos, presiona el botón <b>Ya me uní a todos</b> para continuar."
        )

        try:
            await update.message.reply_text(
                welcome_text,
                parse_mode=ParseMode.HTML,
                reply_markup=get_channel_join_keyboard(missing_channels)
            )
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            # Fallback without formatting
            await update.message.reply_text(
                f"Hola {first_name}! Bienvenido a SALLY-E Bot. "
                f"Debes unirte a los canales oficiales para continuar.",
                reply_markup=get_channel_join_keyboard(missing_channels)
            )
        return

    # Show main menu - Use HTML formatting
    welcome_text = (
        f"👋 <b>Hola {safe_first_name}!</b>\n\n"
        f"🌟 Bienvenido a <b>SALLY-E Bot</b>\n\n"
        f"💰 Gana tokens minando\n"
        f"✅ Completa tareas para obtener recompensas\n"
        f"👥 Invita amigos y gana comisiones\n"
        f"💸 Retira tus ganancias en USDT o DOGE\n\n"
        f"Presiona el botón de abajo para comenzar:"
    )

    try:
        await update.message.reply_text(
            welcome_text,
            parse_mode=ParseMode.HTML,
            reply_markup=get_main_menu_keyboard(user_id)
        )
    except Exception as e:
        logger.error(f"Error sending welcome message: {e}")
        # Fallback without formatting
        await update.message.reply_text(
            f"Hola {first_name}! Bienvenido a SALLY-E Bot. "
            f"Gana tokens minando, completa tareas y retira en USDT o DOGE.",
            reply_markup=get_main_menu_keyboard(user_id)
        )


async def verify_channels_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback para verificar membresía en todos los canales"""
    query = update.callback_query
    await query.answer()

    user = query.from_user
    user_id = user.id
    safe_first_name = escape_html(user.first_name or "Usuario")

    is_member_all, missing_channels = await check_all_channels_membership(user_id, context)

    if not is_member_all:
        channels_list = ', '.join(missing_channels)
        await query.answer(
            f"❌ Aún no te has unido a: {channels_list}",
            show_alert=True
        )
        return

    # Send private welcome notification
    if NOTIF_AVAILABLE:
        language_code = user.language_code if hasattr(user, 'language_code') else None
        notify_welcome(user_id, user.first_name or 'Usuario', language_code)

    # Show main menu
    welcome_text = (
        f"✅ <b>Verificación exitosa!</b>\n\n"
        f"🌟 Ya puedes acceder a <b>SALLY-E Bot</b>\n\n"
        f"💰 Gana tokens minando\n"
        f"✅ Completa tareas para obtener recompensas\n"
        f"👥 Invita amigos y gana comisiones\n"
        f"💸 Retira tus ganancias en USDT o DOGE\n\n"
        f"Presiona el botón de abajo para comenzar:"
    )

    try:
        await query.edit_message_text(
            welcome_text,
            parse_mode=ParseMode.HTML,
            reply_markup=get_main_menu_keyboard(user_id)
        )
    except Exception as e:
        logger.error(f"Error editing message: {e}")
        await query.edit_message_text(
            "Verificación exitosa! Ya puedes acceder a SALLY-E Bot.",
            reply_markup=get_main_menu_keyboard(user_id)
        )


async def my_referrals_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback para mostrar referidos"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    if not DB_AVAILABLE:
        await query.answer("Base de datos no disponible", show_alert=True)
        return

    referrals = get_referrals(user_id)

    # Count validated referrals
    validated_count = sum(1 for ref in referrals if ref.get('validated'))
    pending_count = len(referrals) - validated_count

    if not referrals:
        text = (
            "👥 <b>Mis Referidos</b>\n\n"
            "Aún no tienes referidos.\n\n"
            "💡 Comparte tu link de referido para invitar amigos.\n\n"
            "⚠️ <i>Recuerda: Solo recibirás recompensa cuando tu referido complete su primera tarea.</i>"
        )
    else:
        text = f"👥 <b>Mis Referidos</b>\n\n"
        text += f"✅ Validados: {validated_count}\n"
        text += f"⏳ Pendientes: {pending_count}\n"
        text += f"📊 Total: {len(referrals)}\n\n"

        for i, ref in enumerate(referrals[:10], 1):
            # Escape username/name to prevent HTML errors
            name = ref.get('first_name') or ref.get('username') or str(ref.get('referred_id', 'Usuario'))
            safe_name = escape_html(name)
            status = "✅" if ref.get('validated') else "⏳"
            text += f"{i}. {safe_name} {status}\n"

        if len(referrals) > 10:
            text += f"\n... y {len(referrals) - 10} más"

        text += "\n\n✅ = Validado (completó tarea)\n⏳ = Pendiente"

    keyboard = [[InlineKeyboardButton("⬅️ Volver", callback_data="start")]]

    try:
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"Error showing referrals: {e}")
        await query.edit_message_text(
            f"Tienes {len(referrals)} referidos. {validated_count} validados.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


async def share_referral_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback para compartir link de referido"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    referral_link = f"https://t.me/{BOT_USERNAME}?start=ref_{user_id}"

    text = (
        "📤 <b>Comparte tu Link de Referido</b>\n\n"
        f"🔗 Tu link personal:\n<code>{referral_link}</code>\n\n"
        "💰 Gana <b>1 S-E</b> por cada amigo que invite y complete al menos una tarea.\n\n"
        "📊 Además, recibes <b>5% de comisión</b> de todo lo que tus referidos minen.\n\n"
        "⚠️ <i>Nota: La recompensa se activa cuando tu referido completa su primera tarea.</i>"
    )

    keyboard = [
        [InlineKeyboardButton("📤 Compartir Link",
                            switch_inline_query=f"Únete a SALLY-E y gana tokens! {referral_link}")],
        [InlineKeyboardButton("⬅️ Volver", callback_data="start")]
    ]

    try:
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"Error sharing referral: {e}")
        await query.edit_message_text(
            f"Tu link de referido: {referral_link}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


async def start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback para volver al menú principal"""
    query = update.callback_query
    await query.answer()

    user = query.from_user
    user_id = user.id
    safe_first_name = escape_html(user.first_name or "Usuario")

    welcome_text = (
        f"👋 <b>Hola {safe_first_name}!</b>\n\n"
        f"🌟 Bienvenido a <b>SALLY-E Bot</b>\n\n"
        f"💰 Gana tokens minando\n"
        f"✅ Completa tareas para obtener recompensas\n"
        f"👥 Invita amigos y gana comisiones\n"
        f"💸 Retira tus ganancias en USDT o DOGE\n\n"
        f"Presiona el botón de abajo para comenzar:"
    )

    try:
        await query.edit_message_text(
            welcome_text,
            parse_mode=ParseMode.HTML,
            reply_markup=get_main_menu_keyboard(user_id)
        )
    except Exception as e:
        logger.error(f"Error in start callback: {e}")
        await query.edit_message_text(
            f"Hola! Bienvenido a SALLY-E Bot.",
            reply_markup=get_main_menu_keyboard(user_id)
        )


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /stats - solo para admins"""
    user_id = str(update.effective_user.id)

    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ No tienes permiso para usar este comando.")
        return

    if not DB_AVAILABLE:
        await update.message.reply_text("❌ Base de datos no disponible.")
        return

    stats = get_stats()

    text = (
        "📊 <b>Estadísticas del Bot</b>\n\n"
        f"👥 Total de inicios: {stats.get('total_starts', 0)}\n"
        f"🔗 Total de referidos: {stats.get('total_referrals', 0)}\n"
        f"✅ Referidos validados: {stats.get('validated_referrals', 0)}\n"
        f"📋 Tareas completadas: {stats.get('total_tasks_completed', 0)}\n"
        f"💸 Retiros procesados: {stats.get('total_withdrawals', 0)}\n"
    )

    try:
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error(f"Error sending stats: {e}")
        await update.message.reply_text(str(stats))


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /help"""
    # Build channels list
    channels_text = ', '.join(OFFICIAL_CHANNELS) if OFFICIAL_CHANNELS else "@SallyE_Comunity"

    text = (
        "ℹ️ <b>Ayuda de SALLY-E Bot</b>\n\n"
        "<b>Comandos disponibles:</b>\n"
        "/start - Iniciar el bot\n"
        "/help - Ver esta ayuda\n\n"
        "<b>¿Cómo funciona?</b>\n"
        "1️⃣ Abre la aplicación con el botón\n"
        "2️⃣ Mina tokens automáticamente\n"
        "3️⃣ Completa tareas para ganar más\n"
        "4️⃣ Invita amigos y gana comisiones\n"
        "5️⃣ Retira en USDT o DOGE\n\n"
        "<b>Sistema de Referidos:</b>\n"
        "• Comparte tu link de referido\n"
        "• Recibes 1 S-E cuando tu referido complete su primera tarea\n"
        "• Ganas 5% de comisión del minado de tus referidos\n\n"
        f"📢 Canales: {escape_html(channels_text)}\n"
        f"💬 Soporte: {escape_html(SUPPORT_GROUP)}"
    )

    try:
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error(f"Error sending help: {e}")
        await update.message.reply_text(
            "Comandos: /start /help\n"
            "Mina tokens, completa tareas e invita amigos para ganar."
        )


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja errores de forma segura"""
    error_msg = str(context.error)

    # Log the error
    logger.error(f"Error in update {update}: {error_msg}")

    # Check if it's a parse error and log specifically
    if "parse entities" in error_msg.lower() or "can't find end" in error_msg.lower():
        logger.error(f"PARSE ERROR - This is a formatting issue: {error_msg}")

    # Try to notify user if possible
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "⚠️ Ocurrió un error. Por favor intenta de nuevo."
            )
    except:
        pass


async def generic_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Responde a CUALQUIER mensaje de texto que el usuario envíe al bot.
    Siempre devuelve el menú principal con botón de apertura de la app,
    en el idioma detectado automáticamente.
    """
    user = update.effective_user
    if not user:
        return

    user_id = user.id
    first_name = user.first_name or 'Usuario'
    safe_first_name = escape_html(first_name)
    language_code = user.language_code if hasattr(user, 'language_code') else None

    # Send localized generic reply via notifications module
    if NOTIF_AVAILABLE:
        notify_generic(user_id, first_name, language_code)
    else:
        # Fallback: direct reply in Spanish
        welcome_text = (
            f"👋 <b>Hola {safe_first_name}!</b>\n\n"
            "Usa el botón de abajo para acceder a SALLY-E. 👇"
        )
        try:
            await update.message.reply_text(
                welcome_text,
                parse_mode=ParseMode.HTML,
                reply_markup=get_main_menu_keyboard(user_id)
            )
        except Exception as e:
            logger.error(f"Error in generic handler: {e}")


def main():
    """Función principal"""
    if not BOT_TOKEN:
        print("Error: BOT_TOKEN not configured")
        print("Please set BOT_TOKEN in .env file")
        return

    # Create application
    application = Application.builder().token(BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("stats", stats_command))

    # Callback handlers
    application.add_handler(CallbackQueryHandler(verify_channels_callback, pattern="^verify_channels?$"))
    application.add_handler(CallbackQueryHandler(my_referrals_callback, pattern="^my_referrals$"))
    application.add_handler(CallbackQueryHandler(share_referral_callback, pattern="^share_referral$"))
    application.add_handler(CallbackQueryHandler(start_callback, pattern="^start$"))

    # Error handler
    application.add_error_handler(error_handler)

    # Generic message handler — responds to any text message
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, generic_message_handler))

    # Start bot
    print("🤖 SALLY-E Bot starting...")
    print(f"📢 Channels: {OFFICIAL_CHANNELS}")
    print(f"🌐 WebApp: {WEBAPP_URL}")

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
