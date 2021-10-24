"""
Unittest coins
"""

from pathlib import Path
from typing import cast

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from spartancoin.transactions import encode_varint, Tx


@pytest.fixture(name="private_key")
def fixture_private_key() -> ec.EllipticCurvePrivateKey:
    """
    Return a repeatable private key for testing.

    Generated by `openssl ecparam -name secp256k1 -genkey -noout -out private.pem`
    """
    with open(Path(__file__).parent / "private.pem", "rb") as f:
        return cast(
            ec.EllipticCurvePrivateKey,
            serialization.load_pem_private_key(f.read(), None),
        )


@pytest.mark.parametrize(
    "i, b",
    [
        (0, b"\x00"),
        (252, b"\xFC"),
        (253, b"\xFD\xFD\x00"),
        (255, b"\xFD\xFF\x00"),
        (0x3419, b"\xFD\x19\x34"),
        (0xDC4591, b"\xFE\x91\x45\xDC\x00"),
        (0x80081E5, b"\xFE\xE5\x81\x00\x08"),
        (0xB4DA564E2857, b"\xFFW(NV\xda\xb4\x00\x00"),
        (0x4BF583A17D59C158, b"\xFFX\xc1Y}\xa1\x83\xf5K"),
    ],
)
def test_encode_varint(i: int, b: bytes) -> None:
    """
    Test the encoding of variable-length integers.

    Test cases taken from https://wiki.bitcoinsv.io/index.php/VarInt
    """
    assert encode_varint(i) == b


@pytest.mark.parametrize("i", [-5, -1, 2 ** 65])
def test_encode_varint_invalid(i: int) -> None:
    """Test variable-length integers are unsigned and can fit in 9 bytes."""
    with pytest.raises(ValueError):
        encode_varint(i)


class TestTx:
    '''Test the Tx class'''

    @staticmethod
    def test_genesis(private_key) -> None:
        """Test the Tx class"""
        coinbase = b"Genesis"
        prev_tx_hash = bytearray(32)
        prev_tx_hash[: len(coinbase)] = coinbase

        observed = Tx(prev_tx_hash, -1, private_key).encode()

        assert observed[:32] == prev_tx_hash
        assert observed[32:36] == b"\xFF\xFF\xFF\xFF"

    @staticmethod
    def test_generic(private_key) -> None:
        """Test the Tx class"""
        tmp = b"not genesis"
        prev_tx_hash = bytearray(32)
        prev_tx_hash[: len(tmp)] = tmp

        observed = Tx(prev_tx_hash, 1, private_key).encode()

        assert observed[:32] == prev_tx_hash
        assert observed[32:36] == b"\x01\x00\x00\x00"
