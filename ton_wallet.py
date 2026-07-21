"""
ton_wallet.py — tonutils con ToncenterClient
"""
import asyncio
import logging
import re

logger = logging.getLogger(__name__)

TON_TO_NANO = 1_000_000_000


def send_ton(mnemonic, to_addr, ton_amount, memo='', api_key='',
             bot_wallet_address=''):
    try:
        if isinstance(mnemonic, str):
            words = mnemonic.strip().split()
        else:
            words = list(mnemonic)

        if len(words) != 24:
            return False, None, f'Mnemonic necesita 24 palabras (tiene {len(words)})'

        # API key es recomendada pero no obligatoria; sin ella Toncenter usa
        # límites más estrictos pero puede funcionar para envíos ocasionales.
        if not api_key:
            logger.warning('send_ton sin TONCENTER_API_KEY — usando límites públicos')

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


def _extract_hash(tx) -> str:
    """Extrae hash hex limpio de 64 chars del resultado de tonutils."""
    # Intentar atributos directos primero
    for attr in ('hash', 'cell_hash', 'tx_hash', 'body_hash'):
        val = getattr(tx, attr, None)
        if val is not None:
            if isinstance(val, bytes):
                return val.hex()
            s = str(val).strip()
            if re.match(r'^[0-9a-fA-F]{64}$', s):
                return s

    # Intentar método hash()
    try:
        h = tx.hash()
        if isinstance(h, bytes):
            return h.hex()
        s = str(h).strip()
        if re.match(r'^[0-9a-fA-F]{64}$', s):
            return s
    except Exception:
        pass

    # Buscar patrón hex de 64 chars dentro del string del objeto
    s = str(tx)
    matches = re.findall(r'[0-9a-fA-F]{64}', s)
    if matches:
        return matches[0]

    # Último recurso: truncar
    return s[:190]


async def _send(words, to_addr, ton_amount, memo, api_key):
    from tonutils.clients import ToncenterClient
    from tonutils.contracts.wallet import WalletV5R1

    amount_nano = int(round(ton_amount * TON_TO_NANO))

    # Crear el cliente de Toncenter de forma compatible con varias versiones de tonutils.
    client = None
    # tonutils >= 2.x : requiere 'network' como primer argumento (NetworkGlobalID.MAINNET)
    try:
        from ton_core import NetworkGlobalID
        client = ToncenterClient(NetworkGlobalID.MAINNET, api_key=api_key or None)
    except Exception:
        client = None
    # Fallbacks para versiones antiguas
    if client is None:
        try:
            client = ToncenterClient(api_key=api_key, is_testnet=False)
        except TypeError:
            client = ToncenterClient(api_key=api_key)

    async with client:
        result = WalletV5R1.from_mnemonic(client, words)
        if asyncio.iscoroutine(result):
            result = await result
        wallet = result[0] if isinstance(result, (tuple, list)) else result

        logger.info(f'Enviando {ton_amount} TON ({amount_nano} nanotons) -> {to_addr}, memo={memo!r}')
        tx = await wallet.transfer(
            destination=to_addr,
            amount=amount_nano,
            body=str(memo) if memo else None
        )

        tx_hash = _extract_hash(tx)
        logger.info(f'SUCCESS tx_hash={tx_hash}')
        return True, tx_hash, None
