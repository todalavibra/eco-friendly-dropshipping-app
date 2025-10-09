import pytest
import requests
import time
from flask import session, url_for
from app import app, get_access_token, search_eco_products

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key'
    # While the app uses env vars, setting this in config is a good practice for tests
    # that might rely on url_for building URLs.
    app.config['SERVER_NAME'] = 'localhost'
    with app.test_client() as client:
        with app.app_context():
            yield client

def test_get_access_token_refresh_failure_preserves_session_data(client, requests_mock):
    """
    Tests that a failed token refresh only clears authentication session
    variables, preserving other session data.
    """
    token_url = "https://api.mercadolibre.com/oauth/token"
    requests_mock.post(token_url, status_code=400, json={"error": "invalid_grant"})

    with client.session_transaction() as sess:
        sess['access_token'] = 'expired_token'
        sess['refresh_token'] = 'valid_refresh_token'
        sess['expires_at'] = time.time() - 3600
        sess['cart_items'] = ['item1', 'item2']

    # Any route that triggers get_access_token will work.
    client.get('/products')

    with client.session_transaction() as sess:
        assert 'cart_items' in sess
        assert sess['cart_items'] == ['item1', 'item2']
        assert 'access_token' not in sess
        assert 'refresh_token' not in sess
        assert 'expires_at' not in sess


def test_get_access_token_refresh_missing_token_in_response(client, requests_mock):
    """
    Tests that a successful (200 OK) but invalid token refresh response
    (e.g., missing 'access_token') is handled gracefully.
    """
    token_url = "https://api.mercadolibre.com/oauth/token"
    # Simulate a 200 OK response that is missing the access_token field.
    requests_mock.post(token_url, status_code=200, json={"scope": "read"})

    with app.test_request_context():
        session['refresh_token'] = 'valid_refresh_token'
        session['expires_at'] = time.time() - 3600 # Expired

        # This call should not raise a KeyError.
        token = get_access_token()

        assert token is None
        # The session should be cleared of auth data.
        assert 'access_token' not in session
        assert 'refresh_token' not in session
        assert 'expires_at' not in session

def test_get_access_token_valid_in_session(client):
    """
    Tests that a valid, non-expired token is correctly retrieved from the session.
    """
    with app.test_request_context():
        session['access_token'] = 'valid_token'
        session['expires_at'] = time.time() + 3600
        token = get_access_token()
        assert token == 'valid_token'

def test_get_access_token_no_token_in_session(client):
    """
    Tests that get_access_token returns None when no token is in the session.
    """
    with app.test_request_context():
        # Session is empty by default in a new request context
        token = get_access_token()
        assert token is None

def test_search_eco_products_success(requests_mock):
    """
    Tests a successful product search.
    """
    search_url = "https://api.mercadolibre.com/sites/MLA/search"
    mock_response = {"results": [{"id": "MLA123", "title": "Eco-Friendly Product"}]}
    requests_mock.get(search_url, json=mock_response)

    results, error = search_eco_products("eco-friendly", "fake_token")
    assert error is None
    assert results == mock_response

def test_search_eco_products_api_error(requests_mock):
    """
    Tests the function's error handling when the API call fails.
    """
    search_url = "https://api.mercadolibre.com/sites/MLA/search"
    requests_mock.get(search_url, status_code=500, reason="Internal Server Error")

    results, error = search_eco_products("eco-friendly", "fake_token")
    assert results is None
    assert "Internal Server Error" in error

# --- Route Tests ---

def test_home_route(client):
    """
    Tests that the home page loads correctly.
    """
    response = client.get('/')
    assert response.status_code == 200
    assert b"Eco-Friendly Dropshipping App" in response.data

def test_products_route_unauthenticated(client):
    """
    Tests that the /products route redirects to login when not authenticated.
    """
    response = client.get('/products')
    assert response.status_code == 302
    assert response.location == url_for('login', _external=False)

def test_products_route_authenticated_success(client, requests_mock):
    """
    Tests that the /products route displays products when authenticated.
    """
    search_url = "https://api.mercadolibre.com/sites/MLA/search"
    mock_response = {"results": [{"id": "MLA123", "title": "Green Bottle", "price": 150, "thumbnail": "http://example.com/img.jpg"}]}
    requests_mock.get(search_url, json=mock_response)

    with client.session_transaction() as sess:
        sess['access_token'] = 'valid_token'
        sess['expires_at'] = time.time() + 3600

    response = client.get('/products?q=green')
    assert response.status_code == 200
    assert b"Green Bottle" in response.data
    assert b"150" in response.data

def test_products_route_api_error(client, requests_mock):
    """
    Tests the /products route's error handling.
    """
    search_url = "https://api.mercadolibre.com/sites/MLA/search"
    requests_mock.get(search_url, status_code=500)

    with client.session_transaction() as sess:
        sess['access_token'] = 'valid_token'
        sess['expires_at'] = time.time() + 3600

    response = client.get('/products')
    assert response.status_code == 200
    assert b"There was an error searching for products" in response.data

def test_login_route_with_credentials(client, monkeypatch):
    """
    Tests that the login route redirects to Mercado Libre.
    """
    monkeypatch.setenv("MELI_CLIENT_ID", "test-id")
    monkeypatch.setenv("MELI_CLIENT_SECRET", "test-secret")
    monkeypatch.setenv("MELI_REDIRECT_URI", "http://localhost/callback")

    response = client.get('/login')
    assert response.status_code == 302
    assert 'auth.mercadolibre.com' in response.location
    assert 'client_id=test-id' in response.location

def test_login_route_no_credentials(client, monkeypatch):
    """
    Tests the login route behavior when credentials are not set.
    """
    monkeypatch.delenv("MELI_CLIENT_ID", raising=False)
    monkeypatch.delenv("MELI_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("MELI_REDIRECT_URI", raising=False)

    response = client.get('/login', follow_redirects=True)
    assert response.status_code == 200
    assert b"API credentials are not configured" in response.data

def test_callback_route_success(client, requests_mock):
    """
    Tests the /callback route with a successful token exchange.
    """
    token_url = "https://api.mercadolibre.com/oauth/token"
    requests_mock.post(token_url, json={
        "access_token": "new_access_token",
        "refresh_token": "new_refresh_token",
        "expires_in": 3600
    })

    response = client.get('/callback?code=test-code')
    assert response.status_code == 302
    assert response.location == url_for('products')

    with client.session_transaction() as sess:
        assert sess['access_token'] == 'new_access_token'
        assert sess['refresh_token'] == 'new_refresh_token'

def test_callback_route_no_code(client):
    """
    Tests the /callback route when the authorization code is missing.
    """
    response = client.get('/callback', follow_redirects=True)
    assert response.status_code == 200
    assert b"Authorization code not received." in response.data

def test_callback_route_token_exchange_error(client, requests_mock):
    """
    Tests the /callback route when the token exchange fails.
    """
    token_url = "https://api.mercadolibre.com/oauth/token"
    requests_mock.post(token_url, status_code=400, json={"message": "Invalid code"})

    response = client.get('/callback?code=bad-code', follow_redirects=True)
    assert response.status_code == 200
    assert b"Error during token exchange: Invalid code" in response.data