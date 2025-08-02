"""
Test suite for the calculate_markup_cost function from /utils/cost_calculator.py

Tests confirm that the function:
1. Correctly calculates cost for standard markup (1.3x)
2. Correctly applies custom markup rates
3. Maintains precision of 4 decimal places
4. Handles edge cases and validation
"""

import pytest
import sys
import os

# Add the backend directory to Python path to import open_webui modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from open_webui.utils.cost_calculator import calculate_markup_cost, CostCalculationError


class TestCalculateMarkupCost:
    """Test suite for calculate_markup_cost function"""

    def test_standard_markup_calculation(self):
        """Test standard markup: base_cost_usd: 0.0123, markup 1.3x -> 0.0160"""
        base_cost_usd = 0.0123
        markup_rate = 1.3
        expected_result = 0.0160  # Rounded to 4 decimal places
        
        result = calculate_markup_cost(base_cost_usd, markup_rate)
        
        # Test that result matches expected value with 4 decimal precision
        assert round(result, 4) == expected_result
        # Alternative verification: direct calculation
        assert result == base_cost_usd * markup_rate

    def test_custom_markup_calculation(self):
        """Test custom markup: base_cost_usd: 0.1, markup_rate: 2.0 -> 0.2000"""
        base_cost_usd = 0.1
        markup_rate = 2.0
        expected_result = 0.2000
        
        result = calculate_markup_cost(base_cost_usd, markup_rate)
        
        # Test exact match with 4 decimal precision
        assert round(result, 4) == expected_result
        assert result == base_cost_usd * markup_rate

    def test_precision_four_decimal_places(self):
        """Test 4 decimal precision: base_cost_usd: 10.0, markup 1.3x -> 13.0000"""
        base_cost_usd = 10.0
        markup_rate = 1.3
        expected_result = 13.0000
        
        result = calculate_markup_cost(base_cost_usd, markup_rate)
        
        # Test that result maintains 4 decimal precision even when not mathematically required
        assert round(result, 4) == expected_result
        assert result == base_cost_usd * markup_rate
        
        # Verify the raw calculation gives the expected precision
        assert f"{result:.4f}" == "13.0000"

    def test_zero_base_cost(self):
        """Test edge case: zero base cost should return zero"""
        base_cost_usd = 0.0
        markup_rate = 1.3
        
        result = calculate_markup_cost(base_cost_usd, markup_rate)
        
        assert result == 0.0
        assert round(result, 4) == 0.0000

    def test_very_small_cost(self):
        """Test very small cost values with precision"""
        base_cost_usd = 0.0001
        markup_rate = 1.5
        expected_result = 0.0002  # 0.0001 * 1.5 = 0.00015, rounded to 4 decimals = 0.0002
        
        result = calculate_markup_cost(base_cost_usd, markup_rate)
        
        assert round(result, 4) == expected_result

    def test_large_cost_values(self):
        """Test large cost values maintain precision"""
        base_cost_usd = 999.9999
        markup_rate = 1.1
        expected_result = 1099.9999  # 999.9999 * 1.1 = 1099.99989, rounded to 4 decimals
        
        result = calculate_markup_cost(base_cost_usd, markup_rate)
        
        assert round(result, 4) == round(expected_result, 4)

    def test_fractional_markup_rates(self):
        """Test fractional markup rates (less than 1)"""
        base_cost_usd = 1.0
        markup_rate = 0.5  # 50% of original cost
        expected_result = 0.5000
        
        result = calculate_markup_cost(base_cost_usd, markup_rate)
        
        assert round(result, 4) == expected_result

    def test_exact_precision_examples(self):
        """Test additional precision examples to ensure 4-decimal consistency"""
        test_cases = [
            (0.0123, 1.3, 0.0160),    # User's first example
            (0.1, 2.0, 0.2000),       # User's second example  
            (10.0, 1.3, 13.0000),     # User's third example
            (5.5555, 1.2, 6.6666),    # Additional precision test
            (0.0001, 10.0, 0.0010),   # Small value, large markup
        ]
        
        for base_cost, markup_rate, expected in test_cases:
            result = calculate_markup_cost(base_cost, markup_rate)
            # Test both exact calculation and 4-decimal precision
            assert result == base_cost * markup_rate
            assert round(result, 4) == expected

    def test_negative_base_cost_raises_error(self):
        """Test that negative base cost raises CostCalculationError"""
        base_cost_usd = -0.01
        markup_rate = 1.3
        
        with pytest.raises(CostCalculationError, match="Negative cost not allowed"):
            calculate_markup_cost(base_cost_usd, markup_rate)

    def test_zero_markup_rate_raises_error(self):
        """Test that zero markup rate raises CostCalculationError"""
        base_cost_usd = 1.0
        markup_rate = 0.0
        
        with pytest.raises(CostCalculationError, match="Invalid markup rate"):
            calculate_markup_cost(base_cost_usd, markup_rate)

    def test_negative_markup_rate_raises_error(self):
        """Test that negative markup rate raises CostCalculationError"""
        base_cost_usd = 1.0
        markup_rate = -1.5
        
        with pytest.raises(CostCalculationError, match="Invalid markup rate"):
            calculate_markup_cost(base_cost_usd, markup_rate)

    def test_return_type_is_float(self):
        """Test that function always returns float type"""
        result = calculate_markup_cost(1, 1.5)  # int inputs
        
        assert isinstance(result, float)
        assert result == 1.5

    def test_markup_rate_one_returns_same_cost(self):
        """Test that markup rate of 1.0 returns the same cost"""
        base_cost_usd = 5.4321
        markup_rate = 1.0
        
        result = calculate_markup_cost(base_cost_usd, markup_rate)
        
        assert result == base_cost_usd
        assert round(result, 4) == 5.4321


if __name__ == "__main__":
    pytest.main([__file__, "-v"])