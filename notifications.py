"""
notifications.py - Notificaciones privadas Doge Pixel
Usa requests (síncrono) — compatible con Flask/Gunicorn sin asyncio.
Detecta idioma automáticamente por language_code de Telegram.
"""

import os, json, logging
import requests as _req

logger = logging.getLogger(__name__)

BOT_TOKEN    = os.environ.get('BOT_TOKEN', '')
WEBAPP_URL   = os.environ.get('WEBAPP_URL', '')
BOT_USERNAME = os.environ.get('BOT_USERNAME', 'SallyEbot')
_BOT_TITLE   = os.environ.get('BOT_TITLE', BOT_USERNAME)

# ──────────────────────────────────────────────────────────
# DETECCIÓN DE IDIOMA
# ──────────────────────────────────────────────────────────
_LANG_MAP = {
    'es':'es','es-419':'es','es-ar':'es','es-bo':'es','es-cl':'es','es-co':'es',
    'es-cr':'es','es-cu':'es','es-do':'es','es-ec':'es','es-sv':'es','es-gt':'es',
    'es-hn':'es','es-mx':'es','es-ni':'es','es-pa':'es','es-py':'es','es-pe':'es',
    'es-pr':'es','es-uy':'es','es-ve':'es',
    'pt':'pt','pt-br':'pt','pt-pt':'pt',
    'fr':'fr','fr-be':'fr','fr-ca':'fr','fr-ch':'fr',
    'en':'en','en-us':'en','en-gb':'en','en-au':'en',
}

def detect_lang(language_code):
    if not language_code: return 'es'
    lc = str(language_code).lower().strip()
    return _LANG_MAP.get(lc) or _LANG_MAP.get(lc[:2]) or 'en'

