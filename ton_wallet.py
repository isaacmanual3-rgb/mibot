"""
ton_wallet.py — WalletV5R1 via tonutils
Soporta: Toncenter V3 (principal), V2 (fallback), TonapiClient (fallback 2)

IMPORTANTE: Este código usa WalletV5R1 para coincidir con la wallet
desplegada en la blockchain (wallet v5 r1 según tonscan.org).
"""
import asyncio
import logging

logger = logging.getLogger(__name__)


def send_ton(mnemonic, to_addr, ton_amount, memo='', api_key='',
             bot_wallet_address=''):
    """Envía TON via WalletV5R1. Retorna (success, tx_hash, error)."""
    try:
        if isinstance(mnemonic, str):
            words = mnemonic.strip().split()
        else:
            words = list(mnemonic)
        if len(words) != 24:
            return False, None, f'Mnemonic necesita 24 palabras (tiene {len(words)})'

        if not api_key:
            return False, None, 'TONCENTER_API_KEY no configurada — ve a Railway → Variables'

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
    # WalletV5R1 — coincide con "wallet v5 r1" mostrado en tonscan.org
    from tonutils.wallet import WalletV5R1

    errors = []

    # ── Intento 1: Toncenter V3 (recomendado) ───────────────────────────
    try:
        from tonutils.client import ToncenterV3Client
        client = ToncenterV3Client(api_key=api_key, is_testnet=False)
        wallet, _, _, _ = WalletV5R1.from_mnemonic(client, words)
        logger.info(f'[V5R1] Wallet lista (ToncenterV3). Enviando {ton_amount} TON -> {to_addr}')
        tx = await wallet.transfer(destination=to_addr, amount=ton_amount,
                                   body=memo or None)
        logger.info(f'SUCCESS via ToncenterV3: {tx}')
        return True, str(tx), None
    except Exception as e:
        logger.warning(f'ToncenterV3 fallo: {e}')
        errors.append(f'ToncenterV3: {e}')

    # ── Intento 2: Toncenter V2 ──────────────────────────────────────────
    try:
        from tonutils.client import ToncenterV2Client
        client = ToncenterV2Client(api_key=api_key, is_testnet=False)
        wallet, _, _, _ = WalletV5R1.from_mnemonic(client, words)
        logger.info(f'[V5R1] Wallet lista (ToncenterV2). Enviando {ton_amount} TON -> {to_addr}')
        tx = await wallet.transfer(destination=to_addr, amount=ton_amount,
                                   body=memo or None)
        logger.info(f'SUCCESS via ToncenterV2: {tx}')
        return True, str(tx), None
    except Exception as e:
        logger.warning(f'ToncenterV2 fallo: {e}')
        errors.append(f'ToncenterV2: {e}')

    # ── Intento 3: TonapiClient ──────────────────────────────────────────
    try:
        from tonutils.client import TonapiClient
        client = TonapiClient(api_key=api_key, is_testnet=False)
        wallet, _, _, _ = WalletV5R1.from_mnemonic(client, words)
        logger.info(f'[V5R1] Wallet lista (TonapiClient). Enviando {ton_amount} TON -> {to_addr}')
        tx = await wallet.transfer(destination=to_addr, amount=ton_amount,
                                   body=memo or None)
        logger.info(f'SUCCESS via TonapiClient: {tx}')
        return True, str(tx), None
    except Exception as e:
        logger.warning(f'TonapiClient fallo: {e}')
        errors.append(f'TonapiClient: {e}')

    error_summary = ' | '.join(errors)
    logger.error(f'Todos los clientes fallaron: {error_summary}')
    return False, None, error_summary
