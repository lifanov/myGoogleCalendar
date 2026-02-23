import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add v2 to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import functions

class TestFunctions(unittest.TestCase):

    def test_get_current_timezone_offset_format(self):
        # Check if the output format is correct for the current env.
        offset = functions.get_current_timezone_offset()
        # Should be like "+HH:MM" or "-HH:MM"
        self.assertRegex(offset, r"^[+-]\d{2}:\d{2}$")

    @patch('functions.datetime')
    def test_timezone_formatting(self, mock_datetime):
        # Create a mock datetime object that returns a specific strftime result
        mock_now = MagicMock()
        # We need to mock datetime.datetime.now().astimezone()
        mock_datetime.datetime.now.return_value.astimezone.return_value = mock_now

        # Test +0530
        mock_now.strftime.return_value = "+0530"
        result = functions.get_current_timezone_offset()
        self.assertEqual(result, "+05:30")

        # Test -0500
        mock_now.strftime.return_value = "-0500"
        result = functions.get_current_timezone_offset()
        self.assertEqual(result, "-05:00")

        # Test +0000
        mock_now.strftime.return_value = "+0000"
        result = functions.get_current_timezone_offset()
        self.assertEqual(result, "+00:00")

if __name__ == '__main__':
    unittest.main()
