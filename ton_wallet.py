"""
ton_wallet.py — v9 DEFINITIVO
Usa tonsdk para derivar la wallet exactamente igual que Tonkeeper.
"""

import logging
import base64
import requests

logger = logging.getLogger(__name__)

TONCENTER = 'https://toncenter.com/api/v2'


def _tc_post(method, payload, api_key=''):
    hdrs = {'Content-Type': 'application/json'}
    if api_key:
        hdrs['X-API-Key'] = api_key
    r = requests.post(f'{TONCENTER}/{method}', json=payload, headers=hdrs, timeout=15)
    return r.json()


def _get_seqno(wallet_addr, api_key=''):
    resp = _tc_post(
        'runGetMethod',
        {'address': wallet_addr, 'method': 'seqno', 'stack': []},
        api_key=api_key,
    )
    if not resp.get('ok'):
        err = str(resp.get('error', '')).lower()
        if any(k in err for k in ('exit code', 'uninit', 'not found', '-13')):
            return 0
        logger.warning(f'seqno failed: {resp}')
        return None
    stack = resp.get('result', {}).get('stack', [])
    return int(stack[0][1], 16) if stack else 0


def send_ton(mnemonic, to_addr, ton_amount, memo='', api_key=''):
    """
    Envía TON usando tonsdk — misma derivación de clave que Tonkeeper.

    mnemonic  : str (24 palabras separadas por espacio) o list
    to_addr   : dirección destino (EQ..., UQ..., o 0:hexhash)
    ton_amount: cantidad en TON (float)
    memo      : comentario/referencia opcional
    api_key   : TonCenter API key (recomendado para evitar rate limit)

    Retorna: (success: bool, tx_hash: str|None, error: str|None)
    """
    steps = []
    try:
        # Importar tonsdk
        try:
            from tonsdk.contract.wallet import WalletVersionEnum, Wallets
            from tonsdk.utils import to_nano, Address
        except ImportError:
            return False, None, (
                'tonsdk no instalado. '
                'Asegúrate de que "tonsdk==0.0.23" esté en requirements.txt y redespliega.'
            )

        # Preparar mnemonic
        if isinstance(mnemonic, str):
            words = mnemonic.strip().split()
        else:
            words = list(mnemonic)

        if len(words) != 24:
            return False, None, f'El mnemonic debe tener 24 palabras, tiene {len(words)}.'

        steps.append('Derivando clave con tonsdk...')
        # Wallets.from_mnemonics deriva la clave igual que Tonkeeper
        _mnemonics, _pub, _priv, wallet = Wallets.from_mnemonics(
            words, WalletVersionEnum.v4r2, workchain=0
        )

        sender_addr = wallet.address.to_string(True, True, False)
        steps.append(f'Wallet bot: {sender_addr}')
        logger.info(f'TON sender wallet: {sender_addr}')

        # Obtener seqno
        steps.append('Obteniendo seqno...')
        seqno = _get_seqno(sender_addr, api_key)
        if seqno is None:
            err = 'No se pudo obtener seqno. La wallet debe tener TON y estar desplegada.'
            logger.error(f'TON send FAILED: {err}')
            return False, None, err
        steps.append(f'Seqno: {seqno}')

        # Parsear y normalizar dirección destino
        steps.append(f'Parseando destino: {to_addr}')
        dest = Address(to_addr)
        dest_str = dest.to_string(True, True, True)
        steps.append(f'Destino OK: {dest_str}')

        # Construir mensaje de transferencia y firmar
        nanotons = to_nano(float(ton_amount), 'ton')
        steps.append(f'Firmando BOC: {ton_amount} TON -> {dest_str}')

        transfer = wallet.create_transfer_message(
            to_addr=dest_str,
            amount=nanotons,
            seqno=seqno,
            payload=memo or '',
            send_mode=3,
        )

        # Serializar a BOC base64
        boc_bytes = transfer['message'].to_boc(has_idx=False)
        boc_str = base64.b64encode(boc_bytes).decode()
        steps.append(f'BOC OK ({len(boc_str)} chars, prefijo={boc_str[:8]})')

        # Transmitir a TonCenter
        steps.append('Transmitiendo a toncenter...')
        result = _tc_post('sendBocReturnHash', {'boc': boc_str}, api_key=api_key)
        logger.info(f'TON broadcast result: {result}')

        if result.get('ok'):
            tx_hash = result.get('result', {}).get('hash', '')
            steps.append(f'TX OK: {tx_hash}')
            logger.info(f'TON send SUCCESS: {tx_hash}')
            return True, tx_hash, None
        else:
            err = result.get('error', str(result))
            steps.append(f'Broadcast error: {err}')
            logger.error(f'TON broadcast FAILED: {err} | pasos: {steps}')
            return False, None, f'Error al enviar: {err}'

    except Exception as exc:
        steps.append(f'EXCEPCION: {exc}')
        logger.exception(f'send_ton EXCEPTION pasos={steps}: {exc}')
        return False, None, str(exc)