# ──────────────────────────────────────────────────────────
# TEXTOS
# ──────────────────────────────────────────────────────────
_TEXTS = {
'welcome':{
  'es':(
    "🎉 <b>¡{name}, bienvenido/a a {bot_title}!</b>\n\n"
    "Tu cuenta está lista. Empieza a ganar TON desde ahora mismo:\n\n"
    "⛏️ <b>Minería automática</b> — gana mientras duermes\n"
    "✅ <b>Tareas diarias</b> — recompensas extra cada día\n"
    "👥 <b>Programa de referidos</b> — comisiones por cada amigo\n"
    "💸 <b>Retiros reales</b> — en USDT, DOGE o TON\n\n"
    "👇 <b>Abre la app y activa tu primer plan:</b>"
  ),
  'en':(
    "🎉 <b>Welcome to {bot_title}, {name}!</b>\n\n"
    "Your account is ready. Start earning TON right now:\n\n"
    "⛏️ <b>Auto-mining</b> — earn while you sleep\n"
    "✅ <b>Daily tasks</b> — extra rewards every day\n"
    "👥 <b>Referral program</b> — commissions for every friend\n"
    "💸 <b>Real withdrawals</b> — in USDT, DOGE or TON\n\n"
    "👇 <b>Open the app and activate your first plan:</b>"
  ),
  'pt':(
    "🎉 <b>Bem-vindo(a) ao {bot_title}, {name}!</b>\n\n"
    "Sua conta está pronta. Comece a ganhar TON agora mesmo:\n\n"
    "⛏️ <b>Mineração automática</b> — ganhe enquanto dorme\n"
    "✅ <b>Tarefas diárias</b> — recompensas extras todo dia\n"
    "👥 <b>Programa de indicações</b> — comissões por cada amigo\n"
    "💸 <b>Saques reais</b> — em USDT, DOGE ou TON\n\n"
    "👇 <b>Abra o app e ative seu primeiro plano:</b>"
  ),
  'fr':(
    "🎉 <b>Bienvenue sur {bot_title}, {name}!</b>\n\n"
    "Votre compte est prêt. Commencez à gagner du TON dès maintenant:\n\n"
    "⛏️ <b>Minage automatique</b> — gagnez pendant que vous dormez\n"
    "✅ <b>Tâches quotidiennes</b> — récompenses supplémentaires chaque jour\n"
    "👥 <b>Programme de parrainage</b> — commissions pour chaque ami\n"
    "💸 <b>Retraits réels</b> — en USDT, DOGE ou TON\n\n"
    "👇 <b>Ouvrez l'app et activez votre premier plan:</b>"
  ),
},
'deposit_confirmed':{
  'es':(
    "✅ <b>¡Depósito confirmado!</b>\n\n"
    "💵 <b>Monto:</b> {amount} {currency}\n"
    "🪙 <b>TON acreditados:</b> {credited} TON\n"
    "🕐 <b>Fecha:</b> {date}\n"
    "🆔 <b>ID:</b> <code>{deposit_id}</code>\n\n"
    "Tu saldo ya está disponible. ¡Activa un plan y ponlo a trabajar! ⛏️"
  ),
  'en':(
    "✅ <b>Deposit Confirmed!</b>\n\n"
    "💵 <b>Amount:</b> {amount} {currency}\n"
    "🪙 <b>TON credited:</b> {credited} TON\n"
    "🕐 <b>Date:</b> {date}\n"
    "🆔 <b>ID:</b> <code>{deposit_id}</code>\n\n"
    "Your balance is ready to use. Activate a plan and put it to work! ⛏️"
  ),
  'pt':(
    "✅ <b>Depósito Confirmado!</b>\n\n"
    "💵 <b>Valor:</b> {amount} {currency}\n"
    "🪙 <b>TON creditados:</b> {credited} TON\n"
    "🕐 <b>Data:</b> {date}\n"
    "🆔 <b>ID:</b> <code>{deposit_id}</code>\n\n"
    "Seu saldo está disponível. Ative um plano e coloque-o para trabalhar! ⛏️"
  ),
  'fr':(
    "✅ <b>Dépôt Confirmé!</b>\n\n"
    "💵 <b>Montant:</b> {amount} {currency}\n"
    "🪙 <b>TON crédités:</b> {credited} TON\n"
    "🕐 <b>Date:</b> {date}\n"
    "🆔 <b>ID:</b> <code>{deposit_id}</code>\n\n"
    "Votre solde est prêt. Activez un plan et mettez-le au travail! ⛏️"
  ),
},
'withdrawal_approved':{
  'es':(
    "💸 <b>¡Retiro enviado con éxito!</b>\n\n"
    "💵 <b>Monto:</b> {amount} {currency}\n"
    "📬 <b>Wallet:</b> <code>{wallet}</code>\n"
    "🕐 <b>Fecha:</b> {date}\n"
    "🆔 <b>ID Retiro:</b> <code>{withdrawal_id}</code>\n"
    "🔗 <b>TX Hash:</b> <code>{tx_hash}</code>\n\n"
    "🔍 <a href=\"https://tonscan.org/tx/{tx_hash}\">Verificar en Tonscan</a>\n\n"
    "Tus TON están en camino. ¡Gracias por confiar en nosotros! 🚀"
  ),
  'en':(
    "💸 <b>Withdrawal Sent Successfully!</b>\n\n"
    "💵 <b>Amount:</b> {amount} {currency}\n"
    "📬 <b>Wallet:</b> <code>{wallet}</code>\n"
    "🕐 <b>Date:</b> {date}\n"
    "🆔 <b>Withdrawal ID:</b> <code>{withdrawal_id}</code>\n"
    "🔗 <b>TX Hash:</b> <code>{tx_hash}</code>\n\n"
    "🔍 <a href=\"https://tonscan.org/tx/{tx_hash}\">Verify on Tonscan</a>\n\n"
    "Your TON is on its way. Thank you for trusting us! 🚀"
  ),
  'pt':(
    "💸 <b>Saque Enviado com Sucesso!</b>\n\n"
    "💵 <b>Valor:</b> {amount} {currency}\n"
    "📬 <b>Carteira:</b> <code>{wallet}</code>\n"
    "🕐 <b>Data:</b> {date}\n"
    "🆔 <b>ID Saque:</b> <code>{withdrawal_id}</code>\n"
    "🔗 <b>TX Hash:</b> <code>{tx_hash}</code>\n\n"
    "🔍 <a href=\"https://tonscan.org/tx/{tx_hash}\">Verificar no Tonscan</a>\n\n"
    "Seu TON está a caminho. Obrigado por confiar em nós! 🚀"
  ),
  'fr':(
    "💸 <b>Retrait Envoyé avec Succès!</b>\n\n"
    "💵 <b>Montant:</b> {amount} {currency}\n"
    "📬 <b>Portefeuille:</b> <code>{wallet}</code>\n"
    "🕐 <b>Date:</b> {date}\n"
    "🆔 <b>ID Retrait:</b> <code>{withdrawal_id}</code>\n"
    "🔗 <b>TX Hash:</b> <code>{tx_hash}</code>\n\n"
    "🔍 <a href=\"https://tonscan.org/tx/{tx_hash}\">Vérifier sur Tonscan</a>\n\n"
    "Votre TON est en route. Merci de votre confiance! 🚀"
  ),
},
'withdrawal_rejected':{
  'es':(
    "⚠️ <b>Retiro no procesado</b>\n\n"
    "💵 <b>Monto:</b> {amount} {currency}\n"
    "🆔 <b>ID:</b> <code>{withdrawal_id}</code>\n"
    "📋 <b>Motivo:</b> {reason}\n\n"
    "No te preocupes — el importe fue devuelto a tu saldo de inmediato.\n"
    "Si tienes dudas, contacta a soporte desde la app. 🤝"
  ),
  'en':(
    "⚠️ <b>Withdrawal Not Processed</b>\n\n"
    "💵 <b>Amount:</b> {amount} {currency}\n"
    "🆔 <b>ID:</b> <code>{withdrawal_id}</code>\n"
    "📋 <b>Reason:</b> {reason}\n\n"
    "Don't worry — the amount was instantly returned to your balance.\n"
    "If you have questions, reach out to support from the app. 🤝"
  ),
  'pt':(
    "⚠️ <b>Saque Não Processado</b>\n\n"
    "💵 <b>Valor:</b> {amount} {currency}\n"
    "🆔 <b>ID:</b> <code>{withdrawal_id}</code>\n"
    "📋 <b>Motivo:</b> {reason}\n\n"
    "Não se preocupe — o valor foi devolvido ao seu saldo imediatamente.\n"
    "Se tiver dúvidas, entre em contato com o suporte pelo app. 🤝"
  ),
  'fr':(
    "⚠️ <b>Retrait Non Traité</b>\n\n"
    "💵 <b>Montant:</b> {amount} {currency}\n"
    "🆔 <b>ID:</b> <code>{withdrawal_id}</code>\n"
    "📋 <b>Motif:</b> {reason}\n\n"
    "Pas d'inquiétude — le montant a été restitué immédiatement sur votre solde.\n"
    "Pour toute question, contactez le support depuis l'app. 🤝"
  ),
},
'plan_activated':{
  'es':(
    "⛏️ <b>¡Plan activado! Tu minería ya está corriendo.</b>\n\n"
    "📦 <b>Plan:</b> {plan_name}\n"
    "💰 <b>Ganancia/hora:</b> {ton_per_hour} TON\n"
    "📅 <b>Activo hasta:</b> {expires}\n\n"
    "Cada hora que pasa, tu saldo crece automáticamente.\n"
    "¡Invita amigos para multiplicar tus ganancias! 💎"
  ),
  'en':(
    "⛏️ <b>Plan Activated! Your mining is now running.</b>\n\n"
    "📦 <b>Plan:</b> {plan_name}\n"
    "💰 <b>Earnings/hour:</b> {ton_per_hour} TON\n"
    "📅 <b>Active until:</b> {expires}\n\n"
    "Every hour that passes, your balance grows automatically.\n"
    "Invite friends to multiply your earnings! 💎"
  ),
  'pt':(
    "⛏️ <b>Plano Ativado! Sua mineração já está rodando.</b>\n\n"
    "📦 <b>Plano:</b> {plan_name}\n"
    "💰 <b>Ganhos/hora:</b> {ton_per_hour} TON\n"
    "📅 <b>Ativo até:</b> {expires}\n\n"
    "A cada hora que passa, seu saldo cresce automaticamente.\n"
    "Convide amigos para multiplicar seus ganhos! 💎"
  ),
  'fr':(
    "⛏️ <b>Plan Activé! Votre minage est en cours.</b>\n\n"
    "📦 <b>Plan:</b> {plan_name}\n"
    "💰 <b>Gains/heure:</b> {ton_per_hour} TON\n"
    "📅 <b>Actif jusqu'au:</b> {expires}\n\n"
    "Chaque heure qui passe, votre solde grandit automatiquement.\n"
    "Invitez des amis pour multiplier vos gains! 💎"
  ),
},
'referral_validated':{
  'es':(
    "🎉 <b>¡Comisión recibida!</b>\n\n"
    "👤 <b>Referido:</b> {referred_name}\n"
    "💎 <b>Bono ganado:</b> +{reward} TON\n"
    "👥 <b>Total referidos activos:</b> {total_refs}\n"
    "💰 <b>Total ganado por referidos:</b> {total_earnings} TON\n\n"
    "Tu amigo acaba de activar su primer plan. ¡Sigue creciendo tu red y tus ingresos! 🚀"
  ),
  'en':(
    "🎉 <b>Commission Received!</b>\n\n"
    "👤 <b>Referral:</b> {referred_name}\n"
    "💎 <b>Bonus earned:</b> +{reward} TON\n"
    "👥 <b>Total active referrals:</b> {total_refs}\n"
    "💰 <b>Total referral earnings:</b> {total_earnings} TON\n\n"
    "Your friend just activated their first plan. Keep growing your network and your income! 🚀"
  ),
  'pt':(
    "🎉 <b>Comissão Recebida!</b>\n\n"
    "👤 <b>Indicado:</b> {referred_name}\n"
    "💎 <b>Bônus ganho:</b> +{reward} TON\n"
    "👥 <b>Total de indicados ativos:</b> {total_refs}\n"
    "💰 <b>Total ganho por indicações:</b> {total_earnings} TON\n\n"
    "Seu amigo acabou de ativar o primeiro plano. Continue expandindo sua rede e seus ganhos! 🚀"
  ),
  'fr':(
    "🎉 <b>Commission Reçue!</b>\n\n"
    "👤 <b>Filleul:</b> {referred_name}\n"
    "💎 <b>Bonus gagné:</b> +{reward} TON\n"
    "👥 <b>Total filleuls actifs:</b> {total_refs}\n"
    "💰 <b>Total gains par parrainages:</b> {total_earnings} TON\n\n"
    "Votre ami vient d'activer son premier plan. Continuez à développer votre réseau et vos revenus! 🚀"
  ),
},
'generic_reply':{
  'es':(
    "👋 <b>¡Hola, {name}!</b>\n\n"
    "Para ver tu saldo, activar planes o retirar ganancias,\n"
    "abre la app desde el botón de abajo. 👇"
  ),
  'en':(
    "👋 <b>Hey, {name}!</b>\n\n"
    "To check your balance, activate plans, or withdraw earnings,\n"
    "open the app using the button below. 👇"
  ),
  'pt':(
    "👋 <b>Olá, {name}!</b>\n\n"
    "Para ver seu saldo, ativar planos ou sacar seus ganhos,\n"
    "abra o app pelo botão abaixo. 👇"
  ),
  'fr':(
    "👋 <b>Salut, {name}!</b>\n\n"
    "Pour voir votre solde, activer des plans ou retirer vos gains,\n"
    "ouvrez l'app via le bouton ci-dessous. 👇"
  ),
},
}

