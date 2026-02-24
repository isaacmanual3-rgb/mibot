"""
ton_wallet.py — tonutils con ToncenterClient
"""
import asyncio
import logging
import hashlib

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


def _extract_hash(tx) -> str:
    """Extrae el hash de la transacción de distintos formatos que puede devolver tonutils."""
    # Si es string limpio (hex de 64 chars), úsalo directo
    if isinstance(tx, str):
        s = tx.strip()
        # Si parece un hash hex puro, devuélvelo
        if len(s) <= 200 and all(c in '0123456789abcdefABCDEF' for c in s):
            return s
        # Si es muy largo (objeto serializado), intenta extraer hash interno
        # Buscar patrón de 64 chars hex dentro del string
        import re
        matches = re.findall(r'\b[0-9a-fA-F]{64}\b', s)
        if matches:
            return matches[0]
        # Último recurso: truncar a 190 chars
        return s[:190]

    # Si tiene atributo hash o cell_hash
    for attr in ('hash', 'cell_hash', 'tx_hash', 'body_hash'):
        val = getattr(tx, attr, None)
        if val is not None:
            if isinstance(val, bytes):
                return val.hex()
            return str(val)[:190]

    # Si tiene método hash()
    try:
        h = tx.hash()
        if isinstance(h, bytes):
            return h.hex()
        return str(h)[:190]
    except Exception:
        pass

    # Último recurso
    return str(tx)[:190]


async def _send(words, to_addr, ton_amount, memo, api_key):
    from tonutils.clients import ToncenterClient
    from tonutils.contracts.wallet import WalletV5R1

    amount_nano = int(round(ton_amount * TON_TO_NANO))

    try:
        client = ToncenterClient(api_key=api_key, is_testnet=False)
    except TypeError:
        client = ToncenterClient(api_key=api_key)

    async with client:
        result = WalletV5R1.from_mnemonic(client, words)
        if asyncio.iscoroutine(result):
            result = await result
        wallet = result[0] if isinstance(result, (tuple, list)) else result

        logger.info(f'Enviando {ton_amount} TON ({amount_nano} nanotons) -> {to_addr}')
        tx = await wallet.transfer(
            destination=to_addr,
            amount=amount_nano,
            body=memo if memo else None
        )

        tx_hash = _extract_hash(tx)
        logger.info(f'SUCCESS tx_hash={tx_hash}')
        return True, tx_hash, None
