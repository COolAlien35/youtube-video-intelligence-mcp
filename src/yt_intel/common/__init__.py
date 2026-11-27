"""Minimal stubs for yt_intel.common — from D's §0.4 contract.

This module will be replaced by D's full implementation when
feat/common-* branches merge into main. It is a build-unblocking
stub only: all signatures exactly match the §0.4 interface contract.
"""

from .clock import Clock, FakeClock, SystemClock
from .errors import AppError, ErrorCode
from .request_context import get_request_id, new_request_id, request_id_var, set_request_id
from .types import Principal

__all__ = [
    "AppError",
    "Clock",
    "ErrorCode",
    "FakeClock",
    "Principal",
    "SystemClock",
    "get_request_id",
    "new_request_id",
    "request_id_var",
    "set_request_id",
]