def _get_open_btn(lang):
    labels = {'es': f'🚀 Abrir {_BOT_TITLE}', 'en': f'🚀 Open {_BOT_TITLE}',
              'pt': f'🚀 Abrir {_BOT_TITLE}', 'fr': f'🚀 Ouvrir {_BOT_TITLE}'}
    return labels.get(lang, f'🚀 Open {_BOT_TITLE}')

# ──────────────────────────────────────────────────────────
# ENVÍO VÍA BOT API (síncrono, solo requests)
# ──────────────────────────────────────────────────────────

def _api(method, payload):
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN no configurado")
        return None
    try:
        r = _req.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/{method}",
            json=payload, timeout=10
        )
        data = r.json()
        if not data.get('ok'):
            logger.warning(f"Telegram [{method}] -> {data}")
        return data
    except Exception as e:
        logger.error(f"Error en Telegram API {method}: {e}")
        return None


def _keyboard(user_id, lang):
    if not WEBAPP_URL:
        return None
    url = f"{WEBAPP_URL.rstrip('/')}?user_id={user_id}"
    return {"inline_keyboard":[[{"text": _get_open_btn(lang), "web_app":{"url": url}}]]}


def _send(chat_id, notif_type, lang, user_id=None, **kwargs):
    texts = _TEXTS.get(notif_type, {})
    tmpl  = texts.get(lang) or texts.get('es') or texts.get('en','')
    # Always inject bot_title so templates can use {bot_title}
    kwargs.setdefault('bot_title', _BOT_TITLE)
    try:
        text = tmpl.format(**kwargs)
    except KeyError as e:
        logger.warning(f"Clave faltante {e} en notif '{notif_type}'")
        text = tmpl
    uid = user_id or chat_id
    kb = _keyboard(uid, lang)
    payload = {
        "chat_id": int(chat_id),
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    if kb:
        payload["reply_markup"] = json.dumps(kb)
    _api("sendMessage", payload)

# ──────────────────────────────────────────────────────────
# API PÚBLICA
# ──────────────────────────────────────────────────────────

def notify_welcome(user_id, first_name, language_code=None):
    _send(user_id,'welcome',detect_lang(language_code),user_id=user_id,name=first_name)

def notify_deposit(user_id, amount, currency, credited, deposit_id, date, language_code=None):
    _send(user_id,'deposit_confirmed',detect_lang(language_code),user_id=user_id,
          amount=amount,currency=currency,credited=credited,deposit_id=deposit_id,date=date)

def notify_withdrawal_approved(user_id, amount, currency, wallet, withdrawal_id, date, tx_hash='', language_code=None):
    _send(user_id,'withdrawal_approved',detect_lang(language_code),user_id=user_id,
          amount=amount,currency=currency,wallet=wallet,withdrawal_id=withdrawal_id,date=date,tx_hash=tx_hash or '—')

def notify_withdrawal_rejected(user_id, amount, currency, withdrawal_id, reason='N/A', language_code=None):
    _send(user_id,'withdrawal_rejected',detect_lang(language_code),user_id=user_id,
          amount=amount,currency=currency,withdrawal_id=withdrawal_id,reason=reason)

def notify_plan_activated(user_id, plan_name, ton_per_hour, expires, language_code=None):
    _send(user_id,'plan_activated',detect_lang(language_code),user_id=user_id,
          plan_name=plan_name,ton_per_hour=ton_per_hour,expires=expires)

def notify_referral_validated(referrer_id, referred_name, reward, total_refs=0, total_earnings=0, language_code=None):
    _send(referrer_id,'referral_validated',detect_lang(language_code),user_id=referrer_id,
          referred_name=referred_name,reward=reward,total_refs=total_refs,total_earnings=total_earnings)

def notify_generic(user_id, first_name, language_code=None):
    _send(user_id,'generic_reply',detect_lang(language_code),user_id=user_id,name=first_name)
