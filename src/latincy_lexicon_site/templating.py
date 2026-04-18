"""Jinja2 environment — single source of truth for template loader."""

from __future__ import annotations

from pathlib import Path

from fastapi.templating import Jinja2Templates

from .principal_parts import format_principal_parts
from .ww_codes import ww_age, ww_area, ww_freq, ww_geo, ww_source

TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

templates.env.filters["ww_age"] = ww_age
templates.env.filters["ww_freq"] = ww_freq
templates.env.filters["ww_area"] = ww_area
templates.env.filters["ww_geo"] = ww_geo
templates.env.filters["ww_source"] = ww_source
templates.env.filters["principal_parts"] = format_principal_parts
