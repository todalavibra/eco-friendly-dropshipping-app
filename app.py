"""A simple Flask web application to search for eco-friendly products.

This application integrates with the Mercado Libre API to allow users to
search for products after authenticating via OAuth2. It handles the full
authentication flow, including token refreshing, and provides a basic interface
to display search results.

Attributes:
    app (Flask): The Flask application instance.
"""
import os
import time
from typing import Dict, Optional, Tuple

import requests
from flask import (Flask, flash, redirect, render_template, request, session,
                   url_for)

# --- App Initialization ---
app = Flask(__name__)
# It's crucial to set a secret key for session management.
# In a real app, use a long, random string and load it from env variables.
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "a-very-secret-key-that-should-be-changed")

# Conditionally import and run ngrok for local development
if os.environ.get("USE_NGROK"):
    from flask_ngrok import run_with_ngrok
    run_with_ngrok(app)

# --- Helper Functions ---

def get_access_token() -> Optional[str]:
    """Retrieves the access token from the session, refreshing if needed.

    This function checks for a valid, non-expired access token in the Flask
    session. If the token exists and is fresh, it's returned immediately. If
    the token is expired or missing, it attempts to use the stored refresh
    token to obtain a new access token from the Mercado Libre API.

    If the refresh is successful, it updates the session with the new token
    and its expiry time. If the refresh fails, it clears the session of all
    authentication data.

    Returns:
        A valid access token as a string if available or successfully
        refreshed, otherwise None.
    """
    if ('access_token' in session and 'expires_at' in session
            and time.time() < session['expires_at']):
        return session['access_token']

    if 'refresh_token' in session:
        print("Access token expired or missing. Attempting to refresh...")
        token_url = "https://api.mercadolibre.com/oauth/token"

        # Read credentials at time of use to make testing easier
        client_id = os.environ.get("MELI_CLIENT_ID")
        client_secret = os.environ.get("MELI_CLIENT_SECRET")

        payload = {
            "grant_type": "refresh_token",
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": session['refresh_token'],
        }
        try:
            response = requests.post(token_url, json=payload)
            response.raise_for_status()
            token_data = response.json()

            access_token = token_data.get("access_token")
            expires_in = token_data.get("expires_in")

            if not access_token or not expires_in:
                print(f"Invalid token response received: {token_data}")
                session.pop('access_token', None)
                session.pop('refresh_token', None)
                session.pop('expires_at', None)
                flash("Your session has expired. Please log in again.", "warning")
                return None

            session['access_token'] = access_token
            session['refresh_token'] = token_data.get('refresh_token', session['refresh_token'])
            session['expires_at'] = time.time() + expires_in - 60

            print("Token refreshed successfully.")
            return session['access_token']

        except requests.exceptions.RequestException as e:
            print(f"Error during token refresh: {e}")
            session.pop('access_token', None)
            session.pop('refresh_token', None)
            session.pop('expires_at', None)
            flash("Your session has expired. Please log in again.", "warning")
            return None

    return None


def search_eco_products(query: str, access_token: str, site_id: str = "MLA", sort: str = "relevance", offset: int = 0, limit: int = 10) -> Tuple[Optional[Dict], Optional[str]]:
    """Searches for products on Mercado Libre using the provided query.

    This function constructs and sends a GET request to the Mercado Libre
    search API. It includes the necessary authorization header and query
    parameters for filtering, sorting, and pagination.

    Args:
        query: The search term to look for.
        access_token: The user's OAuth2 access token for API authentication.
        site_id: The Mercado Libre site ID to search within. Defaults to
            "MLA" (Argentina).
        sort: The sorting criteria for the search results (e.g., 'relevance').
        offset: The starting index for pagination.
        limit: The number of results to return per page.

    Returns:
        A tuple containing two elements:
        - A dictionary with the JSON response from the API on success.
        - An error message string on failure.
        If the call is successful, the error message will be None, and vice
        versa.
    """
    if not query or not query.strip():
        return None, "Search query cannot be empty."

    search_url = f"https://api.mercadolibre.com/sites/{site_id}/search"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    params = {
        "q": query,
        "sort": sort,
        "offset": offset,
        "limit": limit
    }
    try:
        response = requests.get(search_url, headers=headers, params=params)
        response.raise_for_status()
        return response.json(), None
    except requests.exceptions.RequestException as e:
        print(f"Error during Mercado Libre search: {e}")
        return None, str(e)

# --- Routes ---

@app.route("/")
def home() -> str:
    """Renders the application's home page.

    Displays the main landing page of the application, which contains a
    welcome message and basic navigation.

    Returns:
        The rendered HTML content for the home page from the 'index.html'
        template.
    """
    return render_template('index.html')


