from services.payments.base import PaymentProvider

_providers: dict[str, PaymentProvider] = {}


def get_provider(name: str) -> PaymentProvider:
    if name not in _providers:
        if name == "paypal":
            from services.payments.paypal import PayPalProvider
            _providers[name] = PayPalProvider()
        else:
            raise ValueError(f"Fournisseur de paiement inconnu : '{name}'")
    return _providers[name]
