import pytest
import requests
import time
from flask import session
from app import app, get_access_token

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key'
    # Set a dummy REDIRECT_URI for login redirects if needed, though not for this test
    app.config['REDIRECT_URI'] = 'http://localhost/callback'
    with app.test_client() as client:
        yield client

def test_get_access_token_refresh_failure_preserves_session_data(client, requests_mock):
    """
    Tests that a failed token refresh only clears authentication session
    variables, preserving other session data. This test will FAIL before the fix.
    """
    # Mock a failed response from the Mercado Libre token refresh endpoint
    token_url = "https://api.mercadolibre.com/oauth/token"
    requests_mock.post(token_url, status_code=400, json={"error": "invalid_grant"})

    # Use the test client's session to set up the initial state
    with client.session_transaction() as sess:
        sess['access_token'] = 'expired_token'
        sess['refresh_token'] = 'valid_refresh_token'
        sess['expires_at'] = time.time() - 3600  # Token is expired
        sess['cart_items'] = ['item1', 'item2'] # Other session data

    # The '/products' route calls get_access_token()
    client.get('/products')

    # After the failed refresh, check the session state
    with client.session_transaction() as sess:
        # The bug is that session.clear() is called, so 'cart_items' will be removed.
        # The correct behavior is for 'cart_items' to be preserved.
        # This assertion will fail with the current code.
        assert 'cart_items' in sess
        assert sess['cart_items'] == ['item1', 'item2']

        # We also expect the auth tokens to be gone.
        assert 'access_token' not in sess
        assert 'refresh_token' not in sess
        assert 'expires_at' not in sess
