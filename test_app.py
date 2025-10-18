import time
import runpy
from unittest.mock import patch

import pytest
from flask import session, url_for
from flask.testing import FlaskClient
from requests_mock import Mocker

from app import app, get_access_token, search_eco_products


@pytest.fixture
def client() -> FlaskClient:
    """Provides a test client for the Flask application.

    This fixture configures the Flask app for testing by enabling the 'TESTING'
    flag, setting a temporary secret key, and defining a server name for
    consistent URL generation. It yields a test client, which allows for
    making requests to the application's endpoints within a test context.

    Yields:
        A Flask test client instance.
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
    """Ensures a failed token refresh preserves other session data.

    This test simulates a scenario where the token refresh API call returns
    an error. It verifies that the session cleaning logic correctly removes
    only the expired authentication keys (`access_token`, `refresh_token`,
    `expires_at`) while preserving other unrelated session data, such as
    items in a shopping cart.

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
    """Tests handling of a malformed but successful token refresh response.

    This test covers the edge case where the token refresh API returns a 200
    OK status but the JSON body is missing the expected 'access_token'. It
    verifies that the application handles this gracefully by clearing the
    invalid session data and redirecting the user to log in again.

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
    """Tests a successful token refresh flow.

    This test simulates a scenario where a user's access token has expired.
    It verifies that the application automatically uses the refresh token to
    request a new access token from the API and correctly updates the session
    with the new token, its expiry time, and the updated refresh token.

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
    """Tests `get_access_token` when the session lacks a refresh token.

    This test ensures that if a user's access token is expired or missing,
    but there is no corresponding refresh token in the session, the function
    correctly returns `None` without attempting an API call.

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
    """Ensures `get_access_token` returns a valid token from the session.

    This test confirms that if a valid, non-expired access token exists in
    the user's session, the `get_access_token` function returns it directly
    without attempting an unnecessary and wasteful API call to refresh it.

    Args:
        client: The Flask test client.
    """
    with app.test_request_context():
        session['access_token'] = 'valid_token'
        session['expires_at'] = time.time() + 3600
        token = get_access_token()
        assert token == 'valid_token'

def test_get_access_token_no_token_in_session(client: FlaskClient) -> None:
    """Tests `get_access_token` for a session with no token information.

    This test verifies that when a user has a completely empty session (no
    access token, no refresh token), the `get_access_token` function
    correctly returns `None` without raising any errors.

    Args:
        client: The Flask test client.
    """
    with app.test_request_context():
        # Session is empty by default in a new request context
        token = get_access_token()
        assert token is None

def test_search_eco_products_success(requests_mock: Mocker) -> None:
    """Tests a successful product search against the Mercado Libre API.

    This test mocks a successful API response for a product search and
    verifies that the `search_eco_products` function correctly calls the API,
    parses the JSON response, and returns the expected data tuple (results,
    None).

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

    This test simulates a scenario where the Mercado Libre search API
    returns an HTTP error (e.g., 500 Internal Server Error). It verifies
    that the `search_eco_products` function catches the exception and returns
    a `(None, str)` tuple containing a descriptive error message.

    Args:
        requests_mock: The mock for the requests library.
    """
    search_url = "https://api.mercadolibre.com/sites/MLA/search"
    requests_mock.get(search_url, status_code=500, reason="Internal Server Error")

    results, error = search_eco_products("eco-friendly", "fake_token")
    assert results is None
    assert "Internal Server Error" in error


def test_search_eco_products_invalid_query(client: FlaskClient) -> None:
    """Ensures the search function handles invalid queries gracefully.

    This test verifies that the `search_eco_products` function returns an
    error message when the provided query is empty or contains only
    whitespace. It confirms that no unnecessary API call is made in these
    cases.

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

    This test makes a GET request to the root URL ('/') and asserts that it
    receives a 200 OK status code. It also checks for the presence of a key
    phrase in the response body to ensure the correct template was rendered.

    Args:
        client: The Flask test client.
    """
    response = client.get('/')
    assert response.status_code == 200
    assert b"Eco-Friendly Dropshipping App" in response.data

def test_products_route_unauthenticated(client: FlaskClient) -> None:
    """Ensures the /products route redirects unauthenticated users.

    This test verifies that any attempt to access the protected /products
    endpoint without a valid session results in a redirect (status code 302)
    to the login page, preventing unauthorized access.

    Args:
        client: The Flask test client.
    """
    response = client.get('/products')
    assert response.status_code == 302
    assert response.location == url_for('login', _external=False)

def test_products_route_authenticated_success(client: FlaskClient, requests_mock: Mocker) -> None:
    """Tests successful product display for an authenticated user.

    This test simulates a logged-in user by creating a valid session with an
    access token. It then mocks a successful API response from the search
    endpoint and verifies that the /products page renders correctly,
    displaying the product information from the API.

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
    """Ensures the /products route handles API errors gracefully.

    This test simulates a scenario where the user is authenticated, but the
    call to the Mercado Libre search API fails. It verifies that the page
    still renders successfully (200 OK) and displays a user-friendly error
    message in the response body.

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

    This test verifies that the 'page' query parameter is correctly
    interpreted and used to calculate the 'offset' for the API request,
    enabling users to navigate through pages of search results.

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
    """Ensures the /products route uses a default query.

    This test verifies that when an authenticated user accesses the /products
    page without specifying a search query 'q' in the URL, the application
    defaults to searching for "eco-friendly" as a fallback.

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
    """Tests the login route redirect when credentials are set.

    This test uses `monkeypatch` to set the necessary environment variables
    for the API credentials. It then verifies that accessing the /login route
    correctly builds the Mercado Libre authorization URL and returns a 302
    redirect to it.

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
    """Ensures the login route handles missing API credentials.

    This test uses `monkeypatch` to simulate an environment where the
    Mercado Libre API credentials have not been set. It verifies that
    accessing the /login route does not cause a crash, but instead flashes
    a user-friendly error message on the home page.

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

    This test simulates a successful authorization by the user, where Mercado
    Libre redirects back to the /callback endpoint with a valid authorization
    code. It mocks a successful response from the token exchange API and
    verifies that the new tokens are correctly stored in the session, and the
    user is redirected to the products page.

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
    """Ensures the callback route handles a missing authorization code.

    This test verifies that if a user is redirected to the /callback
    endpoint without the required 'code' URL parameter, the application
    flashes an appropriate error message and redirects the user to the home
    page.

    Args:
        client: The Flask test client.
    """
    response = client.get('/callback', follow_redirects=True)
    assert response.status_code == 200
    assert b"Authorization code not received." in response.data

