"""
ton_wallet.py — v13 FINAL
Fix crítico: hash() de Cell ahora incluye depth de refs
según el estándar TON (TVM whitepaper).

Hash correcto:
  SHA256(d1 || d2 || data_augmented || depth(ref)*2bytes || hash(ref)*32bytes ...)
"""

import base64
import hashlib
import struct
import time
import logging
import requests

logger = logging.getLogger(__name__)

TONCENTER    = 'https://toncenter.com/api/v2'
SUBWALLET_ID = 698983191


# ══════════════════════════════════════════════════════════════
#  MNEMONIC → SEED (algoritmo Tonkeeper)
# ══════════════════════════════════════════════════════════════

def mnemonic_to_seed(words):
    if isinstance(words, str):
        words = words.strip().split()
    password = ' '.join(words).encode('utf-8')
    entropy  = hashlib.pbkdf2_hmac('sha512', password, b'TON default seed', 100000)
    return entropy[:32]


# ══════════════════════════════════════════════════════════════
#  BIT BUILDER
# ══════════════════════════════════════════════════════════════

class _BB:
    def __init__(self):
        self._d = bytearray()
        self._n = 0

    def _bit(self, v):
        if self._n % 8 == 0:
            self._d.append(0)
        if v:
            self._d[-1] |= 1 << (7 - self._n % 8)
        self._n += 1

    def uint(self, v, bits):
        for i in range(bits - 1, -1, -1):
            self._bit((v >> i) & 1)
        return self

    def int_(self, v, bits):
        return self.uint(v & ((1 << bits) - 1), bits)

    def raw(self, b):
        for x in b:
            self.uint(x, 8)
        return self

    def grams(self, n):
        if n == 0:
            return self.uint(0, 4)
        byte_len = (n.bit_length() + 7) // 8
        self.uint(byte_len, 4)
        self.uint(n, byte_len * 8)
        return self

    def addr_std(self, wc, h):
        self.uint(0b10, 2)
        self._bit(0)
        self.int_(wc, 8)
        self.raw(h)
        return self

    def addr_none(self):
        return self.uint(0b00, 2)

    @property
    def bit_len(self): return self._n

    def augmented(self):
        buf = bytearray(self._d)
        if self._n % 8:
            buf[-1] |= 1 << (7 - self._n % 8)
        return bytes(buf)


# ══════════════════════════════════════════════════════════════
#  CELL + BOC
#  FIX: hash() incluye depth(ref) como 2 bytes antes de hash(ref)
# ══════════════════════════════════════════════════════════════

class Cell:
    def __init__(self):
        self.b    = _BB()
        self.refs = []

    def _desc(self):
        full = self.b.bit_len // 8
        part = 1 if self.b.bit_len % 8 else 0
        return bytes([len(self.refs), full * 2 + part])

    def depth(self):
        """Profundidad máxima de árbol de refs + 1."""
        if not self.refs:
            return 0
        return max(r.depth() for r in self.refs) + 1

    def hash(self):
        """
        Hash estándar TON (TVM whitepaper):
          SHA256(d1 || d2 || data || depth(ref1)[2] || hash(ref1)[32] || ...)
        """
        buf = self._desc() + self.b.augmented()
        # Primero todos los depths (2 bytes cada uno, big-endian)
        for r in self.refs:
            buf += r.depth().to_bytes(2, 'big')
        # Luego todos los hashes
        for r in self.refs:
            buf += r.hash()
        return hashlib.sha256(buf).digest()

    def boc_b64(self):
        cells = []
        self._collect(cells, set())
        n   = len(cells)
        idx = {id(c): i for i, c in enumerate(cells)}
        blobs = []
        for c in cells:
            ref_b = bytes([idx[id(r)] for r in c.refs])
            blobs.append(c._desc() + c.b.augmented() + ref_b)
        payload = b''.join(blobs)
        total   = len(payload)
        hdr = (
            b'\xb5\xee\x9c\x72'
            + bytes([0x01])
            + bytes([0x02])
            + n.to_bytes(1, 'big')
            + (1).to_bytes(1, 'big')
            + (0).to_bytes(1, 'big')
            + total.to_bytes(2, 'big')
            + (0).to_bytes(1, 'big')
        )
        return base64.b64encode(hdr + payload).decode()

    def _collect(self, out, seen):
        if id(self) in seen:
            return
        seen.add(id(self))
        out.append(self)
        for r in self.refs:
            r._collect(out, seen)


# ══════════════════════════════════════════════════════════════
#  ADDRESS HELPERS
# ══════════════════════════════════════════════════════════════

