"""
notifications.py - Notificaciones privadas SALLY-E
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
  'es':"👋 <b>¡Bienvenido/a a {bot_title}, {name}!</b>\n\n🎉 Ya formas parte de nuestra comunidad.\n\n💰 Gana tokens minando automáticamente\n✅ Completa tareas y obtén recompensas\n👥 Invita amigos y gana comisiones\n💸 Retira en USDT, DOGE o TON\n\n👇 <b>Presiona el botón para abrir la app:</b>",
  'en':"👋 <b>Welcome to {bot_title}, {name}!</b>\n\n🎉 You are now part of our community.\n\n💰 Earn tokens by auto-mining\n✅ Complete tasks and get rewards\n👥 Invite friends and earn commissions\n💸 Withdraw in USDT, DOGE or TON\n\n👇 <b>Press the button to open the app:</b>",
  'pt':"👋 <b>Bem-vindo(a) ao {bot_title}, {name}!</b>\n\n🎉 Você agora faz parte da nossa comunidade.\n\n💰 Ganhe tokens com mineração automática\n✅ Complete tarefas e receba recompensas\n👥 Convide amigos e ganhe comissões\n💸 Saque em USDT, DOGE ou TON\n\n👇 <b>Pressione o botão para abrir o app:</b>",
  'fr':"👋 <b>Bienvenue sur {bot_title}, {name}!</b>\n\n🎉 Vous faites maintenant partie de notre communauté.\n\n💰 Gagnez des tokens par le minage automatique\n✅ Complétez des tâches et obtenez des récompenses\n👥 Invitez des amis et gagnez des commissions\n💸 Retirez en USDT, DOGE ou TON\n\n👇 <b>Appuyez sur le bouton pour ouvrir l'app:</b>",
},
'deposit_confirmed':{
  'es':"✅ <b>¡Depósito Confirmado!</b>\n\n💵 <b>Monto:</b> {amount} {currency}\n🪙 <b>Crédito recibido:</b> {credited} S-E\n🕐 <b>Fecha:</b> {date}\n🆔 <b>ID:</b> <code>{deposit_id}</code>\n\nTu saldo fue actualizado. ¡Sigue minando! ⛏️",
  'en':"✅ <b>Deposit Confirmed!</b>\n\n💵 <b>Amount:</b> {amount} {currency}\n🪙 <b>Credited:</b> {credited} S-E\n🕐 <b>Date:</b> {date}\n🆔 <b>ID:</b> <code>{deposit_id}</code>\n\nYour balance has been updated. Keep mining! ⛏️",
  'pt':"✅ <b>Depósito Confirmado!</b>\n\n💵 <b>Valor:</b> {amount} {currency}\n🪙 <b>Creditado:</b> {credited} S-E\n🕐 <b>Data:</b> {date}\n🆔 <b>ID:</b> <code>{deposit_id}</code>\n\nSeu saldo foi atualizado. Continue minerando! ⛏️",
  'fr':"✅ <b>Dépôt Confirmé!</b>\n\n💵 <b>Montant:</b> {amount} {currency}\n🪙 <b>Crédité:</b> {credited} S-E\n🕐 <b>Date:</b> {date}\n🆔 <b>ID:</b> <code>{deposit_id}</code>\n\nVotre solde a été mis à jour. Continuez à miner! ⛏️",
},
'withdrawal_approved':{
  'es':"💸 <b>¡Retiro Procesado!</b>\n\n✅ Tu retiro fue aprobado y enviado.\n\n💵 <b>Monto:</b> {amount} {currency}\n📬 <b>Dirección:</b> <code>{wallet}</code>\n🕐 <b>Fecha:</b> {date}\n🆔 <b>ID:</b> <code>{withdrawal_id}</code>\n\nEl pago puede tardar unos minutos. 🙌",
  'en':"💸 <b>Withdrawal Processed!</b>\n\n✅ Your withdrawal was approved and sent.\n\n💵 <b>Amount:</b> {amount} {currency}\n📬 <b>Address:</b> <code>{wallet}</code>\n🕐 <b>Date:</b> {date}\n🆔 <b>ID:</b> <code>{withdrawal_id}</code>\n\nPayment may take a few minutes. 🙌",
  'pt':"💸 <b>Saque Processado!</b>\n\n✅ Seu saque foi aprovado e enviado.\n\n💵 <b>Valor:</b> {amount} {currency}\n📬 <b>Endereço:</b> <code>{wallet}</code>\n🕐 <b>Data:</b> {date}\n🆔 <b>ID:</b> <code>{withdrawal_id}</code>\n\nO pagamento pode levar alguns minutos. 🙌",
  'fr':"💸 <b>Retrait Traité!</b>\n\n✅ Votre retrait a été approuvé et envoyé.\n\n💵 <b>Montant:</b> {amount} {currency}\n📬 <b>Adresse:</b> <code>{wallet}</code>\n🕐 <b>Date:</b> {date}\n🆔 <b>ID:</b> <code>{withdrawal_id}</code>\n\nLe paiement peut prendre quelques minutes. 🙌",
},
'withdrawal_rejected':{
  'es':"❌ <b>Retiro Rechazado</b>\n\n💵 <b>Monto:</b> {amount} {currency}\n🆔 <b>ID:</b> <code>{withdrawal_id}</code>\n📋 <b>Motivo:</b> {reason}\n\nEl monto fue devuelto a tu saldo. Contacta soporte si tienes dudas. 🤝",
  'en':"❌ <b>Withdrawal Rejected</b>\n\n💵 <b>Amount:</b> {amount} {currency}\n🆔 <b>ID:</b> <code>{withdrawal_id}</code>\n📋 <b>Reason:</b> {reason}\n\nThe amount was returned to your balance. Contact support if needed. 🤝",
  'pt':"❌ <b>Saque Rejeitado</b>\n\n💵 <b>Valor:</b> {amount} {currency}\n🆔 <b>ID:</b> <code>{withdrawal_id}</code>\n📋 <b>Motivo:</b> {reason}\n\nO valor foi devolvido ao seu saldo. Entre em contato com o suporte. 🤝",
  'fr':"❌ <b>Retrait Rejeté</b>\n\n💵 <b>Montant:</b> {amount} {currency}\n🆔 <b>ID:</b> <code>{withdrawal_id}</code>\n📋 <b>Motif:</b> {reason}\n\nLe montant a été restitué. Contactez le support si nécessaire. 🤝",
},
'plan_activated':{
  'es':"⛏️ <b>¡Plan Activado!</b>\n\n🚀 Tu plan de minería fue activado exitosamente.\n\n📦 <b>Plan:</b> {plan_name}\n💰 <b>Ganancia/hora:</b> {ton_per_hour} TON\n📅 <b>Vence:</b> {expires}\n\nTu equipo está minando automáticamente. ¡A ganar! 💎",
  'en':"⛏️ <b>Plan Activated!</b>\n\n🚀 Your mining plan was successfully activated.\n\n📦 <b>Plan:</b> {plan_name}\n💰 <b>Earnings/hour:</b> {ton_per_hour} TON\n📅 <b>Expires:</b> {expires}\n\nYour rig is mining automatically. Let's earn! 💎",
  'pt':"⛏️ <b>Plano Ativado!</b>\n\n🚀 Seu plano de mineração foi ativado com sucesso.\n\n📦 <b>Plano:</b> {plan_name}\n💰 <b>Ganhos/hora:</b> {ton_per_hour} TON\n📅 <b>Expira:</b> {expires}\n\nSeu equipamento está minerando automaticamente. Vamos ganhar! 💎",
  'fr':"⛏️ <b>Plan Activé!</b>\n\n🚀 Votre plan de minage a été activé avec succès.\n\n📦 <b>Plan:</b> {plan_name}\n💰 <b>Gains/heure:</b> {ton_per_hour} TON\n📅 <b>Expire:</b> {expires}\n\nVotre rig mine automatiquement. En avant! 💎",
},
'referral_validated':{
  'es':"🎉 <b>¡Referido Validado!</b>\n\n👤 <b>Tu referido:</b> {referred_name}\n💎 <b>Recompensa:</b> +{reward} S-E\n\n¡Tu amigo activó su primer plan! Sigue invitando para ganar más. 🚀",
  'en':"🎉 <b>Referral Validated!</b>\n\n👤 <b>Your referral:</b> {referred_name}\n💎 <b>Reward:</b> +{reward} S-E\n\nYour friend activated their first plan! Keep inviting to earn more. 🚀",
  'pt':"🎉 <b>Indicado Validado!</b>\n\n👤 <b>Seu indicado:</b> {referred_name}\n💎 <b>Recompensa:</b> +{reward} S-E\n\nSeu amigo ativou o primeiro plano! Continue convidando para ganhar mais. 🚀",
  'fr':"🎉 <b>Filleul Validé!</b>\n\n👤 <b>Votre filleul:</b> {referred_name}\n💎 <b>Récompense:</b> +{reward} S-E\n\nVotre ami a activé son premier plan! Continuez à inviter pour gagner plus. 🚀",
},
'generic_reply':{
  'es':"👋 <b>Hola, {name}!</b>\n\nUsa el botón de abajo para abrir la app SALLY-E y gestionar tu cuenta. 👇",
  'en':"👋 <b>Hi, {name}!</b>\n\nUse the button below to open the SALLY-E app and manage your account. 👇",
  'pt':"👋 <b>Olá, {name}!</b>\n\nUse o botão abaixo para acessar o app SALLY-E e gerenciar sua conta. 👇",
  'fr':"👋 <b>Bonjour, {name}!</b>\n\nUtilisez le bouton ci-dessous pour ouvrir l'app SALLY-E et gérer votre compte. 👇",
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

def notify_withdrawal_approved(user_id, amount, currency, wallet, withdrawal_id, date, language_code=None):
    _send(user_id,'withdrawal_approved',detect_lang(language_code),user_id=user_id,
          amount=amount,currency=currency,wallet=wallet,withdrawal_id=withdrawal_id,date=date)

def notify_withdrawal_rejected(user_id, amount, currency, withdrawal_id, reason='N/A', language_code=None):
    _send(user_id,'withdrawal_rejected',detect_lang(language_code),user_id=user_id,
          amount=amount,currency=currency,withdrawal_id=withdrawal_id,reason=reason)

def notify_plan_activated(user_id, plan_name, ton_per_hour, expires, language_code=None):
    _send(user_id,'plan_activated',detect_lang(language_code),user_id=user_id,
          plan_name=plan_name,ton_per_hour=ton_per_hour,expires=expires)

def notify_referral_validated(referrer_id, referred_name, reward, language_code=None):
    _send(referrer_id,'referral_validated',detect_lang(language_code),user_id=referrer_id,
          referred_name=referred_name,reward=reward)

def notify_generic(user_id, first_name, language_code=None):
    _send(user_id,'generic_reply',detect_lang(language_code),user_id=user_id,name=first_name)
