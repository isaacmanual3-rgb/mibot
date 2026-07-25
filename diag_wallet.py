#!/usr/bin/env python3
"""
diag_wallet.py — Compara la direccion configurada contra la que
realmente controla el mnemonic, y muestra el saldo de cada una.

El chequeo de fondos usa la direccion de la CONFIG, pero quien firma
y envia es el MNEMONIC. Si no coinciden, el chequeo mira una wallet
equivocada: puede reportar 0 TON aunque la wallet real tenga saldo.

Uso:  cd /var/www/aeroflex && ./venv/bin/python diag_wallet.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))

from ton_wallet import get_wallet_balance, TON_TO_NANO

print("=" * 60)
print(" DIAGNOSTICO DE WALLET DEL BOT")
print("=" * 60)

api_key = os.getenv('TONCENTER_API_KEY', '')
print(f"\nTONCENTER_API_KEY: {'configurada (' + api_key[:8] + '...)' if api_key else 'NO configurada'}")

# ── 1. Direccion en la base de datos (config)
addr_db = None
try:
    from database import get_config
    addr_db = get_config('ton_bot_wallet_address', '') or None
except Exception as e:
    print(f"\n[!] No se pudo leer la config de la BD: {e}")

# ── 2. Direccion en el .env
addr_env = os.getenv('TON_BOT_WALLET_ADDRESS', '') or None

# ── 3. Direccion REAL derivada del mnemonic
addr_real = None
mnemonic = os.getenv('TON_BOT_MNEMONIC', '')
try:
    from database import get_config as _gc
    mnemonic = _gc('ton_bot_mnemonic', '') or mnemonic
except Exception:
    pass

if mnemonic and len(mnemonic.split()) == 24:
    try:
        import asyncio
        from tonutils.clients import ToncenterClient
        from tonutils.contracts.wallet import WalletV5R1

        async def _derivar():
            client = None
            try:
                from ton_core import NetworkGlobalID
                client = ToncenterClient(NetworkGlobalID.MAINNET, api_key=api_key or None)
            except Exception:
                try:
                    client = ToncenterClient(api_key=api_key, is_testnet=False)
                except TypeError:
                    client = ToncenterClient(api_key=api_key)
            async with client:
                r = WalletV5R1.from_mnemonic(client, mnemonic.split())
                if asyncio.iscoroutine(r):
                    r = await r
                w = r[0] if isinstance(r, (tuple, list)) else r
                return str(w.address)

        addr_real = asyncio.new_event_loop().run_until_complete(_derivar())
    except Exception as e:
        print(f"\n[!] No se pudo derivar la direccion del mnemonic: {e}")
else:
    print(f"\n[!] Mnemonic ausente o invalido ({len(mnemonic.split())} palabras, se esperan 24)")

# ── Reporte
print("\n" + "-" * 60)
print(" DIRECCIONES")
print("-" * 60)
print(f"En la BD (config):   {addr_db or '(vacia)'}")
print(f"En el .env:          {addr_env or '(vacia)'}")
print(f"REAL del mnemonic:   {addr_real or '(no se pudo derivar)'}")

# Cual usa el codigo actualmente: get_config primero, luego env
addr_usada = addr_db or addr_env
print(f"\n>> La que USA el chequeo de fondos: {addr_usada or '(ninguna)'}")

if addr_real and addr_usada:
    if addr_real.strip() == addr_usada.strip():
        print(">> COINCIDEN. El chequeo mira la wallet correcta.")
    else:
        print(">> !! NO COINCIDEN !!")
        print("   El chequeo consulta una wallet que NO es la que envia.")
        print("   Por eso puede reportar 0 TON aunque hayas recargado.")

# ── Saldos
print("\n" + "-" * 60)
print(" SALDOS ON-CHAIN")
print("-" * 60)
vistas = []
for etiqueta, addr in (("BD/config", addr_db), (".env", addr_env), ("mnemonic (REAL)", addr_real)):
    if not addr or addr in vistas:
        continue
    vistas.append(addr)
    saldo, err = get_wallet_balance(addr, api_key)
    if saldo is None:
        print(f"{etiqueta:18s} {addr[:20]}...  ERROR: {err}")
    else:
        print(f"{etiqueta:18s} {addr[:20]}...  {saldo:.6f} TON")

print("\n" + "=" * 60)
if addr_real and addr_usada and addr_real.strip() != addr_usada.strip():
    print(" ACCION: pon la direccion REAL del mnemonic en la config")
    print(" (panel admin) o en TON_BOT_WALLET_ADDRESS del .env.")
else:
    print(" Si el saldo real sigue en 0, revisa que recargaste esa")
    print(" direccion exacta y que la transaccion ya se confirmo.")
print("=" * 60)
