# Eco-Friendly Product Search App

This is a simple web application built with Flask that allows users to search for eco-friendly products on Mercado Libre. It demonstrates how to integrate with the Mercado Libre API, handle OAuth2 authentication, and display search results.

## Features

-   **OAuth2 Authentication**: Securely authenticates users with their Mercado Libre accounts.
-   **Product Search**: Allows authenticated users to search for products.
-   **Session Management**: Manages user sessions to keep them logged in.
-   **Token Refresh**: Automatically refreshes expired access tokens.
-   **Responsive Design**: Basic responsive design that works on different screen sizes.

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

-   Python 3.6+
-   pip for installing Python packages
-   A Mercado Libre developer account to get API credentials.

### Installation

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/your-username/eco-friendly-dropshipping-app.git
    cd eco-friendly-dropshipping-app
    ```

2.  **Create and activate a virtual environment (recommended):**

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3.  **Install the required packages:**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up environment variables:**

    You need to get your `CLIENT_ID` and `CLIENT_SECRET` from the Mercado Libre developer dashboard.

    Create a `.env` file in the root of the project and add the following variables:

    ```
    FLASK_SECRET_KEY='a-super-secret-key'
    MELI_CLIENT_ID='your_meli_client_id'
    MELI_CLIENT_SECRET='your_meli_client_secret'
    MELI_REDIRECT_URI='http://localhost:5000/callback'
    ```

    **Note:** For development, you can use `ngrok` to expose your local server to the internet and get a public URL for the `REDIRECT_URI`. If you use `ngrok`, set the `USE_NGROK=true` environment variable.

## Usage

1.  **Run the application:**

    ```bash
    python app.py
    ```

2.  **Open your browser and navigate to:**

    ```
    http://localhost:5000
    ```

3.  **Log in with your Mercado Libre account.**

4.  **Search for eco-friendly products.**

## Project Structure

```
.
├── app.py              # Main Flask application file
├── requirements.txt    # Python package dependencies
├── static/             # Static files (CSS, JS, images)
│   └── style.css
├── templates/          # HTML templates
│   ├── base.html
│   ├── index.html
│   └── products.html
└── README.md
```
