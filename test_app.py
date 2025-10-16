import time

import pytest
from flask import session, url_for
from flask.testing import FlaskClient
from requests_mock import Mocker

from app import app, get_access_token, search_eco_products


@pytest.fixture
def client() -> FlaskClient:
    """Provides a test client for the Flask application.

    This fixture configures the application for testing by enabling the
    'TESTING' flag and setting a test-specific secret key. It yields a
    test client instance to make requests to the application's endpoints.

    Yields:
        A test client instance for the Flask application.
    """
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key'
    # While the app uses env vars, setting this in config is a good practice for tests
    # that might rely on url_for building URLs.
    app.config['SERVER_NAME'] = 'localhost'
    with app.test_client() as client:
        with app.app_context():
            yield client

def test_get_access_token_refresh_failure_preserves_session_data(client: FlaskClient, requests_mock: Mocker) -> None:
    """Tests that a failed token refresh preserves other session data.

    Verifies that if the API call to refresh a token fails, only the
    authentication-related keys are removed from the session, while other
    data (e.g., 'cart_items') remains untouched.

    Args:
        client: The Flask test client.
        requests_mock: The mock for the requests library.
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


def test_get_access_token_refresh_missing_token_in_response(client: FlaskClient, requests_mock: Mocker) -> None:
    """Tests graceful handling of a malformed token refresh response.

    Ensures that if the API returns a 200 OK but the JSON response is
    missing the 'access_token', the function handles it without errors and
    clears the expired authentication data from the session.

    Args:
        client: The Flask test client.
        requests_mock: The mock for the requests library.
    """
    token_url = "https://api.mercadolibre.com/oauth/token"
    requests_mock.post(token_url, status_code=200, json={"scope": "read"})

    with client.session_transaction() as sess:
        sess['refresh_token'] = 'valid_refresh_token'
        sess['expires_at'] = time.time() - 3600

    # This should fail the token refresh and redirect to login
    response = client.get('/products')
    assert response.status_code == 302
    assert response.location == url_for('login')

    # Verify that the session was cleared of auth data
    with client.session_transaction() as sess:
        assert 'access_token' not in sess
        assert 'refresh_token' not in sess
        assert 'expires_at' not in sess


def test_get_access_token_refresh_success(client: FlaskClient, requests_mock: Mocker) -> None:
    """Tests a successful token refresh.

    Verifies that an expired token is correctly refreshed using the refresh
    token, and that the new access token and expiry time are stored in the
    session.

    Args:
        client: The Flask test client.
        requests_mock: The mock for the requests library.
    """
    token_url = "https://api.mercadolibre.com/oauth/token"
    requests_mock.post(token_url, json={
        "access_token": "new_refreshed_token",
        "refresh_token": "updated_refresh_token",
        "expires_in": 3600
    })
    # Mock the subsequent search API call in the /products route
    search_url = "https://api.mercadolibre.com/sites/MLA/search"
    requests_mock.get(search_url, json={"results": []})

    with client.session_transaction() as sess:
        sess['refresh_token'] = 'old_refresh_token'
        sess['expires_at'] = time.time() - 7200  # Expired

    response = client.get('/products')
    assert response.status_code == 200

    with client.session_transaction() as sess:
        assert sess['access_token'] == "new_refreshed_token"
        assert sess['refresh_token'] == "updated_refresh_token"
        assert 'expires_at' in sess and sess['expires_at'] > time.time()


def test_get_access_token_no_refresh_token(client: FlaskClient) -> None:
    """Tests that get_access_token returns None when no refresh token is available.

    Ensures that the function returns None and does not attempt a refresh
    if the session is missing a 'refresh_token'.

    Args:
        client: The Flask test client.
    """
    with app.test_request_context():
        # Session has an expired access token but no refresh token
        session['access_token'] = 'expired_token'
        session['expires_at'] = time.time() - 3600

        token = get_access_token()
        assert token is None

def test_get_access_token_valid_in_session(client: FlaskClient) -> None:
    """Tests that a valid token in the session is returned correctly.

    Verifies that `get_access_token` retrieves a non-expired token directly
    from the session without making an unnecessary external API call.

    Args:
        client: The Flask test client.
    """
    with app.test_request_context():
        session['access_token'] = 'valid_token'
        session['expires_at'] = time.time() + 3600
        token = get_access_token()
        assert token == 'valid_token'

def test_get_access_token_no_token_in_session(client: FlaskClient) -> None:
    """Tests that get_access_token returns None for a clean session.

    Ensures that the function returns None and does not raise an error when
    no token information is present in the session.

    Args:
        client: The Flask test client.
    """
    with app.test_request_context():
        # Session is empty by default in a new request context
        token = get_access_token()
        assert token is None

def test_search_eco_products_success(requests_mock: Mocker) -> None:
    """Tests a successful product search against the Mercado Libre API.

    Verifies that the `search_eco_products` function correctly calls the
    API, parses the JSON response, and returns the expected data.

    Args:
        requests_mock: The mock for the requests library.
    """
    search_url = "https://api.mercadolibre.com/sites/MLA/search"
    mock_response = {"results": [{"id": "MLA123", "title": "Eco-Friendly Product"}]}
    requests_mock.get(search_url, json=mock_response)

    results, error = search_eco_products("eco-friendly", "fake_token")
    assert error is None
    assert results == mock_response

def test_search_eco_products_api_error(requests_mock: Mocker) -> None:
    """Tests error handling for a failed product search API call.

    Ensures that if the Mercado Libre API returns an error (e.g., 500),
    the function returns None for the results and a descriptive error message.

    Args:
        requests_mock: The mock for the requests library.
    """
    search_url = "https://api.mercadolibre.com/sites/MLA/search"
    requests_mock.get(search_url, status_code=500, reason="Internal Server Error")

    results, error = search_eco_products("eco-friendly", "fake_token")
    assert results is None
    assert "Internal Server Error" in error


def test_search_eco_products_invalid_query(client: FlaskClient) -> None:
    """Tests that the search function handles invalid queries gracefully.

    Verifies that the function returns an error when the query is empty or
    None, without making an unnecessary API call.

    Args:
        client: The Flask test client.
    """
    with app.test_request_context():
        # Test with an empty query
        results, error = search_eco_products("", "fake_token")
        assert results is None
        assert error == "Search query cannot be empty."

        # Test with a query containing only whitespace
        results, error = search_eco_products("   ", "fake_token")
        assert results is None
        assert error == "Search query cannot be empty."

# --- Route Tests ---

def test_home_route(client: FlaskClient) -> None:
    """Tests that the home page ('/') loads correctly.

    Verifies that the route returns a 200 OK status and contains the
    expected title, indicating the page has rendered successfully.

    Args:
        client: The Flask test client.
    """
    response = client.get('/')
    assert response.status_code == 200
    assert b"Eco-Friendly Dropshipping App" in response.data

def test_products_route_unauthenticated(client: FlaskClient) -> None:
    """Tests that the /products route redirects unauthenticated users.

    Verifies that accessing the /products page without being logged in
    results in a redirect (302) to the login page.

    Args:
        client: The Flask test client.
    """
    response = client.get('/products')
    assert response.status_code == 302
    assert response.location == url_for('login', _external=False)

def test_products_route_authenticated_success(client: FlaskClient, requests_mock: Mocker) -> None:
    """Tests that the /products route displays products for authenticated users.

    Mocks a valid session and a successful API response to verify that the
    route renders the product list correctly with the expected data.

    Args:
        client: The Flask test client.
        requests_mock: The mock for the requests library.
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

