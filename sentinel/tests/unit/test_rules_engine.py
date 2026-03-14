"""Unit tests for the RulesEngine — test every rule and edge case."""

from __future__ import annotations

import pytest

from sentinel.src.services.detection import RulesEngine


@pytest.fixture
def rules() -> RulesEngine:
    """Fresh RulesEngine instance."""
    return RulesEngine()


class TestPhantomDrain:
    """Tests for the Phantom Drain rule."""

    def test_phantom_drain_transfer_detected(self, rules: RulesEngine) -> None:
        """TRANSFER with balance dropping to zero triggers Phantom Drain."""
        violations = rules.check("TRANSFER", 5000, 5000, 0)
        assert "Phantom Drain" in violations

    def test_phantom_drain_cash_out_detected(self, rules: RulesEngine) -> None:
        """CASH_OUT with balance dropping to zero triggers Phantom Drain."""
        violations = rules.check("CASH_OUT", 10000, 10000, 0)
        assert "Phantom Drain" in violations

    def test_phantom_drain_not_triggered_on_payment(self, rules: RulesEngine) -> None:
        """PAYMENT type should NOT trigger Phantom Drain even if balance goes to zero."""
        violations = rules.check("PAYMENT", 5000, 5000, 0)
        assert "Phantom Drain" not in violations

    def test_zero_old_balance_transfer_not_phantom(self, rules: RulesEngine) -> None:
        """If old balance is already zero, Phantom Drain should NOT fire."""
        violations = rules.check("TRANSFER", 0, 0, 0)
        assert "Phantom Drain" not in violations

    def test_partial_drain_not_phantom(self, rules: RulesEngine) -> None:
        """Balance reduction but not to zero should NOT trigger Phantom Drain."""
        violations = rules.check("TRANSFER", 3000, 5000, 2000)
        assert "Phantom Drain" not in violations


class TestMagicMoney:
    """Tests for the Magic Money rule."""

    def test_magic_money_detected(self, rules: RulesEngine) -> None:
        """New balance exceeding old balance + amount triggers Magic Money."""
        violations = rules.check("TRANSFER", 1000, 5000, 7000)
        assert "Magic Money" in violations

    def test_magic_money_not_triggered_on_normal(self, rules: RulesEngine) -> None:
        """Normal transaction where new_balance <= old + amount is clean."""
        violations = rules.check("TRANSFER", 1000, 5000, 4000)
        assert "Magic Money" not in violations

    def test_magic_money_exact_boundary(self, rules: RulesEngine) -> None:
        """Boundary case: new_balance == old_balance + amount + 1.0 is NOT magic."""
        violations = rules.check("TRANSFER", 1000, 5000, 6001.0)
        assert "Magic Money" not in violations

    def test_magic_money_just_over_boundary(self, rules: RulesEngine) -> None:
        """Just over boundary triggers Magic Money."""
        violations = rules.check("TRANSFER", 1000, 5000, 6001.1)
        assert "Magic Money" in violations


class TestLargeValue:
    """Tests for the Large Value rule."""

    def test_large_value_flagged(self, rules: RulesEngine) -> None:
        """Amount > $100k triggers Large Value flag."""
        violations = rules.check("TRANSFER", 150000, 200000, 50000)
        assert "Large Value (>$100k)" in violations

    def test_large_value_threshold_boundary(self, rules: RulesEngine) -> None:
        """Exactly $100k should NOT trigger Large Value (it's >$100k, not >=)."""
        violations = rules.check("TRANSFER", 100000, 200000, 100000)
        assert "Large Value (>$100k)" not in violations


class TestCombinedRules:
    """Tests for multiple rules firing simultaneously."""

    def test_multiple_rules_can_fire_simultaneously(self, rules: RulesEngine) -> None:
        """Phantom Drain + Large Value can fire together."""
        violations = rules.check("TRANSFER", 200000, 200000, 0)
        assert "Phantom Drain" in violations
        assert "Large Value (>$100k)" in violations

    def test_clean_transaction_returns_empty_reasons(self, rules: RulesEngine) -> None:
        """A normal transaction produces no violations."""
        violations = rules.check("PAYMENT", 50, 1000, 950)
        assert violations == []

    def test_all_rules_fire_on_extreme_case(self, rules: RulesEngine) -> None:
        """Extreme case: Phantom Drain + Magic Money cannot co-occur logically,
        but Large Value + Phantom Drain can."""
        violations = rules.check("CASH_OUT", 500000, 500000, 0)
        assert "Phantom Drain" in violations
        assert "Large Value (>$100k)" in violations
        assert len(violations) == 2
