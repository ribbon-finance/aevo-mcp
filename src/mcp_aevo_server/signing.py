from __future__ import annotations

import random
import time
from decimal import Decimal, InvalidOperation
from typing import Any

from eth_account import Account

try:
    from eth_account.messages import encode_structured_data
except Exception:
    encode_structured_data = None

from eth_account.messages import encode_typed_data
from eth_utils import is_address, is_hexstr, to_checksum_address
from eth_utils.crypto import keccak

from .config import AevoNetworkConfig

MAX_UINT256_INT = 2**256 - 1
MAX_UINT256_STR = str(MAX_UINT256_INT)

SCALE = 10**6


EIP712_DOMAIN = [
    {"name": "name", "type": "string"},
    {"name": "version", "type": "string"},
    {"name": "chainId", "type": "uint256"},
]

REGISTER_TYPES = {
    "Register": [
        {"name": "key", "type": "address"},
        {"name": "expiry", "type": "uint256"},
    ],
    "EIP712Domain": EIP712_DOMAIN,
}

SIGN_KEY_TYPES = {
    "SignKey": [{"name": "account", "type": "address"}],
    "EIP712Domain": EIP712_DOMAIN,
}

ORDER_TYPES = {
    "Order": [
        {"name": "maker", "type": "address"},
        {"name": "isBuy", "type": "bool"},
        {"name": "limitPrice", "type": "uint256"},
        {"name": "amount", "type": "uint256"},
        {"name": "salt", "type": "uint256"},
        {"name": "instrument", "type": "uint256"},
        {"name": "timestamp", "type": "uint256"},
    ],
    "EIP712Domain": EIP712_DOMAIN,
}


def _normalize_private_key(private_key: str) -> str:
    if not private_key:
        raise ValueError("missing private key")
    normalized = private_key.lower().removeprefix("0x")
    if len(normalized) != 64:
        raise ValueError("private key must be 32-byte hex")
    if not is_hexstr("0x" + normalized):
        raise ValueError("private key must be hex")
    return "0x" + normalized


def _normalize_address(address: str) -> str:
    if not is_address(address):
        raise ValueError(f"invalid address: {address}")
    return to_checksum_address(address)


def _to_int(value: str, field_name: str) -> int:
    if value is None:
        raise ValueError(f"{field_name} is required")
    if isinstance(value, int):
        out = value
    else:
        try:
            out = int(str(value))
        except Exception as err:
            raise ValueError(f"{field_name} must be integer-like string") from err
    if out < 0:
        raise ValueError(f"{field_name} must be non-negative")
    if out > MAX_UINT256_INT:
        raise ValueError(f"{field_name} exceeds uint256 max")
    return out


def _to_scaled_int(value: str, field_name: str) -> int:
    """Convert a human-readable decimal to a 6-decimal fixed-point integer.

    e.g. "2.86" -> 2860000, "67900" -> 67900000000
    """
    if value is None:
        raise ValueError(f"{field_name} is required")
    try:
        d = Decimal(str(value))
    except (InvalidOperation, ValueError) as err:
        raise ValueError(f"{field_name} must be a valid number") from err
    if not d.is_finite():
        raise ValueError(f"{field_name} must be a finite number")
    scaled = d * SCALE
    if scaled != int(scaled):
        raise ValueError(f"{field_name} exceeds 6 decimal places")
    result = int(scaled)
    if result < 0:
        raise ValueError(f"{field_name} must be non-negative")
    if result > MAX_UINT256_INT:
        raise ValueError(f"{field_name} exceeds uint256 max")
    return result


def _typed_data(
    primary_type: str, types: dict[str, Any], domain: AevoNetworkConfig, message: dict[str, Any]
) -> dict[str, Any]:
    return {
        "types": types,
        "primaryType": primary_type,
        "domain": {
            "name": domain.name,
            "version": "1",
            "chainId": domain.chain_id,
        },
        "message": message,
    }


