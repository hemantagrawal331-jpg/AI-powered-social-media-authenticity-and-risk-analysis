"""Adapters that map external bot-detection datasets into a canonical record.

These do not download or redistribute restricted corpora. Point them at files
you already have a license to use.

Licensing:
- TwiBot-20 / TwiBot-22: request from the dataset authors. Do not commit dumps here.
- Cresci-2015/2017: academic license from the original paper authors.
- Generic CSV: you are responsible for the rights to any file you pass in.
"""

from app.ml.adapters import cresci_adapter, generic_csv_adapter, synthetic_adapter, twibot_adapter

__all__ = [
    "cresci_adapter",
    "generic_csv_adapter",
    "synthetic_adapter",
    "twibot_adapter",
]
