"""
Unit tests for Kobo client and error handling.
"""

from unittest.mock import patch, MagicMock
from src.kobo_client import fetch_kobo_submissions

def test_fetch_kobo_missing_credentials():
    # Patch Config credentials so the test is independent of local secrets.toml
    # (real credentials may be configured in the developer environment).
    with patch("src.kobo_client.Config.KOBO_ASSET_UID", None), \
         patch("src.kobo_client.Config.KOBO_TOKEN", None), \
         patch("src.kobo_client.Config.KOBO_EXPORT_SETTINGS_UID", None):
        data, err = fetch_kobo_submissions(base_url="https://kf.kobotoolbox.org", asset_uid=None, token=None)
    assert data == []
    assert "not configured" in err

@patch("requests.get")
def test_fetch_kobo_pagination_success(mock_get):
    # Mock Page 1
    mock_resp1 = MagicMock()
    mock_resp1.status_code = 200
    mock_resp1.json.return_value = {
        "results": [{"_id": 1, "1. Organization Name": "Org 1"}],
        "next": "https://kf.kobotoolbox.org/api/v2/assets/abc/data.json?page=2"
    }

    # Mock Page 2
    mock_resp2 = MagicMock()
    mock_resp2.status_code = 200
    mock_resp2.json.return_value = {
        "results": [{"_id": 2, "1. Organization Name": "Org 2"}],
        "next": None
    }

    mock_get.side_effect = [mock_resp1, mock_resp2]

    results, err = fetch_kobo_submissions(
        base_url="https://kf.kobotoolbox.org",
        asset_uid="test_uid",
        token="test_token"
    )

    assert err is None
    assert len(results) == 2
    assert results[0]["_id"] == 1
    assert results[1]["_id"] == 2
    assert mock_get.call_count == 2
