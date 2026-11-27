from dataclasses import dataclass


@dataclass(frozen=True)
class Principal:
    issuer: str
    subject: str

    def __post_init__(self) -> None:
        if not self.issuer.strip() or not self.subject.strip():
            raise ValueError("Principal requires issuer and subject")
        if "|" in self.issuer:
            raise ValueError("Issuer cannot contain the principal key separator")

    @property
    def key(self) -> str:
        return f"{self.issuer}|{self.subject}"
