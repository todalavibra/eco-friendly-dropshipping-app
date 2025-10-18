# Eco-Friendly Product Search App

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A demonstration Flask web application that allows users to search for eco-friendly products on Mercado Libre. It showcases a complete integration with the Mercado Libre API, including OAuth2 authentication, token management, and product searching.

> **Live Demo:** [Link to your live demo here]

## Purpose

This application serves as a clear, well-documented example for developers looking to work with third-party APIs in a Python web framework. It provides a practical guide to:

-   Implementing a full OAuth2 authorization code flow.
-   Managing access and refresh tokens.
-   Making authenticated API requests.
-   Structuring a simple Flask application.
-   Writing comprehensive tests with `pytest` and `requests-mock`.

## Features

-   **OAuth2 Authentication**: Securely authenticates users via their Mercado Libre accounts.
-   **API Integration**: Searches for products on the Mercado Libre marketplace.
-   **Session Management**: Uses Flask's server-side sessions to maintain user authentication state.
-   **Automatic Token Refresh**: Includes logic to automatically refresh expired access tokens, ensuring a seamless user experience.
-   **Local Development Tunneling**: Integrated with `pyngrok` to simplify testing of OAuth2 callbacks during local development.
-   **Comprehensive Test Suite**: Comes with a full suite of unit and integration tests.

## Getting Started

Follow these instructions to get the project running on your local machine.

### Prerequisites

-   Python 3.7+
-   `pip` for installing Python packages.
-   A Mercado Libre developer account. You can create one on the [Mercado Libre Developers](https://developers.mercadolibre.com/) site.

### Installation & Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/eco-friendly-dropshipping-app.git
    cd eco-friendly-dropshipping-app
    ```

2.  **Create and activate a virtual environment:**
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
    The application requires environment variables for configuration. Create a `.env` file in the project root and add the following, replacing the placeholder values:

    ```
    FLASK_SECRET_KEY='a-very-strong-and-secret-key'
    MELI_CLIENT_ID='your_meli_client_id'
    MELI_CLIENT_SECRET='your_meli_client_secret'
    MELI_REDIRECT_URI='http://localhost:5000/callback'
    ```

    **Important Notes:**
    -   The `FLASK_SECRET_KEY` should be a long, random string for security.
    -   The `MELI_REDIRECT_URI` must **exactly match** one of the redirect URIs you configured in your Mercado Libre application dashboard.

## Usage

1.  **Run the Flask application:**
    ```bash
    python3 app.py
    ```
    If your Mercado Libre credentials are not set, you will see a warning in the console, and authentication will fail.

2.  **Access the application:**
    Open your web browser and navigate to `http://localhost:5000`.

3.  Click the "Login with Mercado Libre" button to authorize the application. You will be redirected back to the app and can start searching for products.

### Local Development with `ngrok`

The Mercado Libre OAuth flow requires a publicly accessible Redirect URI. This project is configured to use `ngrok` to create a secure tunnel to your local server for easy development.

1.  **Set the `USE_NGROK` environment variable:**
    Add `USE_NGROK=True` to your `.env` file or export it in your shell.

2.  **Run the app:**
    ```bash
    python3 app.py
    ```
    When the app starts, `ngrok` will activate and print a public URL to your console (e.g., `https://<random-string>.ngrok.io`).

3.  **Update your Mercado Libre Redirect URI:**
    In your Mercado Libre app settings, change your Redirect URI to the public URL provided by `ngrok`, making sure to append `/callback`. For example: `https://<random-string>.ngrok.io/callback`.

4.  **Access the app** using the `ngrok` URL to test the full authentication flow.

## Running Tests

The project includes a comprehensive test suite to ensure functionality and prevent regressions.

1.  **Install testing dependencies:**
    The `requirements.txt` file includes `pytest` and `requests-mock`.

2.  **Run the tests:**
    From the root of the project, run the following command:
    ```bash
    python3 -m pytest
    ```

## Project Structure

```
.
├── .gitignore          # Specifies intentionally untracked files to ignore.
├── app.py              # Main Flask application logic, routes, and helpers.
├── test_app.py         # Unit and integration tests for the application.
├── requirements.txt    # Python package dependencies.
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

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.