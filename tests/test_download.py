import unittest
from unittest.mock import MagicMock, patch
from requests.exceptions import Timeout

from uavsar_pytools.download.download import stream_download

class download_test(unittest.TestCase):
    @patch('uavsar_pytools.download.download.requests')
    def test_stream_timeout(self, mock_requests):
        mock_requests.get.side_effect = Timeout
        with self.assertRaises(Timeout):
            stream_download()
            mock_requests.get.assert_called_once()

if __name__ == '__main__':
    unittest.main()