def _crc16xmodem(data):
    crc = 0
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if (crc & 0x8000) else (crc << 1)
    return crc & 0xFFFF


def friendly_to_raw(addr):
    addr = addr.strip()
    if ':' in addr:
        wc_str, hex_str = addr.split(':', 1)
        hex_str = hex_str.strip()
        if len(hex_str) != 64:
            raise ValueError(f'Dirección raw inválida: {addr!r}')
        return int(wc_str), bytes.fromhex(hex_str)
    s       = addr.replace('-', '+').replace('_', '/')
    padding = (4 - len(s) % 4) % 4
    raw     = base64.b64decode(s + '=' * padding)
    if len(raw) < 34:
        raise ValueError(f'Dirección TON inválida: {addr!r}')
    return struct.unpack('b', raw[1:2])[0], raw[2:34]


def _addr_friendly(wc, h):
    wc_byte = struct.pack('b', wc)
    prefix  = bytes([0x11]) + wc_byte + h
    crc     = _crc16xmodem(prefix)
    raw     = prefix + bytes([crc >> 8, crc & 0xFF])
    return base64.urlsafe_b64encode(raw).decode().rstrip('=')


# ══════════════════════════════════════════════════════════════
#  TONCENTER
# ══════════════════════════════════════════════════════════════

def _tc_post(method, payload, api_key=''):
    hdrs = {'Content-Type': 'application/json'}
    if api_key:
        hdrs['X-API-Key'] = api_key
    r = requests.post(f'{TONCENTER}/{method}', json=payload, headers=hdrs, timeout=15)
    return r.json()


def _get_network_time(api_key=''):
    """
    Obtiene tiempo Unix real usando múltiples fuentes en orden de prioridad:
    1. Toncenter getMasterchainInfo (con API key)
    2. Toncenter sin API key
    3. worldtimeapi.org (tiempo UTC externo confiable)
    4. time.cloudflare.com
    5. Tiempo local del sistema (último recurso)
    """
    # 1 y 2: Intentar con Toncenter
    for use_key in ([True, False] if api_key else [False]):
        try:
            hdrs = {}
            if use_key and api_key:
                hdrs['X-API-Key'] = api_key
            r = requests.get(f'{TONCENTER}/getMasterchainInfo', headers=hdrs, timeout=8)
            data = r.json()
            if data.get('ok'):
                utime = data['result'].get('last', {}).get('utime', 0)
                if utime > 1_000_000_000:
                    logger.info(f'TON net_time via Toncenter: {utime}')
                    return utime
        except Exception as e:
            logger.warning(f'Toncenter time fallo (key={use_key}): {e}')

    # 3: worldtimeapi como fallback confiable
    try:
        r = requests.get('https://worldtimeapi.org/api/timezone/Etc/UTC', timeout=6)
        data = r.json()
        utime = data.get('unixtime', 0)
        if utime > 1_000_000_000:
            logger.info(f'TON net_time via worldtimeapi: {utime}')
            return utime
    except Exception as e:
        logger.warning(f'worldtimeapi fallo: {e}')

    # 4: Cloudflare como otro fallback
    try:
        r = requests.get('https://time.cloudflare.com/cdn-cgi/trace', timeout=6)
        for line in r.text.splitlines():
            if line.startswith('ts='):
                utime = int(float(line.split('=')[1]))
                if utime > 1_000_000_000:
                    logger.info(f'TON net_time via Cloudflare: {utime}')
                    return utime
    except Exception as e:
        logger.warning(f'Cloudflare time fallo: {e}')

    # 5: Último recurso: tiempo local
    local = int(time.time())
    logger.error(f'TODAS las fuentes de tiempo fallaron. Usando tiempo local: {local}')
    return local


def _get_seqno(wallet_addr, api_key=''):
    resp = _tc_post('runGetMethod',
                    {'address': wallet_addr, 'method': 'seqno', 'stack': []},
                    api_key=api_key)
    if not resp.get('ok'):
        err = str(resp.get('error', '')).lower()
        if any(k in err for k in ('exit code', 'uninit', 'not found', '-13')):
            return 0
        logger.warning(f'seqno failed: {resp}')
        return None
    stack = resp.get('result', {}).get('stack', [])
    return int(stack[0][1], 16) if stack else 0


# ══════════════════════════════════════════════════════════════
#  BUILD BOC
# ══════════════════════════════════════════════════════════════

