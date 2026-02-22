"""
ton_wallet.py — WalletV4R2 via tonutils
Soporta: Toncenter (con API key) y TON API (sin key)
"""
import asyncio
import logging
import requests
import time

logger = logging.getLogger(__name__)


def send_ton(mnemonic, to_addr, ton_amount, memo='', api_key='',
             bot_wallet_address=''):
    """Envía TON via WalletV4R2. Retorna (success, tx_hash, error)."""
    try:
        if isinstance(mnemonic, str):
            words = mnemonic.strip().split()
        else:
            words = list(mnemonic)
        if len(words) != 24:
            return False, None, f'Mnemonic necesita 24 palabras (tiene {len(words)})'

        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                raise RuntimeError
            return loop.run_until_complete(_send(words, to_addr, float(ton_amount), memo, api_key))
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(_send(words, to_addr, float(ton_amount), memo, api_key))
            finally:
                loop.close()
    except Exception as e:
        logger.exception(f'send_ton: {e}')
        return False, None, str(e)


async def _send(words, to_addr, ton_amount, memo, api_key):
    from tonutils.wallet import WalletV4R2

    # ── Intentar con Toncenter (requiere API key para sendBoc) ──────────
    if api_key:
        try:
            from tonutils.client import ToncenterV2Client
            client = ToncenterV2Client(api_key=api_key, is_testnet=False)
            wallet, _, _, _ = WalletV4R2.from_mnemonic(client, words)
            logger.info(f'Wallet lista (Toncenter). Enviando {ton_amount} TON -> {to_addr}')
            tx = await wallet.transfer(destination=to_addr, amount=ton_amount,
                                       body=memo or None)
            logger.info(f'SUCCESS via Toncenter: {tx}')
            return True, str(tx), None
        except Exception as e:
            logger.warning(f'Toncenter fallo: {e}. Intentando TON API...')

    # ── Fallback: tonapi.io (funciona sin API key) ───────────────────────
    try:
        from tonutils.client import TonapiClient
        client = TonapiClient(api_key='', is_testnet=False)
        wallet, _, _, _ = WalletV4R2.from_mnemonic(client, words)
        logger.info(f'Wallet lista (TON API). Enviando {ton_amount} TON -> {to_addr}')
        tx = await wallet.transfer(destination=to_addr, amount=ton_amount,
                                   body=memo or None)
        logger.info(f'SUCCESS via TON API: {tx}')
        return True, str(tx), None
    except Exception as e:
        logger.warning(f'TON API fallo: {e}. Intentando ToncenterV3...')

    # ── Fallback 2: Toncenter V3 ─────────────────────────────────────────
    try:
        from tonutils.client import ToncenterV3Client
        client = ToncenterV3Client(api_key=api_key or '', is_testnet=False)
        wallet, _, _, _ = WalletV4R2.from_mnemonic(client, words)
        logger.info(f'Wallet lista (Toncenter V3). Enviando {ton_amount} TON -> {to_addr}')
        tx = await wallet.transfer(destination=to_addr, amount=ton_amount,
                                   body=memo or None)
        logger.info(f'SUCCESS via Toncenter V3: {tx}')
        return True, str(tx), None
    except Exception as e:
        logger.error(f'Todos los clientes fallaron. Último error: {e}')
        return False, None, str(e)
