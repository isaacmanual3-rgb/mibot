"""
ton_wallet.py — tonutils 2.0.0
clients.http = ToncenterClient
contracts.wallet = WalletV5R1
"""
import asyncio
import logging

logger = logging.getLogger(__name__)


def send_ton(mnemonic, to_addr, ton_amount, memo='', api_key='',
             bot_wallet_address=''):
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

    # Inspeccionar ToncenterClient para ver sus parámetros
    try:
        from tonutils.clients.http import ToncenterClient
        import inspect
        sig = inspect.signature(ToncenterClient.__init__)
        logger.info(f'ToncenterClient params: {list(sig.parameters.keys())}')
    except Exception as e:
        logger.warning(f'No se pudo inspeccionar ToncenterClient: {e}')

    # ── Intento 1: sin is_testnet ──────────────────────────────────────
    try:
        from tonutils.clients.http import ToncenterClient
        from tonutils.contracts.wallet import WalletV5R1

        client = ToncenterClient(api_key=api_key)
        wallet, _, _, _ = await WalletV5R1.from_mnemonic(client, words)
        logger.info(f'Enviando {ton_amount} TON -> {to_addr}')
        tx = await wallet.transfer(
            destination=to_addr,
            amount=ton_amount,
            body=memo if memo else None
        )
        logger.info(f'SUCCESS: {tx}')
        return True, str(tx), None
    except ImportError as e:
        logger.warning(f'Import 1 fallo: {e}')
        errors.append(f'Import1: {e}')
    except Exception as e:
        logger.warning(f'Intento 1 fallo: {e}')
        errors.append(f'Intento1: {e}')

    # ── Intento 2: clients.base ────────────────────────────────────────
    try:
        from tonutils.clients.base import ToncenterClient
        from tonutils.contracts.wallet import WalletV5R1

        client = ToncenterClient(api_key=api_key)
        wallet, _, _, _ = await WalletV5R1.from_mnemonic(client, words)
        tx = await wallet.transfer(
            destination=to_addr,
            amount=ton_amount,
            body=memo if memo else None
        )
        logger.info(f'SUCCESS (base): {tx}')
        return True, str(tx), None
    except ImportError as e:
        logger.warning(f'Import 2 fallo: {e}')
        errors.append(f'Import2: {e}')
    except Exception as e:
        logger.warning(f'Intento 2 fallo: {e}')
        errors.append(f'Intento2: {e}')

    # ── Intento 3: tonutils.clients directo ───────────────────────────
    try:
        import tonutils.clients as cl
        import inspect
        # Listar clases disponibles en clients
        clases = [name for name, obj in inspect.getmembers(cl, inspect.isclass)]
        logger.info(f'Clases en clients: {clases}')
    except Exception as e:
        logger.warning(f'Diagnóstico clients fallo: {e}')

    error_summary = ' | '.join(errors)
    logger.error(f'Todos los intentos fallaron: {error_summary}')
    return False, None, error_summary
