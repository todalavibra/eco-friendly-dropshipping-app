import os
import time
import requests
from flask import Flask, render_template, request, redirect, url_for, session, flash

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

def get_access_token():
    """Retrieves the access token from the session, refreshing it if necessary.

    This function checks if a valid, non-expired access token is present in the
    user's session. If the token is expired or missing, it attempts to use the
    refresh token to obtain a new one from the Mercado Libre API.

    Returns:
        str: The access token if available and valid.
        None: If the access token cannot be retrieved or refreshed, or if no
              refresh token is available.
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


def search_eco_products(query, access_token, site_id="MLA"):
    """Searches for products on Mercado Libre using the provided query."""
    search_url = f"https://api.mercadolibre.com/sites/{site_id}/search"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    params = {
        "q": query
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
def home():
    """Renders the home page."""
    return render_template('index.html')


@app.route("/products")
def products():
    """Displays a list of eco-friendly products from Mercado Libre."""
    access_token = get_access_token()
    if not access_token:
        flash("You need to be logged in to view products.", "warning")
        return redirect(url_for('login'))

    query = request.args.get("q", "eco-friendly")
    search_results, error = search_eco_products(query, access_token)

    if error:
        flash(f"There was an error searching for products: {error}", "danger")
        product_list = []
    else:
        product_list = search_results.get("results", []) if search_results else []

    return render_template('products.html', products=product_list, query=query)


@app.route("/login")
def login():
    """Redirects the user to the Mercado Libre authorization page."""
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
def callback():
    """Handles the OAuth2 callback from Mercado Libre."""
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