"""
ton_wallet.py — tonutils (ToncenterClient desde tonutils.clients)
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
    # Importar directo del paquete raíz clients (no submodulo .http ni .base)
    from tonutils.clients import ToncenterClient
    from tonutils.contracts.wallet import WalletV5R1

    try:
        client = ToncenterClient(api_key=api_key, is_testnet=False)
    except TypeError:
        client = ToncenterClient(api_key=api_key)

    # from_mnemonic en versiones recientes NO es awaitable
    result = WalletV5R1.from_mnemonic(client, words)
    if asyncio.iscoroutine(result):
        result = await result
    wallet = result[0] if isinstance(result, (tuple, list)) else result

    logger.info(f'Enviando {ton_amount} TON -> {to_addr}')
    tx = await wallet.transfer(
        destination=to_addr,
        amount=ton_amount,
        body=memo if memo else None
    )
    logger.info(f'SUCCESS: {tx}')
    return True, str(tx), None
