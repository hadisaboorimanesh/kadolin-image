# بالای فایل شما همین هست
CARRIER_REGISTRY = {}

def register_carrier(code: str, model_name: str | None = None):
    """
    Decorator to register an adapter model for a given carrier code.

    Usage:
      1) @register_carrier("chapar", "delivery.adapter.chapar")
         class DeliveryAdapterChapar(models.AbstractModel): ...
      2) @register_carrier("chapar")
         class DeliveryAdapterChapar(models.AbstractModel):
             _name = "delivery.adapter.chapar"
    """
    def _decorator(cls):
        name = model_name or getattr(cls, "_name", None)
        if not name:
            raise ValueError(
                "Adapter class must define _name or pass model_name to register_carrier"
            )
        CARRIER_REGISTRY[code] = name
        return cls
    return _decorator