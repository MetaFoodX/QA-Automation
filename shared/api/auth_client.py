"""AWS Cognito authentication for API tests."""

import base64
import requests


COGNITO_URL = "https://cognito-idp.us-west-2.amazonaws.com/"


def get_access_token(username: str, password: str, client_id: str) -> str:
    """Authenticate via Cognito InitiateAuth and return access token.

    The token is valid for 60 minutes — sufficient for a single test session.
    """
    # Basic Auth header: base64(username:password)
    credentials = f"{username}:{password}"
    basic_auth = base64.b64encode(credentials.encode()).decode()

    headers = {
        "x-amz-target": "AWSCognitoIdentityProviderService.InitiateAuth",
        "content-type": "application/x-amz-json-1.1",
        "Authorization": f"Basic {basic_auth}",
    }

    body = {
        "AuthParameters": {
            "USERNAME": username,
            "PASSWORD": password,
        },
        "AuthFlow": "USER_PASSWORD_AUTH",
        "ClientId": client_id,
    }

    response = requests.post(COGNITO_URL, json=body, headers=headers, timeout=30)
    response.raise_for_status()

    data = response.json()
    return data["AuthenticationResult"]["AccessToken"]