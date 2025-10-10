import pytest
import requests
import time
from flask import session, url_for
from app import app, get_access_token, search_eco_products

@pytest.fixture
def client():
    """A test client for the Flask application.

    This fixture sets up the application for testing by enabling the 'TESTING'
    flag, setting a test-specific secret key, and providing a test client to
    make requests to the application's endpoints.

    Yields:
        FlaskClient: A test client instance for the application.
    """
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
    variables, preserving other session data. This ensures that a user's
    unrelated session information (e.g., a shopping cart) is not lost during
    a failed re-authentication attempt.
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
    (e.g., missing 'access_token') is handled gracefully. The function should
    not raise an exception and should clear the expired authentication data
    from the session.
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
    Tests that a valid, non-expired token is correctly retrieved from the session
    without needing to make an external API call.
    """
    with app.test_request_context():
        session['access_token'] = 'valid_token'
        session['expires_at'] = time.time() + 3600
        token = get_access_token()
        assert token == 'valid_token'

def test_get_access_token_no_token_in_session(client):
    """
    Tests that get_access_token returns None when no token information is
    present in the session, ensuring it doesn't error on a clean session.
    """
    with app.test_request_context():
        # Session is empty by default in a new request context
        token = get_access_token()
        assert token is None

def test_search_eco_products_success(requests_mock):
    """
    Tests a successful product search, ensuring that the function correctly
    parses the JSON response from the Mercado Libre API and returns it.
    """
    search_url = "https://api.mercadolibre.com/sites/MLA/search"
    mock_response = {"results": [{"id": "MLA123", "title": "Eco-Friendly Product"}]}
    requests_mock.get(search_url, json=mock_response)

    results, error = search_eco_products("eco-friendly", "fake_token")
    assert error is None
    assert results == mock_response

def test_search_eco_products_api_error(requests_mock):
    """
    Tests the function's error handling when the Mercado Libre API call fails.
    It should return None for the results and a descriptive error message.
    """
    search_url = "https://api.mercadolibre.com/sites/MLA/search"
    requests_mock.get(search_url, status_code=500, reason="Internal Server Error")

    results, error = search_eco_products("eco-friendly", "fake_token")
    assert results is None
    assert "Internal Server Error" in error

# --- Route Tests ---

def test_home_route(client):
    """
    Tests that the home page ('/') loads correctly and returns a 200 OK status.
    """
    response = client.get('/')
    assert response.status_code == 200
    assert b"Eco-Friendly Dropshipping App" in response.data

def test_products_route_unauthenticated(client):
    """
    Tests that the /products route correctly redirects to the login page
    when the user is not authenticated.
    """
    response = client.get('/products')
    assert response.status_code == 302
    assert response.location == url_for('login', _external=False)

def test_products_route_authenticated_success(client, requests_mock):
    """
    Tests that the /products route displays products correctly when the user
    is authenticated. It mocks the API call to return a sample product list.
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
    Tests that the /products route handles an API error gracefully by
    displaying an error message to the user on the page.
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
    Tests that the login route correctly redirects the user to the
    Mercado Libre authorization URL when API credentials are set.
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
    Tests that the login route displays an error message on the home page
    when the required API credentials are not set in the environment.
    """
    monkeypatch.delenv("MELI_CLIENT_ID", raising=False)
    monkeypatch.delenv("MELI_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("MELI_REDIRECT_URI", raising=False)

    response = client.get('/login', follow_redirects=True)
    assert response.status_code == 200
    assert b"API credentials are not configured" in response.data

def test_callback_route_success(client, requests_mock):
    """
    Tests the /callback route with a successful token exchange. It verifies
    that the access and refresh tokens are correctly stored in the session
    and the user is redirected to the products page.
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
    Tests the /callback route's behavior when the 'code' URL parameter is
    missing, ensuring it flashes an appropriate error message.
    """
    response = client.get('/callback', follow_redirects=True)
    assert response.status_code == 200
    assert b"Authorization code not received." in response.data

def test_callback_route_token_exchange_error(client, requests_mock):
    """
    Tests the /callback route when the token exchange with the API fails.
    It should display a descriptive error message to the user.
    """
    token_url = "https://api.mercadolibre.com/oauth/token"
    requests_mock.post(token_url, status_code=400, json={"message": "Invalid code"})

    response = client.get('/callback?code=bad-code', follow_redirects=True)
    assert response.status_code == 200
    assert b"Error during token exchange: Invalid code" in response.data