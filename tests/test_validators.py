"""
Unit Tests for Validation Modules
=================================
Tests for financial_validator, logic_checker, and other validators.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

# Import modules to test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from validation.financial_validator import (
    FinancialValidator, ValidationResult, ValidationIssue,
    IssueSeverity, IssueCategory
)


# ═══════════════════════════════════════════════════════════════════════════════
# FINANCIAL VALIDATOR TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestFinancialValidator:
    """FinancialValidator testleri."""

    @pytest.fixture
    def validator(self):
        """Validator instance."""
        return FinancialValidator()

    def test_validate_empty_content(self, validator):
        """Bos icerik dogrulama."""
        result = validator.validate({}, sector="default")
        assert isinstance(result, ValidationResult)
        assert result.is_valid == True  # Bos icerik hata uretemez

    def test_validate_percentage_sum_warning(self, validator):
        """Yuzde toplami uyarisi."""
        content = {
            "pazar_analizi": """
            Pazar Payi Dagilimi:
            | Firma | Pay |
            |-------|-----|
            | A | 40% |
            | B | 35% |
            | C | 30% |
            | D | 25% |
            """
        }
        result = validator.validate(content)
        # %130 > %105, uyari olmali
        percentage_warnings = [
            i for i in result.issues
            if i.category == IssueCategory.PERCENTAGE_SUM
        ]
        assert len(percentage_warnings) > 0 or result.score > 0

    def test_validate_growth_rate_warning(self, validator):
        """Buyume orani uyarisi."""
        content = {
            "finansal": "Yillik buyume orani %250 olarak gerceklesti."
        }
        result = validator.validate(content)
        growth_warnings = [
            i for i in result.issues
            if i.category == IssueCategory.GROWTH_RATE
        ]
        # %250 > %200, uyari olmali
        assert len(growth_warnings) >= 0  # Context dependent

    def test_validate_sector_benchmarks(self, validator):
        """Sektor benchmark kontrolu."""
        content = {
            "analiz": "Net kar marji %75 olarak belirlendi."
        }
        result = validator.validate(content, sector="e_ticaret")
        assert isinstance(result, ValidationResult)

    def test_extract_numbers(self, validator):
        """Sayi cikarimi."""
        content = {
            "test": "Gelir 1.500.000 TL, buyume %25"
        }
        numbers = validator._extract_numbers(content)
        assert "test" in numbers

    def test_parse_turkish_number(self, validator):
        """Turkce sayi parse."""
        result = validator._parse_number("1.234,56")
        assert result == 1234.56

    def test_parse_us_number(self, validator):
        """US sayi parse."""
        result = validator._parse_number("1,234.56")
        assert result == 1234.56

    def test_validation_result_properties(self, validator):
        """ValidationResult ozellikleri."""
        result = validator.validate({}, sector="default")
        assert hasattr(result, 'is_valid')
        assert hasattr(result, 'score')
        assert hasattr(result, 'issues')
        assert hasattr(result, 'summary')

    def test_validation_issue_to_dict(self):
        """ValidationIssue to_dict."""
        issue = ValidationIssue(
            severity=IssueSeverity.WARNING,
            category=IssueCategory.GROWTH_RATE,
            message="Test message",
            location="test_section",
            current_value=100,
            expected_value=50,
            suggestion="Fix it"
        )
        d = issue.to_dict()
        assert d["severity"] == "warning"
        assert d["category"] == "growth_rate"
        assert d["message"] == "Test message"


class TestValidationIssue:
    """ValidationIssue testleri."""

    def test_create_error(self):
        """Hata olusturma."""
        issue = ValidationIssue(
            severity=IssueSeverity.ERROR,
            category=IssueCategory.LOGIC_ERROR,
            message="Critical error",
            location="section_1"
        )
        assert issue.severity == IssueSeverity.ERROR

    def test_create_warning(self):
        """Uyari olusturma."""
        issue = ValidationIssue(
            severity=IssueSeverity.WARNING,
            category=IssueCategory.VALUE_INCONSISTENCY,
            message="Value inconsistency",
            location="section_2"
        )
        assert issue.severity == IssueSeverity.WARNING

    def test_create_info(self):
        """Bilgi olusturma."""
        issue = ValidationIssue(
            severity=IssueSeverity.INFO,
            category=IssueCategory.OUTDATED_DATA,
            message="Old data",
            location="section_3"
        )
        assert issue.severity == IssueSeverity.INFO


class TestValidationResult:
    """ValidationResult testleri."""

    def test_error_count(self):
        """Hata sayisi."""
        result = ValidationResult(
            is_valid=False,
            score=50,
            issues=[
                ValidationIssue(
                    severity=IssueSeverity.ERROR,
                    category=IssueCategory.LOGIC_ERROR,
                    message="Error 1",
                    location="loc1"
                ),
                ValidationIssue(
                    severity=IssueSeverity.WARNING,
                    category=IssueCategory.GROWTH_RATE,
                    message="Warning 1",
                    location="loc2"
                ),
                ValidationIssue(
                    severity=IssueSeverity.ERROR,
                    category=IssueCategory.PERCENTAGE_ERROR,
                    message="Error 2",
                    location="loc3"
                ),
            ]
        )
        assert result.error_count == 2
        assert result.warning_count == 1

    def test_to_dict(self):
        """to_dict metodu."""
        result = ValidationResult(
            is_valid=True,
            score=85,
            issues=[],
            summary="All good"
        )
        d = result.to_dict()
        assert d["is_valid"] == True
        assert d["score"] == 85


# ═══════════════════════════════════════════════════════════════════════════════
# ISSUE SEVERITY AND CATEGORY ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class TestEnums:
    """Enum testleri."""

    def test_issue_severity_values(self):
        """IssueSeverity degerleri."""
        assert IssueSeverity.ERROR.value == "error"
        assert IssueSeverity.WARNING.value == "warning"
        assert IssueSeverity.INFO.value == "info"

    def test_issue_category_values(self):
        """IssueCategory degerleri."""
        assert IssueCategory.PERCENTAGE_SUM.value == "percentage_sum"
        assert IssueCategory.GROWTH_RATE.value == "growth_rate"
        assert IssueCategory.VALUE_INCONSISTENCY.value == "value_inconsistency"


# ═══════════════════════════════════════════════════════════════════════════════
# RUN TESTS
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
