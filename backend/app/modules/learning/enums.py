# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Enumerations for Learning Materials and Socratic AI bounded context."""

from enum import Enum


class MaterialType(str, Enum):
    """Supported digital learning material format types."""

    SLIDE = "SLIDE"
    PDF = "PDF"
    VIDEO = "VIDEO"
    DOCUMENT = "DOCUMENT"