@app.route("/products")
def products() -> str:
    """Displays a list of products based on a search query.

    Requires the user to be authenticated. It retrieves the user's access
    token and uses it to search for products on Mercado Libre. The search
    query is passed via the 'q' URL parameter; if absent, it defaults to
    "eco-friendly". The results are rendered on the products page.

    The view supports pagination via the 'page' URL parameter and sorting via
    the 'sort' parameter.

    Returns:
        A redirect to the login page if the user is not authenticated, or the
        rendered HTML of the 'products.html' template with the product list.
    """
    access_token = get_access_token()
    if not access_token:
        flash("You need to be logged in to view products.", "warning")
        return redirect(url_for('login'))

    query = request.args.get("q", "eco-friendly")
    sort = request.args.get("sort", "relevance")
    page = int(request.args.get("page", 1))
    limit = 10
    offset = (page - 1) * limit

    search_results, error = search_eco_products(query, access_token, sort=sort, offset=offset, limit=limit)

    if error:
        flash(f"There was an error searching for products: {error}", "danger")
        product_list = []
        total_pages = 0
    else:
        product_list = search_results.get("results", []) if search_results else []
        paging = search_results.get("paging", {})
        total_results = paging.get("total", 0)
        total_pages = (total_results + limit - 1) // limit

    return render_template('products.html', products=product_list, query=query, sort=sort, page=page, pages=total_pages)


@app.route("/login")
def login() -> str:
    """Initiates the OAuth2 login process.

    Constructs the Mercado Libre authorization URL and redirects the user.
    If the necessary API credentials (client ID, secret, redirect URI) are
    not configured in the environment, it flashes an error message and
    renders the home page instead of attempting the redirect.

    Returns:
        A Flask redirect response to the Mercado Libre authorization URL or
        the rendered HTML of the home page if credentials are missing.
    """
    # Read credentials at time of use
    client_id = os.environ.get("MELI_CLIENT_ID")
    client_secret = os.environ.get("MELI_CLIENT_SECRET")
    redirect_uri = os.environ.get("MELI_REDIRECT_URI")

    if not all([client_id, client_secret, redirect_uri]):
        flash("API credentials are not configured on the server.", "danger")
        return render_template('index.html')

    auth_url = (f"https://auth.mercadolibre.com/authorization?response_type=code"
                f"&client_id={client_id}&redirect_uri={redirect_uri}")
    return redirect(auth_url)


@app.route("/callback")
def callback() -> str:
    """Handles the OAuth2 callback from Mercado Libre.

    This route is triggered after a user authorizes the application on the
    Mercado Libre platform. It receives an authorization 'code' in the URL
    parameters, which it then exchanges for an access token and a refresh
    token by making a POST request to the Mercado Libre token endpoint.

    On success, the tokens are stored in the user's session, and the user
    is redirected to the main products page. On failure (e.g., no code,
    API error), it flashes an error message and redirects to the home page.

    Returns:
        A Flask redirect response to either the products page (on success) or
        the home page (on failure).
    """
    code = request.args.get("code")
    if not code:
        flash("Authorization code not received.", "danger")
        return redirect(url_for('home'))

    # Read credentials at time of use
    client_id = os.environ.get("MELI_CLIENT_ID")
    client_secret = os.environ.get("MELI_CLIENT_SECRET")
    redirect_uri = os.environ.get("MELI_REDIRECT_URI")

    token_url = "https://api.mercadolibre.com/oauth/token"
    payload = {
        "grant_type": "authorization_code",
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "redirect_uri": redirect_uri,
    }

    try:
        response = requests.post(token_url, json=payload)
        response.raise_for_status()
        token_data = response.json()

        if 'access_token' not in token_data or 'expires_in' not in token_data:
            flash("Error during token exchange: Malformed response from API.", "danger")
            return redirect(url_for('home'))

        session['access_token'] = token_data['access_token']
        session['refresh_token'] = token_data.get('refresh_token')
        session['expires_at'] = time.time() + token_data['expires_in'] - 60

        flash("Authentication successful!", "success")
        return redirect(url_for('products'))

    except requests.exceptions.RequestException as e:
        error_message = str(e)
        if e.response is not None:
            try:
                error_data = e.response.json()
                error_message = error_data.get('message', error_message)
            except ValueError:
                pass
        flash(f"Error during token exchange: {error_message}", "danger")
        return redirect(url_for('home'))


if __name__ == '__main__':
    # Check for credentials at startup for a helpful warning
    if not all([os.environ.get("MELI_CLIENT_ID"),
                os.environ.get("MELI_CLIENT_SECRET"),
                os.environ.get("MELI_REDIRECT_URI")]):
        print("WARNING: Mercado Libre API credentials (MELI_CLIENT_ID, MELI_CLIENT_SECRET, MELI_REDIRECT_URI) are not set in environment variables.")
        print("The application will run, but authentication will fail.")
    app.run(host='0.0.0.0', port=5000)