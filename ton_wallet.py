"""
ton_wallet.py — WalletV5R1 via tonutils 2.x
Compatible con tonutils >= 2.0.0
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

    # ── Intento 1: tonutils 2.x ────────────────────────────────────────
    try:
        import tonutils
        logger.info(f'tonutils version: {getattr(tonutils, "__version__", "unknown")}')
        logger.info(f'tonutils path: {tonutils.__file__}')

        # Listar submódulos disponibles
        import pkgutil
        mods = [m.name for m in pkgutil.iter_modules(tonutils.__path__)]
        logger.info(f'tonutils modules: {mods}')
    except Exception as e:
        logger.warning(f'No se pudo inspeccionar tonutils: {e}')

    # ── Intento con imports de tonutils 2.x ────────────────────────────
    try:
        from tonutils.wallet import WalletV5R1
        from tonutils.providers.toncenter import ToncenterClient

        client = ToncenterClient(api_key=api_key, is_testnet=False)
        wallet, _, _, _ = await WalletV5R1.from_mnemonic(client, words)
        logger.info(f'[V5R1] Enviando {ton_amount} TON -> {to_addr}')
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

    # ── Intento con imports alternativos ───────────────────────────────
    try:
        from tonutils.wallet import WalletV5R1
        from tonutils.toncenter import ToncenterClient

        client = ToncenterClient(api_key=api_key, is_testnet=False)
        wallet, _, _, _ = await WalletV5R1.from_mnemonic(client, words)
        tx = await wallet.transfer(
            destination=to_addr,
            amount=ton_amount,
            body=memo if memo else None
        )
        logger.info(f'SUCCESS (alt): {tx}')
        return True, str(tx), None
    except ImportError as e:
        logger.warning(f'Import 2 fallo: {e}')
        errors.append(f'Import2: {e}')
    except Exception as e:
        logger.warning(f'Intento 2 fallo: {e}')
        errors.append(f'Intento2: {e}')

    # ── Intento directo sin client ─────────────────────────────────────
    try:
        from tonutils.wallet import WalletV5R1

        wallet, _, _, _ = await WalletV5R1.from_mnemonic(None, words)
        tx = await wallet.transfer(
            destination=to_addr,
            amount=ton_amount,
            body=memo if memo else None
        )
        logger.info(f'SUCCESS (no client): {tx}')
        return True, str(tx), None
    except ImportError as e:
        logger.warning(f'Import 3 fallo: {e}')
        errors.append(f'Import3: {e}')
    except Exception as e:
        logger.warning(f'Intento 3 fallo: {e}')
        errors.append(f'Intento3: {e}')

    error_summary = ' | '.join(errors)
    logger.error(f'Todos los clientes fallaron: {error_summary}')
    return False, None, error_summary
