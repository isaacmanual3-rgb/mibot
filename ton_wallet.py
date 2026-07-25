"""
ton_wallet.py — tonutils con ToncenterClient

Incluye verificacion de saldo ANTES de enviar. Sin esto,
wallet.transfer() difunde el mensaje a la red y devuelve un hash
aunque la wallet este vacia: la transaccion se acepta pero falla
en la blockchain, y la app ya marco el retiro como completado.
"""
import asyncio
import json
import logging
import re
import urllib.parse
import urllib.request

logger = logging.getLogger(__name__)

TON_TO_NANO = 1_000_000_000

# Margen que se deja SIEMPRE en la wallet: cubre la comision de red
# (~0.005 TON por envio) mas la renta de almacenamiento del contrato.
# Si el saldo no alcanza para monto + este margen, no se intenta enviar.
FEE_RESERVE_TON = 0.05

# Prefijo reconocible para que app.py distinga "no hay fondos" de
# cualquier otro fallo y pueda avisar al admin.
ERR_SIN_FONDOS = 'SALDO_INSUFICIENTE'


def get_wallet_balance(address, api_key='', timeout=12):
    """
    Consulta el saldo on-chain de una direccion via Toncenter HTTP API.

    Se usa la API REST directa en vez de tonutils para no depender de
    los cambios de firma entre versiones de la libreria.

    Devuelve (saldo_en_ton: float|None, error: str|None).
    """
    if not address:
        return None, 'Direccion de wallet vacia'

    url = ('https://toncenter.com/api/v2/getAddressBalance?address='
           + urllib.parse.quote(str(address), safe=''))

    req = urllib.request.Request(url, headers={'Accept': 'application/json'})
    if api_key:
        req.add_header('X-API-Key', api_key)

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        return None, f'Toncenter no responde: {e}'

    if not data.get('ok'):
        return None, f"Toncenter devolvio error: {data.get('error', data)}"

    try:
        nano = int(data.get('result') or 0)
    except (TypeError, ValueError):
        return None, f"Saldo ilegible: {data.get('result')!r}"

    return nano / TON_TO_NANO, None


def check_funds(bot_wallet_address, ton_amount, api_key='', reserve=None):
    """
    Verifica si la wallet del bot tiene saldo para cubrir el envio.

    Devuelve (alcanza: bool, saldo: float|None, error: str|None).

    Si no se puede consultar el saldo devuelve alcanza=False (fail-closed):
    ante la duda es mejor mandar el retiro a revision manual que difundir
    una transaccion que va a fallar. Se reintenta una vez para tolerar
    cortes momentaneos de red.
    """
    if reserve is None:
        reserve = FEE_RESERVE_TON

    necesario = float(ton_amount) + float(reserve)

    saldo, err = get_wallet_balance(bot_wallet_address, api_key)
    if saldo is None:
        # Un reintento por si fue un corte momentaneo
        logger.warning(f'[check_funds] primer intento fallo ({err}), reintentando')
        saldo, err = get_wallet_balance(bot_wallet_address, api_key)

    if saldo is None:
        return False, None, f'No se pudo verificar el saldo: {err}'

    if saldo < necesario:
        return False, saldo, (
            f'{ERR_SIN_FONDOS}: la wallet tiene {saldo:.4f} TON y se necesitan '
            f'{necesario:.4f} TON ({ton_amount:.4f} + {reserve:.4f} de comision)'
        )

    return True, saldo, None


def send_ton(mnemonic, to_addr, ton_amount, memo='', api_key='',
             bot_wallet_address='', skip_balance_check=False):
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

        # ── Verificacion de saldo ANTES de difundir la transaccion.
        # Es el punto clave: sin esto se enviaba igual y quedaba "Fallido"
        # en la blockchain mientras la app lo daba por pagado.
        if not skip_balance_check:
            if not bot_wallet_address:
                logger.warning(
                    'send_ton sin bot_wallet_address — no se puede verificar '
                    'saldo, se envia a ciegas'
                )
            else:
                alcanza, saldo, err = check_funds(
                    bot_wallet_address, float(ton_amount), api_key
                )
                if not alcanza:
                    logger.error(f'[send_ton] envio abortado: {err}')
                    return False, None, err
                logger.info(
                    f'[send_ton] saldo OK: {saldo:.4f} TON disponibles para '
                    f'enviar {float(ton_amount):.4f} TON'
                )

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
