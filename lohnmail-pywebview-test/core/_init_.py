# core/__init__.py
from .config import (
    BASE_DIR,
    APP_NAME,
    APP_TAGLINE,
    APP_COPYRIGHT,
    DEVELOPER_NAME,
    SUPPORT_EMAIL,
    DSGVO_CLAIM,
    ensure_default_config,
    load_settings,
    save_settings,
)

from .excel_io import (
    normalize_persnr,
    load_email_records,
    load_email_map,
)

from .input_scan import (
    scan_pdf_folder,
)
