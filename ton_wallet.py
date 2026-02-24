"""
ton_wallet.py — WalletV5R1 via tonutils 2.0.0
Módulos disponibles: clients, contracts, types, utils
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

    # ── Intento 1: tonutils 2.0.0 — clients + contracts ───────────────
    try:
        from tonutils.clients import ToncenterClient
        from tonutils.contracts import WalletV5R1

        client = ToncenterClient(api_key=api_key, is_testnet=False)
        wallet, _, _, _ = await WalletV5R1.from_mnemonic(client, words)
        logger.info(f'[V5R1] Enviando {ton_amount} TON -> {to_addr}')
        tx = await wallet.transfer(
            destination=to_addr,
            amount=ton_amount,
            body=memo if memo else None
        )
        logger.info(f'SUCCESS via ToncenterClient: {tx}')
        return True, str(tx), None
    except ImportError as e:
        logger.warning(f'Import 1 fallo: {e}')
        errors.append(f'Import1: {e}')
    except Exception as e:
        logger.warning(f'Intento 1 fallo: {e}')
        errors.append(f'Intento1: {e}')

    # ── Intento 2: contracts con wallet submodule ──────────────────────
    try:
        from tonutils.clients import ToncenterClient
        from tonutils.contracts.wallet import WalletV5R1

        client = ToncenterClient(api_key=api_key, is_testnet=False)
        wallet, _, _, _ = await WalletV5R1.from_mnemonic(client, words)
        tx = await wallet.transfer(
            destination=to_addr,
            amount=ton_amount,
            body=memo if memo else None
        )
        logger.info(f'SUCCESS via contracts.wallet: {tx}')
        return True, str(tx), None
    except ImportError as e:
        logger.warning(f'Import 2 fallo: {e}')
        errors.append(f'Import2: {e}')
    except Exception as e:
        logger.warning(f'Intento 2 fallo: {e}')
        errors.append(f'Intento2: {e}')

    # ── Intento 3: explorar contratos disponibles ──────────────────────
    try:
        import tonutils.contracts as c
        import pkgutil
        submods = [m.name for m in pkgutil.iter_modules(c.__path__)]
        logger.info(f'contracts submódulos: {submods}')

        import tonutils.clients as cl
        submods2 = [m.name for m in pkgutil.iter_modules(cl.__path__)]
        logger.info(f'clients submódulos: {submods2}')
    except Exception as e:
        logger.warning(f'Diagnóstico fallo: {e}')

    error_summary = ' | '.join(errors)
    logger.error(f'Todos los intentos fallaron: {error_summary}')
    return False, None, error_summary
