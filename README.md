# Eco-Friendly Product Search App

This is a simple web application built with Flask that allows users to search for eco-friendly products on Mercado Libre. It serves as a demonstration of how to integrate with the Mercado Libre API, handle its OAuth2 authentication flow, and display data to users.

The application focuses on providing a clean, straightforward example of a third-party API integration in a Python web framework.

## Features

-   **OAuth2 Authentication**: Securely authenticates users via their Mercado Libre accounts using the standard OAuth2 authorization code flow.
-   **API Integration**: Searches for products on the Mercado Libre marketplace using its public API.
-   **Session Management**: Uses Flask's session handling to maintain a user's authentication state.
-   **Token Refresh**: Includes logic to automatically refresh expired access tokens using a refresh token, ensuring a seamless user experience.
-   **Clear Structure**: Organized with a standard Flask project layout, making it easy to understand and extend.

## Getting Started

Follow these instructions to get a copy of the project up and running on your local machine for development and testing.

### Prerequisites

-   Python 3.7+
-   `pip` for installing Python packages
-   A Mercado Libre developer account to obtain API credentials. You can create one on the [Mercado Libre Developers](https://developers.mercadolibre.com/) site.

### Installation & Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/eco-friendly-dropshipping-app.git
    cd eco-friendly-dropshipping-app
    ```

2.  **Create and activate a virtual environment (recommended):**
    This isolates the project's dependencies from your system's Python installation.
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
    The application requires API credentials and a secret key to run. These are configured via environment variables.

    **On macOS/Linux:**
    ```bash
    export FLASK_SECRET_KEY='a-very-strong-and-secret-key'
    export MELI_CLIENT_ID='your_meli_client_id'
    export MELI_CLIENT_SECRET='your_meli_client_secret'
    export MELI_REDIRECT_URI='http://localhost:5000/callback'
    ```

    **On Windows (Command Prompt):**
    ```bash
    set FLASK_SECRET_KEY="a-very-strong-and-secret-key"
    set MELI_CLIENT_ID="your_meli_client_id"
    set MELI_CLIENT_SECRET="your_meli_client_secret"
    set MELI_REDIRECT_URI="http://localhost:5000/callback"
    ```

    **Important:**
    - Replace the placeholder values with your actual Mercado Libre credentials.
    - The `FLASK_SECRET_KEY` should be a long, random string.
    - The `MELI_REDIRECT_URI` must exactly match one of the redirect URIs you configured in your Mercado Libre application dashboard.

## Usage

1.  **Run the Flask application:**
    ```bash
    python3 app.py
    ```
    You should see a warning if your Mercado Libre credentials are not set.

2.  **Access the application:**
    Open your web browser and navigate to `http://localhost:5000`.

3.  Click the "Login with Mercado Libre" button and authorize the application. You will be redirected back to the app and can start searching for products.

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

This project is licensed under the MIT License - see the LICENSE.md file for details (if applicable).