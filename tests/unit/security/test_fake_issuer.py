import base64
import json

import pytest
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from tests.support.fake_issuer import FakeIssuer

pytestmark = pytest.mark.unit


def test_jwks_and_claims_are_synthetic(issuer: FakeIssuer) -> None:
    token = issuer.mint("user_alpha", role="FAKE_role")
    header, payload, signature = token.split(".")
    decoded_header = json.loads(base64.urlsafe_b64decode(header + "=="))
    decoded_payload = json.loads(base64.urlsafe_b64decode(payload + "=="))
    assert decoded_header["alg"] == "RS256"
    assert decoded_payload["iss"] == issuer.issuer
    assert decoded_payload["sub"] == "user_alpha"
    assert signature
    assert issuer.jwks["keys"][0]["kid"] == "FAKE_kid_1"


def test_attacker_helpers(issuer: FakeIssuer) -> None:
    assert issuer.expired().split(".")[1]
    assert (
        json.loads(base64.urlsafe_b64decode(issuer.alg_none().split(".")[0] + "=="))["alg"]
        == "none"
    )
    assert issuer.wrong_key() != issuer.mint()


def test_claim_overrides_support_auth_cases(issuer: FakeIssuer) -> None:
    token = issuer.mint(iss="https://wrong.example.invalid", aud="wrong", exp_delta=30)
    assert token.count(".") == 2


def test_published_jwk_verifies_only_issuer_signatures(issuer: FakeIssuer) -> None:
    jwk = issuer.jwks["keys"][0]
    numbers = [int.from_bytes(base64.urlsafe_b64decode(jwk[k] + "=="), "big") for k in ("e", "n")]
    public = rsa.RSAPublicNumbers(*numbers).public_key()
    for token, valid in [(issuer.mint(), True), (issuer.wrong_key(), False)]:
        header, payload, signature = token.split(".")
        args = (
            base64.urlsafe_b64decode(signature + "=="),
            f"{header}.{payload}".encode(),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        if valid:
            public.verify(*args)
        else:
            with pytest.raises(InvalidSignature):
                public.verify(*args)


def test_expired_claim_and_unsigned_signature(issuer: FakeIssuer) -> None:
    import time

    claims = json.loads(base64.urlsafe_b64decode(issuer.expired().split(".")[1] + "=="))
    assert claims["exp"] < time.time()
    assert issuer.alg_none().endswith(".")
