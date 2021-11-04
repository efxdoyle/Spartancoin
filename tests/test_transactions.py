"""
Unittest coins
"""

import random
from pathlib import Path
from typing import cast

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from spartancoin.transactions import (
    decode_varint,
    DecodeError,
    encode_varint,
    Receiver,
    Sender,
)


@pytest.fixture(name="private_key")
def fixture_private_key() -> ec.EllipticCurvePrivateKey:
    """
    Return a repeatable private key for testing.

    Generated by `openssl ecparam -name secp256k1 -genkey -noout -out private.pem`
    or by `ec.generate_private_key(ec.SECP256K1())`.
    """
    with open(Path(__file__).parent / "private.pem", "rb") as f:
        return cast(
            ec.EllipticCurvePrivateKey,
            serialization.load_pem_private_key(f.read(), None),
        )


class TestVarInt:
    """Test variable-length encoded integers"""

    @staticmethod
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
    def test_encode_decode(i: int, b: bytes) -> None:
        """
        Test the encoding of variable-length integers.

        Test cases taken from https://wiki.bitcoinsv.io/index.php/VarInt
        """
        assert encode_varint(i) == b
        assert decode_varint(b) == i

    @staticmethod
    @pytest.mark.parametrize("i", [-5, -1, 2 ** 65])
    def test_encode_errors(i: int) -> None:
        """Test variable-length integers are unsigned and can fit in 9 bytes."""
        with pytest.raises(ValueError):
            encode_varint(i)

    @staticmethod
    @pytest.mark.parametrize(
        "b",
        [
            b"",
            b"\xFC-",
            b"\xFD\xFF",
            b"\xFD\x19\x34==",
            b"\xFFW(NV\xda\xb4\x00",
            b"\xFFX\xc1Y}\xa1\x83\xf5K=",
        ],
    )
    def test_decode_errors(b: bytes) -> None:
        """
        Invalid encodings should raise.
        """
        with pytest.raises(ValueError):
            decode_varint(b)


class TestTx:
    """Test the `Sender` class"""

    @staticmethod
    def test_genesis(private_key) -> None:
        """Test the Sender class"""
        coinbase = b"Genesis"
        prev_tx_hash = bytearray(32)
        prev_tx_hash[: len(coinbase)] = coinbase

        observed = Sender.from_prk(prev_tx_hash, -1, private_key).encode()

        assert observed[:32] == prev_tx_hash
        assert observed[32:36] == b"\xFF\xFF\xFF\xFF"

    @staticmethod
    def test_generic(private_key) -> None:
        """Test the Sender class"""
        tmp = b"not genesis"
        prev_tx_hash = bytearray(32)
        prev_tx_hash[: len(tmp)] = tmp

        observed = Sender.from_prk(prev_tx_hash, 1, private_key).encode()

        assert observed[:32] == prev_tx_hash
        assert observed[32:36] == b"\x01\x00\x00\x00"

    @staticmethod
    @pytest.mark.parametrize(
        "tx",
        [
            Sender(
                bytearray(random.randrange(1 << 8) for _ in range(32)),
                random.randrange(1 << 32),
                bytearray(
                    random.randrange(1 << 8) for _ in range(random.randrange(80))
                ),
                ec.generate_private_key(ec.SECP256K1()).public_key(),
            )
            for _ in range(10)
        ],
    )
    def test_encode_decode(tx) -> None:
        """Test encoding and decoding are inverses"""
        encoded = tx.encode()
        decoded = Sender.from_bytes(encoded)
        assert decoded == tx

    @staticmethod
    def test_decode_raises() -> None:
        """Test decoding invalid representations raise"""
        with pytest.raises(DecodeError) as excinfo:
            Sender.from_bytes(b"-")
        assert "invalid length" in excinfo.value.args

        encoded = (
            b"\xe4\xf1<\x9em\xf4\xe4f\x1a\x8e\xe0\x8a\x89\xe3\x0e\xc8|\xbeia\xb9"
            b"\xcc\xfe\xfc\xbe\xb9H+\x8e\x17\xfb\xd8\xedv\xc3\xc5\x9c\xf7kTO\xf8"
            b"\xc128\xfc\xd4\xff\xc3\x9c\xa8\xf2\x93\x8c\xe5\xf8\xfcB\xf5a\xe4/*"
            b"c8\x8e\x8e\x93Z\xdaq\x18F\x0c|\x03K?\xd9\xb0c\x1at\xf3g\xcf\xa4|"
            b"\xfe\xa5\x80\xf6\x03K%\x1a%\x02\xbb\x92Nt\xa5\xf5\xea0V0\x10\x06"
            b"\x07*\x86H\xce=\x02\x01\x06\x05+\x81\x04\x00\n\x03B\x00\x04\x93)"
            b"\xa0\xb4\xde)\x99J_\xb4\xe3K\x11\x91\x9c\x15\xa4+\x8bp\nQ\xdd\xa1"
            b"\xbb\xfb\xe8%\xa7\x91\x84\x05\xdd)$l\xce\xb7\x0b\xcd\xcc\xe1\xdd"
            b"\xbcS\xd70O\xcc~\xd1\x97s\x8d\xde\xe8$\xb2`\xef\x0f\xec\xaf\x90"
        )
        assert Sender.from_bytes(encoded)
        with pytest.raises(DecodeError) as excinfo:
            Sender.from_bytes(encoded + b"-")
        assert "invalid length" in excinfo.value.args
        with pytest.raises(DecodeError) as excinfo:
            Sender.from_bytes(encoded[:-1])
        assert "invalid length" in excinfo.value.args


class TestRx:
    """Test the `Receiver` class"""

    @staticmethod
    @pytest.mark.parametrize(
        "rx",
        [
            Receiver(43, ec.generate_private_key(ec.SECP256K1()).public_key())
            for _ in range(10)
        ],
    )
    def test_encode_decode(rx) -> None:
        """Test encoding and decoding are inverses"""
        encoded = rx.encode()
        decoded = Receiver.from_bytes(encoded)
        assert decoded == rx

    @staticmethod
    def test_decode_raises() -> None:
        """Test decoding invalid representations raise"""
        with pytest.raises(DecodeError) as excinfo:
            Receiver.from_bytes(8 * b"-" + 3 * b"\xff")
        assert "invalid varint" in excinfo.value.args
        with pytest.raises(DecodeError) as excinfo:
            Receiver.from_bytes(b"-")
        assert "invalid length" in excinfo.value.args

        encoded = (
            b"+\x00\x00\x00\x00\x00\x00\x00X0V0\x10\x06\x07*\x86H\xce=\x02\x01"
            b"\x06\x05+\x81\x04\x00\n\x03B\x00\x04\rp\xad\xdc\xa7\x88\xc9#0\xad"
            b"Jd \xf1J+FW\x81sg\xc4U\xe6\x19\xadwF8\x94\x0fcM>!\xd3\xed\x96\xf0"
            b"\x9e\xae\x1eKF\x0e\xc7\r\x9d\x1e\xf2PoPiv\xb9.\\i\x84\x94\xf4Q\x1f"
        )
        assert Receiver.from_bytes(encoded)
        with pytest.raises(DecodeError) as excinfo:
            Receiver.from_bytes(encoded + b"-")
        assert "invalid length" in excinfo.value.args
        with pytest.raises(DecodeError) as excinfo:
            Receiver.from_bytes(encoded[:-1])
        assert "invalid length" in excinfo.value.args
