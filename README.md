# Eco-Friendly Product Search App

A demonstration Flask web application that allows users to search for eco-friendly products on Mercado Libre. It showcases a complete integration with the Mercado Libre API, including OAuth2 authentication, token management, and product searching.

The application is designed to be a clear, well-documented example for developers looking to work with third-party APIs in a Python web framework.

## Features

-   **OAuth2 Authentication**: Securely authenticates users via their Mercado Libre accounts using the standard authorization code flow.
-   **API Integration**: Searches for products on the Mercado Libre marketplace.
-   **Session Management**: Uses Flask's server-side sessions to maintain user authentication state.
-   **Automatic Token Refresh**: Includes logic to automatically refresh expired access tokens using a refresh token, ensuring a seamless user experience.
-   **Local Development Tunneling**: Integrated with `pyngrok` to simplify testing of OAuth2 callbacks during local development.
-   **Comprehensive Test Suite**: Comes with a full suite of unit and integration tests using `pytest`.

## Getting Started

Follow these instructions to get the project running on your local machine.

### Prerequisites

-   Python 3.7+
-   `pip` for installing Python packages.
-   A Mercado Libre developer account to get API credentials. You can create one on the [Mercado Libre Developers](https://developers.mercadolibre.com/) site.

### Installation & Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/eco-friendly-dropshipping-app.git
    cd eco-friendly-dropshipping-app
    ```

2.  **Create and activate a virtual environment (recommended):**
    This isolates the project's dependencies from your global Python installation.
    ```bash
    # For macOS/Linux
    python3 -m venv venv
    source venv/bin/activate

    # For Windows
    python -m venv venv
    venv\Scripts\activate
    ```

3.  **Install the required packages:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables:**
    The application uses environment variables for configuration. You can set them directly in your shell or create a `.env` file in the project root.

    Create a file named `.env` and add the following, replacing the placeholder values:
    ```
    FLASK_SECRET_KEY='a-very-strong-and-secret-key'
    MELI_CLIENT_ID='your_meli_client_id'
    MELI_CLIENT_SECRET='your_meli_client_secret'
    MELI_REDIRECT_URI='http://localhost:5000/callback'
    ```

    **Important:**
    -   The `FLASK_SECRET_KEY` should be a long, random string.
    -   The `MELI_REDIRECT_URI` must **exactly match** one of the redirect URIs you configured in your Mercado Libre application dashboard. For local testing, `http://localhost:5000/callback` is standard. See the section on `ngrok` below if you need a public URL.

## Usage

1.  **Run the Flask application:**
    ```bash
    python3 app.py
    ```
    If your Mercado Libre credentials are not set, you will see a warning in the console.

2.  **Access the application:**
    Open your web browser and navigate to `http://localhost:5000`.

3.  Click the "Login with Mercado Libre" button and authorize the application. You will be redirected back to the app and can start searching for products.

### Local Development with `ngrok`

The Mercado Libre OAuth flow requires a publicly accessible Redirect URI. While `http://localhost:5000/callback` works for local testing, you may need a public URL for testing on other devices or for more advanced scenarios. This project is configured to use `ngrok` to create a secure tunnel to your local server.

1.  **Set the `USE_NGROK` environment variable:**
    Add `USE_NGROK=True` to your `.env` file or export it in your shell.

2.  **Run the app:**
    ```bash
    python3 app.py
    ```
    When the app starts, `ngrok` will activate and print a public URL to your console (e.g., `https://<random-string>.ngrok.io`).

3.  **Update your Mercado Libre Redirect URI:**
    In your Mercado Libre app settings, change your Redirect URI to the public URL provided by `ngrok`, making sure to append `/callback`. For example: `https://<random-string>.ngrok.io/callback`.

4.  **Access the app** using the `ngrok` URL. The authentication flow will now work through the public tunnel.

## Running Tests

The project includes a suite of tests to ensure functionality and prevent regressions.

1.  **Install testing dependencies:**
    The `requirements.txt` file includes `pytest` and `requests-mock`.

2.  **Run the tests:**
    From the root directory of the project, run the following command:
    ```bash
    python3 -m pytest
    ```

## Project Structure

```
.
├── .gitignore          # Specifies intentionally untracked files to ignore.
├── app.py              # Main Flask application logic, routes, and helpers.
├── test_app.py         # Unit and integration tests for the application.
├── requirements.txt    # Python package dependencies for the project.
├── static/             # Static assets (CSS, JavaScript, images).
│   └── style.css
├── templates/          # Jinja2 HTML templates for rendering pages.
│   ├── base.html       # Base template with common structure.
│   ├── index.html      # Home page template.
│   └── products.html   # Product search results page.
└── README.md           # This file.
```

## Contributing

Contributions are welcome! If you have suggestions for improvements or find a bug, please feel free to open an issue or submit a pull request.

1.  Fork the repository.
2.  Create a new branch (`git checkout -b feature/your-feature-name`).
3.  Make your changes.
4.  Commit your changes (`git commit -m 'Add some feature'`).
5.  Push to the branch (`git push origin feature/your-feature-name`).
6.  Open a Pull Request.

## License

This project is licensed under the MIT License.