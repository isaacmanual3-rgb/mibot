"""
ton_wallet.py — WalletV5R1 via tonutils 2.x
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
            return False, None, 'TONCENTER_API_KEY no configurada'

        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                raise RuntimeError
            return loop.run_until_complete(
                _send(words, to_addr, float(ton_amount), memo, api_key)
            )
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(
                    _send(words, to_addr, float(ton_amount), memo, api_key)
                )
            finally:
                loop.close()

    except Exception as e:
        logger.exception(f'send_ton error: {e}')
        return False, None, str(e)


async def _send(words, to_addr, ton_amount, memo, api_key):
    errors = []

    # ── Intento 1: ToncenterV3Client ───────────────────────────────────
    try:
        from tonutils.client import ToncenterV3Client
        from tonutils.wallet import WalletV5R1

        client = ToncenterV3Client(api_key=api_key, is_testnet=False)
        wallet, _, _, _ = await WalletV5R1.from_mnemonic(client, words)
        logger.info(f'[V5R1] Enviando {ton_amount} TON -> {to_addr} (ToncenterV3)')
        tx = await wallet.transfer(
            destination=to_addr,
            amount=ton_amount,
            body=memo if memo else None
        )
        logger.info(f'SUCCESS via ToncenterV3: {tx}')
        return True, str(tx), None
    except ImportError as e:
        errors.append(f'ImportError: {e}')
    except Exception as e:
        logger.warning(f'ToncenterV3 fallo: {e}')
        errors.append(f'ToncenterV3: {e}')

    # ── Intento 2: ToncenterV2Client ───────────────────────────────────
    try:
        from tonutils.client import ToncenterV2Client
        from tonutils.wallet import WalletV5R1

        client = ToncenterV2Client(api_key=api_key, is_testnet=False)
        wallet, _, _, _ = await WalletV5R1.from_mnemonic(client, words)
        logger.info(f'[V5R1] Enviando {ton_amount} TON -> {to_addr} (ToncenterV2)')
        tx = await wallet.transfer(
            destination=to_addr,
            amount=ton_amount,
            body=memo if memo else None
        )
        logger.info(f'SUCCESS via ToncenterV2: {tx}')
        return True, str(tx), None
    except ImportError as e:
        errors.append(f'ImportError: {e}')
    except Exception as e:
        logger.warning(f'ToncenterV2 fallo: {e}')
        errors.append(f'ToncenterV2: {e}')

    # ── Intento 3: TonapiClient ────────────────────────────────────────
    try:
        from tonutils.client import TonapiClient
        from tonutils.wallet import WalletV5R1

        client = TonapiClient(api_key=api_key, is_testnet=False)
        wallet, _, _, _ = await WalletV5R1.from_mnemonic(client, words)
        logger.info(f'[V5R1] Enviando {ton_amount} TON -> {to_addr} (TonapiClient)')
        tx = await wallet.transfer(
            destination=to_addr,
            amount=ton_amount,
            body=memo if memo else None
        )
        logger.info(f'SUCCESS via TonapiClient: {tx}')
        return True, str(tx), None
    except ImportError as e:
        errors.append(f'ImportError: {e}')
    except Exception as e:
        logger.warning(f'TonapiClient fallo: {e}')
        errors.append(f'TonapiClient: {e}')

    error_summary = ' | '.join(errors)
    logger.error(f'Todos los clientes fallaron: {error_summary}')
    return False, None, error_summary