def _hash_typed_message(typed_data: dict[str, Any]) -> bytes:
    """
    Compute raw EIP-712 hash for Go backend parity.

    We keep this explicit to avoid personal-sign ambiguity; AEVO order verification uses
    raw signature recover against this hash.
    """
    signed = None
    if encode_structured_data is not None:
        try:
            signed = encode_structured_data(typed_data)
        except Exception:
            pass
    if signed is None:
        try:
            signed = encode_typed_data(full_message=typed_data)
        except Exception:
            try:
                signed = encode_typed_data(typed_data)
            except Exception:
                signed = encode_typed_data(
                    domain_data=typed_data["domain"],
                    message_types=typed_data["types"],
                    message_data=typed_data["message"],
                )
    # eth-account SignableMessage implementations commonly expose `body` and `header`.
    body = getattr(signed, "body", None)
    header = getattr(signed, "header", None)
    if body is not None and header is not None:
        body_b = bytes(body)
        header_b = bytes(header)
        return keccak(b"\x19\x01" + header_b + body_b)

    # Fallback for message object variants that include final digest directly.
    direct_hash = getattr(signed, "hash", None)
    if direct_hash is not None:
        if isinstance(direct_hash, str):
            return bytes.fromhex(direct_hash.removeprefix("0x"))
        return bytes(direct_hash)

    raise RuntimeError("Could not derive EIP-712 typed data hash from eth-account message object")


def sign_typed_data(private_key: str, typed_data: dict[str, Any]) -> str:
    hash_bytes = _hash_typed_message(typed_data)
    signature = Account.unsafe_sign_hash(hash_bytes, _normalize_private_key(private_key)).signature
    return signature.hex()


def random_salt() -> int:
    return random.SystemRandom().randrange(1, MAX_UINT256_INT)


def sign_register_payload(
    network: AevoNetworkConfig,
    account_address: str,
    account_private_key: str,
    signing_key_address: str,
    signing_key_private_key: str,
    expiry: str | int | None = None,
) -> dict[str, str]:
    account = _normalize_address(account_address)
    signing_key = _normalize_address(signing_key_address)
    account_sig = sign_typed_data(
        account_private_key,
        _typed_data(
            "SignKey",
            SIGN_KEY_TYPES,
            network,
            {"account": account},
        ),
    )
    expiry_value = _to_int(expiry or MAX_UINT256_STR, "expiry")
    register_sig = sign_typed_data(
        signing_key_private_key,
        _typed_data(
            "Register",
            REGISTER_TYPES,
            network,
            {"key": signing_key, "expiry": expiry_value},
        ),
    )
    return {
        "account_signature": "0x" + account_sig,
        "signing_key_signature": "0x" + register_sig,
    }


def order_typed_message(
    network: AevoNetworkConfig,
    account: str,
    is_buy: bool,
    price: str,
    amount: str,
    instrument_id: str,
    timestamp: int | None = None,
    salt: int | None = None,
) -> dict[str, str]:
    if timestamp is None:
        timestamp = int(time.time())
    typed = _typed_data(
        "Order",
        ORDER_TYPES,
        network,
        {
            "maker": _normalize_address(account),
            "isBuy": bool(is_buy),
            "limitPrice": _to_scaled_int(price, "price"),
            "amount": _to_scaled_int(amount, "amount"),
            "salt": _to_int(str(salt or random_salt()), "salt"),
            "instrument": _to_int(instrument_id, "instrument"),
            "timestamp": int(timestamp),
        },
    )
    return typed


def sign_order_payload(
    network: AevoNetworkConfig,
    account: str,
    is_buy: bool,
    price: str,
    amount: str,
    instrument_id: str,
    signing_key_private_key: str,
    timestamp: int | None = None,
    salt: int | None = None,
    post_only: bool = False,
    reduce_only: bool = False,
    time_in_force: str = "GTC",
    mmp: bool = False,
) -> dict[str, str]:
    typed = order_typed_message(
        network=network,
        account=account,
        is_buy=is_buy,
        price=price,
        amount=amount,
        instrument_id=instrument_id,
        timestamp=timestamp,
        salt=salt,
    )
    typed_sig = sign_typed_data(signing_key_private_key, typed)
    body = typed["message"]
    payload = {
        "maker": to_checksum_address(body["maker"]),
        "is_buy": body["isBuy"],
        "limit_price": str(body["limitPrice"]),
        "amount": str(body["amount"]),
        "instrument": str(body["instrument"]),
        "salt": str(body["salt"]),
        "timestamp": str(body["timestamp"]),
        "signature": "0x" + typed_sig,
        "post_only": bool(post_only),
        "reduce_only": bool(reduce_only),
        "time_in_force": time_in_force.upper() or "GTC",
        "mmp": bool(mmp),
    }
    # Keep backend compatible with default field omission.
    if time_in_force == "GTC":
        payload.pop("time_in_force", None)
    if not post_only:
        payload.pop("post_only", None)
    if not reduce_only:
        payload.pop("reduce_only", None)
    if not mmp:
        payload.pop("mmp", None)
    return payload


def derive_address(private_key: str) -> str:
    return to_checksum_address(Account.from_key(_normalize_private_key(private_key)).address)
