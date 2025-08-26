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

# --- Mercado Libre API Configuration ---
# It's recommended to use environment variables for sensitive information.
CLIENT_ID = os.environ.get("MELI_CLIENT_ID")
CLIENT_SECRET = os.environ.get("MELI_CLIENT_SECRET")
# This should be the ngrok URL ending with /callback
REDIRECT_URI = os.environ.get("MELI_REDIRECT_URI")


# --- Helper Functions ---

def get_access_token():
    """
    Retrieves the access token from the session, refreshing it if necessary.
    Returns the access token or None if it can't be obtained.
    """
    # Check if token exists and is not expired (with a 60-second buffer)
    if ('access_token' in session and 'expires_at' in session
            and time.time() < session['expires_at']):
        return session['access_token']

    # If token is expired or doesn't exist, try to refresh
    if 'refresh_token' in session:
        print("Access token expired or missing. Attempting to refresh...")
        token_url = "https://api.mercadolibre.com/oauth/token"
        payload = {
            "grant_type": "refresh_token",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "refresh_token": session['refresh_token'],
        }
        try:
            response = requests.post(token_url, json=payload)
            response.raise_for_status()
            token_data = response.json()

            session['access_token'] = token_data['access_token']
            session['refresh_token'] = token_data.get('refresh_token', session['refresh_token'])
            session['expires_at'] = time.time() + token_data['expires_in'] - 60

            print("Token refreshed successfully.")
            return session['access_token']

        except requests.exceptions.RequestException as e:
            print(f"Error during token refresh: {e}")
            # Clear session and notify user if refresh fails
            session.clear()
            flash("Your session has expired. Please log in again.", "warning")
            return None

    # No valid access token or refresh token available.
    return None


def search_eco_products(query, access_token, site_id="MLA"):
    """
    Searches for products on Mercado Libre based on a query.
    Returns a tuple (data, error).
    """
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
    """
    Displays eco-friendly products after attempting authenticated search.
    """
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
    if not all([CLIENT_ID, CLIENT_SECRET, REDIRECT_URI]):
        flash("API credentials are not configured on the server.", "danger")
        return render_template('index.html')

    auth_url = (f"https://auth.mercadolibre.com/authorization?response_type=code"
                f"&client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}")
    return redirect(auth_url)


@app.route("/callback")
def callback():
    """
    Handles the redirect from Mercado Libre and exchanges the authorization
    code for an access token.
    """
    code = request.args.get("code")
    if not code:
        flash("Authorization code not received.", "danger")
        return redirect(url_for('home'))

    token_url = "https://api.mercadolibre.com/oauth/token"
    payload = {
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "redirect_uri": REDIRECT_URI,
    }

    try:
        response = requests.post(token_url, json=payload)
        response.raise_for_status()
        token_data = response.json()

        session['access_token'] = token_data['access_token']
        session['refresh_token'] = token_data.get('refresh_token')
        session['expires_at'] = time.time() + token_data['expires_in'] - 60 # 60s buffer

        flash("Authentication successful!", "success")
        return redirect(url_for('products'))

    except requests.exceptions.RequestException as e:
        error_message = str(e)
        if e.response is not None:
            try:
                error_data = e.response.json()
                error_message = error_data.get('message', error_message)
            except ValueError:
                # Response is not JSON, use the original exception message
                pass
        flash(f"Error during token exchange: {error_message}", "danger")
        return redirect(url_for('home'))


if __name__ == '__main__':
    if not all([CLIENT_ID, CLIENT_SECRET, REDIRECT_URI]):
        print("WARNING: Mercado Libre API credentials (MELI_CLIENT_ID, MELI_CLIENT_SECRET, MELI_REDIRECT_URI) are not set in environment variables.")
        print("The application will run, but authentication will fail.")
    app.run(host='0.0.0.0', port=5000)
