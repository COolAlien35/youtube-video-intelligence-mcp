"""B-local synthetic issuer until the shared C fixture arrives."""

import time

import jwt
from cryptography.hazmat.primitives.asymmetric import ec

from yt_intel.server.auth import JwtVerifier


class FakeIssuer:
    def __init__(self):
        self.key = ec.generate_private_key(ec.SECP256R1())
        self.jwk = jwt.algorithms.ECAlgorithm.to_jwk(self.key.public_key(), as_dict=True)
        self.jwk.update(kid="synthetic", alg="ES256")
        self.fetches = 0

    def jwks(self):
        self.fetches += 1
        return {"keys": [self.jwk]}

    def verifier(self):
        return JwtVerifier("https://issuer.example", "authenticated", self.jwks)

    def mint(self, sub="one", kid="synthetic", **claims):
        payload = {
            "iss": "https://issuer.example",
            "aud": "authenticated",
            "exp": int(time.time()) + 90,
            "sub": sub,
        }
        return jwt.encode(payload | claims, self.key, algorithm="ES256", headers={"kid": kid})
