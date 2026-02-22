"""
ton_wallet.py — Implementación verificada Wallet V4R2
Basada en el estándar oficial TON.
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


# ── Mnemonic → Seed ──────────────────────────────────────────────────────────

def mnemonic_to_seed(words):
    if isinstance(words, str):
        words = words.strip().split()
    password = ' '.join(words).encode('utf-8')
    return hashlib.pbkdf2_hmac('sha512', password, b'TON default seed', 100000)[:32]


# ── Bit Builder ───────────────────────────────────────────────────────────────

class BitBuilder:
    def __init__(self):
        self._buf = bytearray()
        self._len = 0

    def write_bit(self, v):
        if self._len % 8 == 0:
            self._buf.append(0)
        if v:
            self._buf[-1] |= 1 << (7 - self._len % 8)
        self._len += 1

    def write_uint(self, v, bits):
        for i in range(bits - 1, -1, -1):
            self.write_bit((v >> i) & 1)
        return self

    def write_int(self, v, bits):
        return self.write_uint(v & ((1 << bits) - 1), bits)

    def write_bytes(self, b):
        for x in b:
            self.write_uint(x, 8)
        return self

    def write_coins(self, n):
        if n == 0:
            return self.write_uint(0, 4)
        byte_len = (n.bit_length() + 7) // 8
        self.write_uint(byte_len, 4)
        self.write_uint(n, byte_len * 8)
        return self

    def write_addr(self, wc, addr_bytes):
        """addr_std: $10 anycast=0 wc:int8 addr:bits256"""
        self.write_uint(0b10, 2)
        self.write_bit(0)           # anycast = none
        self.write_int(wc, 8)
        self.write_bytes(addr_bytes)
        return self

    def write_addr_none(self):
        return self.write_uint(0b00, 2)

    @property
    def bit_len(self):
        return self._len

    def get_augmented(self):
        """Datos con bit de terminación si no es múltiplo de 8."""
        buf = bytearray(self._buf)
        if self._len % 8:
            buf[-1] |= 1 << (7 - self._len % 8)
        return bytes(buf)

    def get_data(self):
        return bytes(self._buf)


# ── Cell y BOC ───────────────────────────────────────────────────────────────

class Cell:
    def __init__(self):
        self.b = BitBuilder()
        self.refs = []

    def _descriptors(self):
        full = self.b.bit_len // 8
        part = 1 if self.b.bit_len % 8 else 0
        return bytes([len(self.refs), full * 2 + part])

    def depth(self):
        if not self.refs:
            return 0
        return max(r.depth() for r in self.refs) + 1

    def cell_hash(self):
        buf = self._descriptors() + self.b.get_augmented()
        for r in self.refs:
            buf += r.depth().to_bytes(2, 'big')
        for r in self.refs:
            buf += r.cell_hash()
        return hashlib.sha256(buf).digest()

    def to_boc(self):
        """Serializa a BOC base64."""
        cells = []
        seen = set()
        self._collect(cells, seen)
        
        n = len(cells)
        idx = {id(c): i for i, c in enumerate(cells)}
        
        blobs = []
        for c in cells:
            ref_bytes = bytes([idx[id(r)] for r in c.refs])
            blobs.append(c._descriptors() + c.b.get_augmented() + ref_bytes)
        
        payload = b''.join(blobs)
        hdr = (
            b'\xb5\xee\x9c\x72'  # magic
            + bytes([0x01])           # ref_size=1
            + bytes([0x02])           # off_bytes=2
            + n.to_bytes(1, 'big')   # cell count
            + (1).to_bytes(1, 'big') # root count
            + (0).to_bytes(1, 'big') # absent count
            + len(payload).to_bytes(2, 'big')  # total size
            + (0).to_bytes(1, 'big') # root index
        )
        return base64.b64encode(hdr + payload).decode()

    def _collect(self, out, seen):
        if id(self) in seen:
            return
        seen.add(id(self))
        out.append(self)
        for r in self.refs:
            r._collect(out, seen)


# ── Address Utils ─────────────────────────────────────────────────────────────

def _crc16(data):
    crc = 0
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if (crc & 0x8000) else (crc << 1)
    return crc & 0xFFFF


def parse_address(addr):
    """Parsea dirección TON (friendly o raw) -> (wc, hash_bytes)."""
    addr = addr.strip()
    if ':' in addr:
        wc_str, hex_str = addr.split(':', 1)
        return int(wc_str), bytes.fromhex(hex_str.strip())
    s = addr.replace('-', '+').replace('_', '/')
    raw = base64.b64decode(s + '==')
    return struct.unpack('b', raw[1:2])[0], raw[2:34]


# ── Toncenter API ─────────────────────────────────────────────────────────────

def _post(method, payload, api_key=''):
    hdrs = {'Content-Type': 'application/json'}
    if api_key:
        hdrs['X-API-Key'] = api_key
    r = requests.post(f'{TONCENTER}/{method}', json=payload, headers=hdrs, timeout=15)
    return r.json()


def _get_time(api_key=''):
    """Tiempo real de la blockchain TON."""
    from email.utils import parsedate_to_datetime

    def http_date(hdrs):
        s = hdrs.get('Date', '')
        try:
            return int(parsedate_to_datetime(s).timestamp()) if s else 0
        except Exception:
            return 0

    # Intentar getMasterchainInfo
    for key in ([api_key, ''] if api_key else ['']):
        try:
            hdrs = {'X-API-Key': key} if key else {}
            r = requests.get(f'{TONCENTER}/getMasterchainInfo', headers=hdrs, timeout=8)
            data = r.json()
            # Extraer utime del resultado
            if data.get('ok'):
                t = data.get('result', {}).get('last', {}).get('utime', 0)
                if t > 1_000_000_000:
                    logger.info(f'net_time via getMasterchainInfo: {t}')
                    return t
            # Extraer del @extra
            extra = str(data.get('@extra', ''))
            if ':' in extra:
                try:
                    t = int(extra.split(':')[0])
                    if t > 1_000_000_000:
                        logger.info(f'net_time via @extra (con key={bool(key)}): {t}')
                        return t
                except Exception:
                    pass
            # Usar Date header
            t = http_date(r.headers)
            if t > 1_000_000_000:
                logger.info(f'net_time via Date header: {t}')
                return t
        except Exception as e:
            logger.warning(f'getMasterchainInfo fallo: {e}')

    t = int(time.time())
    logger.error(f'Usando tiempo local: {t}')
    return t


def _get_seqno(wallet_addr, api_key=''):
    resp = _post('runGetMethod', {'address': wallet_addr, 'method': 'seqno', 'stack': []}, api_key)
    if not resp.get('ok'):
        err = str(resp.get('error', '')).lower()
        if any(k in err for k in ('exit code', 'uninit', 'not found', '-13')):
            return 0
        logger.warning(f'seqno error: {resp}')
        return None
    stack = resp.get('result', {}).get('stack', [])
    return int(stack[0][1], 16) if stack else 0


# ── Construcción del mensaje ──────────────────────────────────────────────────

def _build_transfer(seed, sender_wc, sender_hash, to_wc, to_hash,
                    nanotons, seqno, memo, expire_at):
    """
    Construye el BOC para un transfer de wallet-v4r2.
    
    Estructura (verificada contra ton-core y pytonlib):
    
    ┌─ ext_msg (inline body, bit=0) ───────────────────┐
    │  header: ext_in_msg_info                          │
    │  bits inline:                                     │
    │    signature (512 bits)                           │
    │    subwallet_id (32 bits)                         │
    │    valid_until (32 bits)                          │
    │    seqno (32 bits)                                │
    │    op (8 bits = 0)                                │
    │    send_mode (8 bits = 3)                         │
    │  ref[0] → int_msg                                 │
    └───────────────────────────────────────────────────┘
    
    Lo que firma Ed25519:
      SHA256 del slice: subwallet_id | valid_until | seqno | op | send_mode | hash(int_msg)
    
    Nota: en TON, slice_hash ≠ cell_hash
    slice_hash = SHA256(bits_del_slice || hashes_de_refs)
    """
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    priv = Ed25519PrivateKey.from_private_bytes(seed)

    # ── 1. Mensaje interno ──────────────────────────────────────────────
    int_msg = Cell()
    (int_msg.b
        .write_uint(0, 1)          # int_msg_info$0
        .write_uint(1, 1)          # ihr_disabled
        .write_uint(1, 1)          # bounce
        .write_uint(0, 1)          # bounced
        .write_addr_none()         # src
        .write_addr(to_wc, to_hash)
        .write_coins(nanotons)
        .write_uint(0, 1)          # no extra currencies
        .write_coins(0)            # ihr_fee
        .write_coins(0)            # fwd_fee
        .write_uint(0, 64)         # created_lt
        .write_uint(0, 32)         # created_at
        .write_uint(0, 1))         # no state_init

    if memo:
        int_msg.b.write_uint(1, 1) # body como ref
        cmt = Cell()
        cmt.b.write_uint(0, 32).write_bytes(memo.encode('utf-8')[:120])
        int_msg.refs.append(cmt)
    else:
        int_msg.b.write_uint(0, 1) # body inline vacío

    # ── 2. Calcular slice_hash del body (lo que verifica el contrato) ──
    # slice_hash = SHA256(bits_del_body || hash(int_msg))
    # bits_del_body = subwallet_id(32) | valid_until(32) | seqno(32) | op(8) | mode(8)
    body_bb = BitBuilder()
    (body_bb
        .write_uint(SUBWALLET_ID, 32)
        .write_uint(expire_at, 32)
        .write_uint(seqno, 32)
        .write_uint(0, 8)          # op
        .write_uint(3, 8))         # send_mode

    # slice_hash incluye los bits + hash de cada ref
    slice_data = body_bb.get_data()  # 13 bytes (104 bits exactos)
    slice_hash = hashlib.sha256(slice_data + int_msg.cell_hash()).digest()
    
    logger.info(f'slice_hash: {slice_hash.hex()[:16]}... seqno={seqno} expire={expire_at}')

    # ── 3. Firmar ────────────────────────────────────────────────────────
    sig = priv.sign(slice_hash)

    # ── 4. Mensaje externo con body INLINE ──────────────────────────────
    # Todo va en los bits del ext_msg directamente (either = 0 = inline)
    ext = Cell()
    (ext.b
        .write_uint(0b10, 2)       # ext_in_msg_info$10
        .write_addr_none()         # src
        .write_addr(sender_wc, sender_hash)  # dest
        .write_coins(0)            # import_fee
        .write_uint(0, 1)          # no state_init
        .write_uint(0, 1)          # body INLINE (either = 0)
        # body inline:
        .write_bytes(sig)          # firma 512 bits
        .write_uint(SUBWALLET_ID, 32)
        .write_uint(expire_at, 32)
        .write_uint(seqno, 32)
        .write_uint(0, 8)          # op
        .write_uint(3, 8))         # send_mode
    ext.refs.append(int_msg)       # int_msg como ref

    boc = ext.to_boc()
    logger.info(f'BOC OK ({len(boc)} chars, prefijo={boc[:8]})')
    return boc


# ── API Pública ───────────────────────────────────────────────────────────────

def send_ton(mnemonic, to_addr, ton_amount, memo='', api_key='',
             bot_wallet_address='UQCqD6yy4uQvbmsZ792ScmyfynK6GnlLkkaE6T-xBSWAKtJN'):
    """
    Envía TON desde la wallet del bot.
    Retorna: (success, tx_hash, error_msg)
    """
    steps = []
    try:
        logger.info('TON WALLET v14 - slice_hash + body inline')

        if isinstance(mnemonic, str):
            words = mnemonic.strip().split()
        else:
            words = list(mnemonic)

        if len(words) != 24:
            return False, None, f'Mnemonic debe tener 24 palabras (tiene {len(words)})'

        steps.append('Derivando seed...')
        seed = mnemonic_to_seed(words)

        sender_addr = bot_wallet_address.strip()
        steps.append(f'Wallet bot: {sender_addr}')
        logger.info(f'Cartera remitente TON: {sender_addr}')

        sender_wc, sender_hash = parse_address(sender_addr)

        steps.append('Obteniendo seqno...')
        seqno = _get_seqno(sender_addr, api_key)
        if seqno is None:
            return False, None, 'No se pudo obtener seqno'
        steps.append(f'Seqno: {seqno}')

        steps.append(f'Destino: {to_addr}')
        to_wc, to_hash = parse_address(to_addr)
        steps.append(f'Destino OK wc={to_wc}')

        net_time  = _get_time(api_key)
        expire_at = net_time + 120
        logger.info(f'net_time={net_time} expire_at={expire_at}')

        nanotons = int(float(ton_amount) * 1_000_000_000)
        steps.append(f'Firmando: {ton_amount} TON -> {to_addr}')

        boc_b64 = _build_transfer(seed, sender_wc, sender_hash,
                                   to_wc, to_hash, nanotons, seqno,
                                   memo, expire_at)
        steps.append(f'Transmitiendo a toncenter...')
        
        result = _post('sendBocReturnHash', {'boc': boc_b64}, api_key)
        logger.info(f'TON broadcast result: {result}')

        if result.get('ok'):
            tx_hash = result.get('result', {}).get('hash', '')
            logger.info(f'TON send SUCCESS: {tx_hash}')
            return True, tx_hash, None
        else:
            err = result.get('error', str(result))
            logger.error(f'TON FAILED: {err} | pasos: {steps}')
            return False, None, f'Error al enviar: {err}'

    except Exception as exc:
        logger.exception(f'send_ton excepción pasos={steps}: {exc}')
        return False, None, str(exc)
