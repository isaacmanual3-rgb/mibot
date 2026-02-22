"""
ton_wallet.py — v5
Envío automático TON (wallet-v4r2). Sin deps externas.
Solo: stdlib + cryptography + requests (todos preinstalados en PythonAnywhere).

FIXES vs versiones anteriores:
  - BOC header correcto: ref_byte_size=1, offset_byte_size=2
  - Ref indices como 1 byte (no 4 bytes)
  - friendly_to_raw acepta formato raw "0:hexhash" que envía TON Connect
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
        """VarUInteger 16 — coin amount."""
        if n == 0:
            return self.uint(0, 4)
        byte_len = (n.bit_length() + 7) // 8
        self.uint(byte_len, 4)
        self.uint(n, byte_len * 8)
        return self

    def addr_std(self, wc, h):
        """MsgAddressInt addr_std."""
        self.uint(0b10, 2)   # tag
        self._bit(0)          # anycast=None
        self.int_(wc, 8)
        self.raw(h)
        return self

    def addr_none(self):
        return self.uint(0b00, 2)

    @property
    def bit_len(self): return self._n

    def augmented(self):
        """Bytes with stop-bit if not byte-aligned."""
        buf = bytearray(self._d)
        if self._n % 8:
            buf[-1] |= 1 << (7 - self._n % 8)
        return bytes(buf)


# ══════════════════════════════════════════════════════════════
#  CELL + BOC SERIALISER
# ══════════════════════════════════════════════════════════════

class Cell:
    def __init__(self):
        self.b    = _BB()
        self.refs = []

    def _desc(self):
        full = self.b.bit_len // 8
        part = 1 if self.b.bit_len % 8 else 0
        return bytes([len(self.refs), full * 2 + part])

    def hash(self):
        return hashlib.sha256(
            self._desc() + self.b.augmented() +
            b''.join(r.hash() for r in self.refs)
        ).digest()

    def boc_b64(self):
        """
        Serialize to base64 BOC.
        Header format (verified against real TON transactions):
          magic(4) | flags(1) | offset_sz(1) | cells_n(1) | roots_n(1) |
          absent(1) | total_sz(offset_sz bytes) | root_idx(1)
        flags = 0x01 → ref_byte_size=1
        offset_sz = 0x02 → total_cells_size in 2 bytes
        """
        cells = []
        self._collect(cells, set())
        n   = len(cells)
        idx = {id(c): i for i, c in enumerate(cells)}

        blobs = []
        for c in cells:
            # ref indices as 1-byte each (ref_byte_size=1)
            ref_b = bytes([idx[id(r)] for r in c.refs])
            blobs.append(c._desc() + c.b.augmented() + ref_b)

        payload = b''.join(blobs)
        total   = len(payload)

        hdr = (
            b'\xb5\xee\x9c\x72'       # magic
            + bytes([0x01])             # flags: ref_byte_size = 1
            + bytes([0x02])             # offset_byte_size = 2
            + n.to_bytes(1, 'big')      # cells_num
            + (1).to_bytes(1, 'big')    # roots_num = 1
            + (0).to_bytes(1, 'big')    # absent_num = 0
            + total.to_bytes(2, 'big')  # total_cells_size (2 bytes)
            + (n - 1).to_bytes(1, 'big')  # root index (last collected = root)
        )
        return base64.b64encode(hdr + payload).decode()

    def _collect(self, out, seen):
        if id(self) in seen:
            return
        seen.add(id(self))
        for r in self.refs:
            r._collect(out, seen)
        out.append(self)   # root is appended last → index n-1


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
    """
    Parsea CUALQUIER formato de dirección TON:
      "0:69e30859..."    → raw hex (formato de TON Connect)
      "-1:abcdef..."     → raw hex workchain negativo
      "EQD2NmD_..."      → base64url friendly (48 chars)
      "UQBkIKoV..."      → base64url friendly (47 chars)
    Retorna (workchain: int, hash: bytes[32])
    """
    addr = addr.strip()

    # Formato raw "workchain:hexhash64" — lo que devuelve TON Connect
    if ':' in addr:
        wc_str, hex_str = addr.split(':', 1)
        wc      = int(wc_str)
        hex_str = hex_str.strip()
        if len(hex_str) != 64:
            raise ValueError(f'Raw TON address debe tener 64 hex chars: {addr!r}')
        return wc, bytes.fromhex(hex_str)

    # Formato friendly base64url EQ.../UQ...
    s       = addr.replace('-', '+').replace('_', '/')
    padding = (4 - len(s) % 4) % 4   # padding dinámico
    raw     = base64.b64decode(s + '=' * padding)
    if len(raw) < 34:
        raise ValueError(f'Dirección TON inválida: {addr!r}')
    return struct.unpack('b', raw[1:2])[0], raw[2:34]


def _pub_to_addr(pub):
    """Deriva dirección wallet-v4r2 desde clave pública Ed25519."""
    CODE_HASH = bytes.fromhex(
        'fe9530d3243253bd5f7e4b9b7b3eb9843765c37b0b2c68944fced5e7f3e2fc3d'
    )
    data = Cell()
    data.b.uint(0, 32).uint(SUBWALLET_ID, 32).raw(pub).uint(0, 1)
    code = Cell()
    code.b.raw(CODE_HASH)
    si = Cell()
    si.b.uint(0, 2).uint(1, 1).uint(1, 1).uint(0, 1)
    si.refs = [code, data]
    return 0, si.hash()


def _addr_friendly(wc, h):
    """Codifica como EQ... (bounceable, mainnet)."""
    wc_byte = struct.pack('b', wc)
    prefix  = bytes([0x11]) + wc_byte + h
    crc     = _crc16xmodem(prefix)
    raw     = prefix + bytes([crc >> 8, crc & 0xFF])
    return base64.urlsafe_b64encode(raw).decode().rstrip('=')


# ══════════════════════════════════════════════════════════════
#  MNEMONIC → CLAVE PRIVADA
# ══════════════════════════════════════════════════════════════

def mnemonic_to_key(words):
    """Deriva 32-byte Ed25519 seed desde mnemonic TON (24 palabras)."""
    if isinstance(words, str):
        words = words.strip().split()
    entropy = ' '.join(words).encode('utf-8')
    return hashlib.pbkdf2_hmac('sha512', entropy, b'TON default seed', 100000)[:32]


# ══════════════════════════════════════════════════════════════
#  CONSTRUIR BOC FIRMADO (wallet-v4r2)
# ══════════════════════════════════════════════════════════════

def _build_boc(priv_bytes, to_wc, to_hash, nanotons, seqno, memo, expire_at):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

    priv = Ed25519PrivateKey.from_private_bytes(priv_bytes)
    pub  = priv.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)

    # Mensaje interno
    int_msg = Cell()
    (int_msg.b
        .uint(1, 1)                  # ihr_disabled
        .uint(1, 1)                  # bounce
        .uint(0, 1)                  # bounced=0
        .addr_none()                 # src = addr_none
        .addr_std(to_wc, to_hash)   # dest
        .grams(nanotons)             # value
        .uint(0, 1)                  # no extra currencies
        .grams(0).grams(0)          # ihr_fee, fwd_fee
        .uint(0, 64).uint(0, 32)    # created_lt, created_at
        .uint(0, 1)                  # no state_init
        .uint(0, 1))                 # body inline

    if memo:
        cmt = Cell()
        cmt.b.uint(0, 32).raw(memo.encode('utf-8')[:120])
        int_msg.refs.append(cmt)

    # Cuerpo wallet-v4r2
    body = Cell()
    (body.b
        .uint(SUBWALLET_ID, 32)
        .uint(expire_at, 32)
        .uint(seqno, 32)
        .uint(0, 8)                  # op = simple send
        .uint(3, 8))                 # send_mode = 3
    body.refs.append(int_msg)

    # Firmar
    sig = priv.sign(body.hash())

    # Mensaje externo
    s_wc, s_hash = _pub_to_addr(pub)
    ext = Cell()
    (ext.b
        .uint(0b10, 2)
        .addr_none()
        .addr_std(s_wc, s_hash)
        .grams(0)
        .uint(0, 1)
        .uint(1, 1))

    signed = Cell()
    signed.b.raw(sig)
    signed.refs.append(body)
    ext.refs.append(signed)

    return ext.boc_b64()


# ══════════════════════════════════════════════════════════════
#  TONCENTER API
# ══════════════════════════════════════════════════════════════

def _tc_post(method, payload, api_key=''):
    hdrs = {'Content-Type': 'application/json'}
    if api_key:
        hdrs['X-API-Key'] = api_key
    r = requests.post(f'{TONCENTER}/{method}', json=payload, headers=hdrs, timeout=15)
    return r.json()


def _get_seqno(wallet_addr, api_key=''):
    resp = _tc_post('runGetMethod',
                    {'address': wallet_addr, 'method': 'seqno', 'stack': []},
                    api_key=api_key)
    if not resp.get('ok'):
        err = str(resp.get('error', '')).lower()
        # Wallet no desplegada = seqno 0
        if any(k in err for k in ('exit code', 'uninit', 'not found', '-13')):
            return 0
        logger.warning(f'seqno failed: {resp}')
        return None
    stack = resp.get('result', {}).get('stack', [])
    return int(stack[0][1], 16) if stack else 0


# ══════════════════════════════════════════════════════════════
#  FUNCIÓN PÚBLICA
# ══════════════════════════════════════════════════════════════

def send_ton(mnemonic, to_addr, ton_amount, memo='', api_key=''):
    """
    Envía TON desde la wallet del bot a to_addr.

    to_addr acepta:
      - "0:69e308..."   (raw, lo que devuelve TON Connect)
      - "EQ..." / "UQ..." (friendly)

    Retorna: (success: bool, tx_hash: str|None, error: str|None)
    """
    steps = []
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

        steps.append('Derivando clave...')
        priv_bytes = mnemonic_to_key(mnemonic)
        priv = Ed25519PrivateKey.from_private_bytes(priv_bytes)
        pub  = priv.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)

        s_wc, s_hash = _pub_to_addr(pub)
        sender_addr  = _addr_friendly(s_wc, s_hash)
        steps.append(f'Wallet bot: {sender_addr}')
        logger.info(f'TON sender wallet: {sender_addr}')

        steps.append('Obteniendo seqno...')
        seqno = _get_seqno(sender_addr, api_key)
        if seqno is None:
            err = 'No se pudo obtener seqno. La wallet del bot debe tener TON y estar desplegada.'
            logger.error(f'TON send FAILED (seqno): {err}')
            return False, None, err
        steps.append(f'Seqno: {seqno}')

        steps.append(f'Parseando destino: {to_addr}')
        to_wc, to_hash = friendly_to_raw(to_addr)
        steps.append(f'Destino OK wc={to_wc}')

        expire_at = int(time.time()) + 600
        nanotons  = int(ton_amount * 1_000_000_000)
        steps.append(f'Firmando BOC: {ton_amount} TON')
        boc_b64 = _build_boc(priv_bytes, to_wc, to_hash, nanotons, seqno, memo, expire_at)
        steps.append(f'BOC OK ({len(boc_b64)} chars, prefix={boc_b64[:8]})')

        steps.append('Transmitiendo a toncenter...')
        result = _tc_post('sendBocReturnHash', {'boc': boc_b64}, api_key=api_key)
        logger.info(f'TON broadcast: {result}')

        if result.get('ok'):
            tx_hash = result.get('result', {}).get('hash', '')
            steps.append(f'TX OK: {tx_hash}')
            logger.info(f'TON send SUCCESS: {tx_hash}')
            return True, tx_hash, None
        else:
            err = result.get('error', str(result))
            steps.append(f'Broadcast error: {err}')
            logger.error(f'TON broadcast FAILED: {err} | steps: {steps}')
            return False, None, f'Error al enviar: {err}'

    except Exception as exc:
        steps.append(f'EXCEPCION: {exc}')
        logger.exception(f'send_ton EXCEPTION steps={steps}: {exc}')
        return False, None, str(exc)