def test_products_route_api_error(client: FlaskClient, requests_mock: Mocker) -> None:
    """Tests that the /products route handles API errors gracefully.

    Verifies that if the underlying API call fails, the page still renders
    and displays a user-friendly error message.

    Args:
        client: The Flask test client.
        requests_mock: The mock for the requests library.
    """
    search_url = "https://api.mercadolibre.com/sites/MLA/search"
    requests_mock.get(search_url, status_code=500)

    with client.session_transaction() as sess:
        sess['access_token'] = 'valid_token'
        sess['expires_at'] = time.time() + 3600

    response = client.get('/products')
    assert response.status_code == 200
    assert b"There was an error searching for products" in response.data


def test_products_route_pagination(client: FlaskClient, requests_mock: Mocker) -> None:
    """Tests the pagination functionality on the /products route.

    Verifies that the correct offset is sent to the API based on the 'page'
    query parameter.

    Args:
        client: The Flask test client.
        requests_mock: The mock for the requests library.
    """
    search_url = "https://api.mercadolibre.com/sites/MLA/search"
    requests_mock.get(search_url, json={"results": [], "paging": {"total": 50, "offset": 20, "limit": 10}})

    with client.session_transaction() as sess:
        sess['access_token'] = 'valid_token'
        sess['expires_at'] = time.time() + 3600

    response = client.get('/products?page=3')
    assert response.status_code == 200
    # Verify that the 'offset' parameter in the API call was correct (page 3 -> offset 20)
    assert requests_mock.last_request.qs['offset'] == ['20']