def _build_boc(seed, sender_wc, sender_hash, to_wc, to_hash,
               nanotons, seqno, memo, expire_at):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    priv = Ed25519PrivateKey.from_private_bytes(seed)

    # Mensaje interno
    int_msg = Cell()
    (int_msg.b
        .uint(1, 1)
        .uint(1, 1)
        .uint(0, 1)
        .addr_none()
        .addr_std(to_wc, to_hash)
        .grams(nanotons)
        .uint(0, 1)
        .grams(0).grams(0)
        .uint(0, 64).uint(0, 32)
        .uint(0, 1)
        .uint(0, 1))

    if memo:
        cmt = Cell()
        cmt.b.uint(0, 32).raw(memo.encode('utf-8')[:120])
        int_msg.refs.append(cmt)

    # Cuerpo wallet-v4r2: subwallet_id | valid_until | seqno | op | send_mode
    body = Cell()
    (body.b
        .uint(SUBWALLET_ID, 32)
        .uint(expire_at, 32)
        .uint(seqno, 32)
        .uint(0, 8)
        .uint(3, 8))
    body.refs.append(int_msg)

    # Firmar hash del body (ahora correcto con depth incluido)
    sig = priv.sign(body.hash())
    logger.info(f'Body hash: {body.hash().hex()[:16]}... seqno={seqno} expire={expire_at}')

    # Mensaje externo
    ext = Cell()
    (ext.b
        .uint(0b10, 2)
        .addr_none()
        .addr_std(sender_wc, sender_hash)
        .grams(0)
        .uint(0, 1)
        .uint(1, 1))

    signed = Cell()
    signed.b.raw(sig)
    signed.refs.append(body)
    ext.refs.append(signed)

    return ext.boc_b64()


# ══════════════════════════════════════════════════════════════
#  API PÚBLICA
# ══════════════════════════════════════════════════════════════

def send_ton(mnemonic, to_addr, ton_amount, memo='', api_key='',
             bot_wallet_address='UQCqD6yy4uQvbmsZ792ScmyfynK6GnlLkkaE6T-xBSWAKtJN'):
    """
    Envía TON desde la wallet del bot.
    Retorna: (success, tx_hash, error)
    """
    steps = []
    try:
        logger.info('TON WALLET v13 - hash con depth corregido')
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

        if isinstance(mnemonic, str):
            words = mnemonic.strip().split()
        else:
            words = list(mnemonic)

        if len(words) != 24:
            return False, None, f'Mnemonic debe tener 24 palabras (tiene {len(words)}).'

        steps.append('Derivando seed...')
        seed = mnemonic_to_seed(words)

        sender_addr = bot_wallet_address.strip()
        steps.append(f'Wallet bot: {sender_addr}')
        logger.info(f'TON sender wallet: {sender_addr}')

        sender_wc, sender_hash = friendly_to_raw(sender_addr)

        steps.append('Obteniendo seqno...')
        seqno = _get_seqno(sender_addr, api_key)
        if seqno is None:
            return False, None, 'No se pudo obtener seqno.'
        steps.append(f'Seqno: {seqno}')

        steps.append(f'Parseando destino: {to_addr}')
        to_wc, to_hash = friendly_to_raw(to_addr)
        steps.append(f'Destino OK wc={to_wc}')

        net_time  = _get_network_time(api_key)
        expire_at = net_time + 300  # 5 minutos para mayor tolerancia a latencia
        logger.info(f'net_time={net_time} expire_at={expire_at}')

        nanotons = int(float(ton_amount) * 1_000_000_000)
        steps.append(f'Firmando BOC: {ton_amount} TON -> {to_addr}')
        boc_b64 = _build_boc(seed, sender_wc, sender_hash,
                              to_wc, to_hash,
                              nanotons, seqno, memo, expire_at)
        steps.append(f'BOC OK ({len(boc_b64)} chars, prefijo={boc_b64[:8]})')

        steps.append('Transmitiendo a toncenter...')
        result = _tc_post('sendBocReturnHash', {'boc': boc_b64}, api_key=api_key)
        logger.info(f'TON broadcast result: {result}')

        if result.get('ok'):
            tx_hash = result.get('result', {}).get('hash', '')
            logger.info(f'TON send SUCCESS: {tx_hash}')
            return True, tx_hash, None
        else:
            err = result.get('error', str(result))
            logger.error(f'TON broadcast FAILED: {err} | pasos: {steps}')
            return False, None, f'Error al enviar: {err}'

    except Exception as exc:
        logger.exception(f'send_ton EXCEPTION pasos={steps}: {exc}')
        return False, None, str(exc)
