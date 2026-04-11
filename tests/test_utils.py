# tests/test_utils.py
import pytest
from utils import average_from_hd

class TestAverageFromHd:
    def test_basic_dice(self):
        assert average_from_hd('10d12') == 65  # 10*(12+1)//2 = 65

    def test_dice_with_bonus(self):
        assert average_from_hd('1d5+1') == 4   # 1*(5+1)//2 + 1 = 3+1 = 4

    def test_small_die(self):
        assert average_from_hd('2d8') == 9     # 2*(8+1)//2 = 9

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            average_from_hd('invalid')
