"""
ton_wallet.py — Wallet V4R2 usando tonutils
Librería: https://github.com/nessshon/tonutils
Instalar: pip install tonutils
"""
import asyncio
import logging
import requests
import time
from email.utils import parsedate_to_datetime

logger = logging.getLogger(__name__)
TONCENTER = 'https://toncenter.com/api/v2'


def _get_time(api_key=''):
    for key in ([api_key, ''] if api_key else ['']):
        try:
            hdrs = {'X-API-Key': key} if key else {}
            r = requests.get(f'{TONCENTER}/getMasterchainInfo', headers=hdrs, timeout=8)
            data = r.json()
            if data.get('ok'):
                t = data.get('result', {}).get('last', {}).get('utime', 0)
                if t > 1_000_000_000:
                    return t
            extra = str(data.get('@extra', ''))
            if ':' in extra:
                try:
                    t = int(extra.split(':')[0])
                    if t > 1_000_000_000:
                        return t
                except Exception:
                    pass
        except Exception:
            pass
    return int(time.time())


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
        
        # Intentar con tonutils (async)
        try:
            return asyncio.run(_send_tonutils(words, to_addr, float(ton_amount), memo, api_key))
        except RuntimeError:
            # Si hay un loop corriendo (ej. dentro de Flask con async), crear nuevo
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(_send_tonutils(words, to_addr, float(ton_amount), memo, api_key))
            finally:
                loop.close()
    except Exception as e:
        logger.exception(f'send_ton: {e}')
        return False, None, str(e)


async def _send_tonutils(words, to_addr, ton_amount, memo, api_key):
    try:
        from tonutils.client import ToncenterV2Client
        from tonutils.wallet import WalletV4R2

        logger.info('TON WalletV4R2 via tonutils')

        # Cliente Toncenter V2
        client = ToncenterV2Client(
            api_key=api_key or None,
            is_testnet=False
        )

        # Cargar wallet desde mnemonic - seqno se obtiene automáticamente
        wallet, _, _, _ = WalletV4R2.from_mnemonic(client, words)
        logger.info(f'Wallet lista. Enviando {ton_amount} TON -> {to_addr}')

        # Transferencia - tonutils maneja seqno, firma, BOC internamente
        tx_hash = await wallet.transfer(
            destination=to_addr,
            amount=ton_amount,
            body=memo or None
        )

        logger.info(f'SUCCESS tx_hash={tx_hash}')
        return True, str(tx_hash), None

    except ImportError:
        logger.error('tonutils no instalado. Agrega "tonutils" a requirements.txt')
        return False, None, 'tonutils no instalado. Agrega "tonutils" a requirements.txt y redespliega.'
    except Exception as e:
        logger.error(f'tonutils error: {e}')
        return False, None, str(e)
