"""AgriConnect machine-learning package.

Shared by the training scripts (ml/train.py, ml/evaluate.py, ml/predict.py) and the
Flask prediction service, so that training and inference use exactly the same
cleaning and feature-generation code.
"""

from .data import REQUIRED_COLUMNS, clean_price_frame, load_price_csv  # noqa: F401
from .features import (  # noqa: F401
    FEATURE_VERSION,
    HORIZONS,
    MIN_HISTORY_WEEKS,
    InsufficientHistoryError,
    build_latest_features,
    build_training_rows,
    to_weekly,
)
