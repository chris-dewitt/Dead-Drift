"""Regression coverage for visible slingshot rewards."""
from __future__ import annotations


def test_sector_flash_formats_slingshot_credit_breakdown():
    from core.game import _format_slingshot_flash_value

    assert _format_slingshot_flash_value({
        "slingshots": 2,
        "slingshot_credit_each": 800,
        "slingshot_credits": 1600,
    }) == "2 x 800 = +1,600 cr"
    assert _format_slingshot_flash_value({"slingshots": 0}) == "0"