def test_callback_route_malformed_token_response(client: FlaskClient, requests_mock: Mocker) -> None:
    """Tests the callback route with a malformed token response.

    This test handles the edge case where the token exchange API returns a
    200 OK status, but the JSON response is missing the required
    'access_token' field. It verifies that the application correctly
    identifies this as an error, flashes a message, and redirects home.

    Args:
        client: The Flask test client.
        requests_mock: The mock for the requests library.
    """
    token_url = "https://api.mercadolibre.com/oauth/token"
    requests_mock.post(token_url, status_code=200, json={"scope": "read"}) # Missing 'access_token'

    response = client.get('/callback?code=test-code', follow_redirects=True)
    assert response.status_code == 200
    assert b"Error during token exchange" in response.data


def test_callback_route_api_error_with_json_body(client: FlaskClient, requests_mock: Mocker) -> None:
    """Tests the callback route when the API returns a JSON error.

    This test simulates a scenario where the token exchange API returns a
    structured JSON error (e.g., a 400 Bad Request). It verifies that the
    application correctly parses the JSON, extracts the 'message' field, and
    displays it to the user as a flashed message.

    Args:
        client: The Flask test client.
        requests_mock: The mock for the requests library.
    """
    token_url = "https://api.mercadolibre.com/oauth/token"
    requests_mock.post(
        token_url,
        status_code=400,
        json={"message": "Invalid authorization code."}
    )

    response = client.get('/callback?code=invalid-code', follow_redirects=True)
    assert response.status_code == 200
    assert b"Error during token exchange: Invalid authorization code." in response.data


def test_main_execution_with_ngrok_and_warning(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests the main execution block with ngrok and a credential warning.

    This test verifies multiple startup conditions simultaneously:
    1.  It ensures that `run_with_ngrok` is called when the `USE_NGROK`
        environment variable is set.
    2.  It checks that a warning is printed to the console if the Mercado
        Libre API credentials are not set in the environment.
    3.  It confirms that `app.run()` is called with the correct host and port.

    This is achieved by using `runpy` to execute the app's script as `__main__`
    and patching the `run`, `run_with_ngrok`, and `print` functions.

    Args:
        monkeypatch: The pytest fixture for modifying the environment.
    """
    # Set up conditions for the test
    monkeypatch.setenv("USE_NGROK", "true")
    monkeypatch.delenv("MELI_CLIENT_ID", raising=False)  # Trigger the warning

    # Patch the low-level Flask run method, the ngrok wrapper, and print
    with patch('flask.Flask.run') as mock_flask_run, \
         patch('flask_ngrok.run_with_ngrok') as mock_run_with_ngrok, \
         patch('builtins.print') as mock_print:

        # Execute the app script as if it were the main entry point
        runpy.run_module('app', run_name='__main__')

        # Assert that the startup logic behaved as expected
        mock_run_with_ngrok.assert_called_once()
        mock_flask_run.assert_called_once_with(host='0.0.0.0', port=5000)

        # Check that the warning for missing credentials was printed
        warning_message_found = any(
            "WARNING: Mercado Libre API credentials" in call.args[0]
            for call in mock_print.call_args_list
        )
        assert warning_message_found, "The warning for missing credentials was not printed."

    # Clean up environment variables
    monkeypatch.delenv("USE_NGROK")


def test_callback_route_api_error_with_non_json_body(client: FlaskClient, requests_mock: Mocker) -> None:
    """Tests the callback route when the API returns a non-JSON error.

    This test ensures that if the token exchange API returns an error with a
    non-JSON response body (e.g., plain text or HTML), the application
    handles it gracefully by displaying a generic error message to the user
    instead of crashing due to a JSON decoding error.

    Args:
        client: The Flask test client.
        requests_mock: The mock for the requests library.
    """
    token_url = "https://api.mercadolibre.com/oauth/token"
    requests_mock.post(
        token_url,
        status_code=500,
        text="Internal Server Error"
    )

    response = client.get('/callback?code=any-code', follow_redirects=True)
    assert response.status_code == 200
    assert b"Error during token exchange: 500 Server Error" in response.data