def test_products_route_default_query(client: FlaskClient, requests_mock: Mocker) -> None:
    """Tests that the /products route uses a default query.

    Verifies that if no 'q' parameter is provided, the route defaults to
    searching for "eco-friendly".

    Args:
        client: The Flask test client.
        requests_mock: The mock for the requests library.
    """
    search_url = "https://api.mercadolibre.com/sites/MLA/search"
    requests_mock.get(search_url, json={"results": []})

    with client.session_transaction() as sess:
        sess['access_token'] = 'valid_token'
        sess['expires_at'] = time.time() + 3600

    client.get('/products')
    assert requests_mock.last_request.qs['q'] == ['eco-friendly']

def test_login_route_with_credentials(client: FlaskClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests that the login route redirects correctly when credentials are set.

    Uses monkeypatch to set the required environment variables and verifies
    that the /login route redirects to the correct Mercado Libre auth URL.

    Args:
        client: The Flask test client.
        monkeypatch: The pytest fixture for modifying the environment.
    """
    monkeypatch.setenv("MELI_CLIENT_ID", "test-id")
    monkeypatch.setenv("MELI_CLIENT_SECRET", "test-secret")
    monkeypatch.setenv("MELI_REDIRECT_URI", "http://localhost/callback")

    response = client.get('/login')
    assert response.status_code == 302
    assert 'auth.mercadolibre.com' in response.location
    assert 'client_id=test-id' in response.location

def test_login_route_no_credentials(client: FlaskClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests that the login route shows an error if credentials are missing.

    Uses monkeypatch to delete environment variables and verifies that the
    /login route renders the home page with a visible error message.

    Args:
        client: The Flask test client.
        monkeypatch: The pytest fixture for modifying the environment.
    """
    monkeypatch.delenv("MELI_CLIENT_ID", raising=False)
    monkeypatch.delenv("MELI_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("MELI_REDIRECT_URI", raising=False)

    response = client.get('/login', follow_redirects=True)
    assert response.status_code == 200
    assert b"API credentials are not configured" in response.data

def test_callback_route_success(client: FlaskClient, requests_mock: Mocker) -> None:
    """Tests a successful OAuth2 callback and token exchange.

    Mocks a successful response from the token exchange endpoint and verifies
    that the access/refresh tokens are stored in the session and the user is
    redirected to the products page.

    Args:
        client: The Flask test client.
        requests_mock: The mock for the requests library.
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

def test_callback_route_no_code(client: FlaskClient) -> None:
    """Tests the callback route when the 'code' parameter is missing.

    Verifies that if the callback is accessed without an authorization code,
    it flashes an appropriate error message and redirects.

    Args:
        client: The Flask test client.
    """
    response = client.get('/callback', follow_redirects=True)
    assert response.status_code == 200
    assert b"Authorization code not received." in response.data

def test_callback_route_malformed_token_response(client: FlaskClient, requests_mock: Mocker) -> None:
    """Tests the callback route with a malformed token response from the API.

    Verifies that if the API returns a 200 OK but the response is missing
    the 'access_token', an error is flashed to the user.

    Args:
        client: The Flask test client.
        requests_mock: The mock for the requests library.
    """
    token_url = "https://api.mercadolibre.com/oauth/token"
    requests_mock.post(token_url, status_code=200, json={"scope": "read"}) # Missing 'access_token'

    response = client.get('/callback?code=test-code', follow_redirects=True)
    assert response.status_code == 200
    assert b"Error during token exchange" in response.data