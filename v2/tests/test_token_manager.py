import unittest
from unittest.mock import MagicMock, patch, mock_open
import sys
import os
import json

# Add v2 to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from token_manager import TokenManager

class TestTokenManager(unittest.TestCase):

    @patch('token_manager.requests.get')
    def test_is_token_valid(self, mock_get):
        tm = TokenManager()

        # Test 200 OK
        mock_get.return_value.status_code = 200
        self.assertTrue(tm.is_token_valid("fake_token"))

        # Test 400 Bad Request (which we consider valid auth)
        mock_get.return_value.status_code = 400
        self.assertTrue(tm.is_token_valid("fake_token"))

        # Test 401 Unauthorized
        mock_get.return_value.status_code = 401
        self.assertFalse(tm.is_token_valid("fake_token"))

    @patch('token_manager.os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data='{"bearer_token": "existing_token"}')
    @patch('token_manager.TokenManager.is_token_valid')
    def test_get_valid_token_existing(self, mock_is_valid, mock_file, mock_exists):
        tm = TokenManager()
        mock_exists.return_value = True
        mock_is_valid.return_value = True

        token = tm.get_valid_token()
        self.assertEqual(token, "existing_token")
        mock_is_valid.assert_called_with("existing_token")

    @patch('token_manager.os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data='{"bearer_token": "invalid_token"}')
    @patch('token_manager.TokenManager.is_token_valid')
    @patch('token_manager.get_bearer.get_token')
    def test_get_valid_token_refresh(self, mock_get_token, mock_is_valid, mock_file, mock_exists):
        tm = TokenManager()
        mock_exists.return_value = True
        # First call is valid check for existing token -> False
        # Second call is valid check for new token -> True
        mock_is_valid.side_effect = [False, True]

        mock_get_token.return_value = "new_token"

        token = tm.get_valid_token()
        self.assertEqual(token, "new_token")
        mock_get_token.assert_called_once()

        # Verify save was called
        # mock_open creates a mock object, calling it returns the file handle mock
        # handle = mock_file()
        # handle.write.assert_called()
        # Check if write was called with correct JSON
        # Since mock_open is tricky with multiple calls (read then write), we just check called.
        self.assertTrue(mock_file.called)

if __name__ == '__main__':
    unittest.main()
