import boto3
import json
import pathlib
import jwt
import sys
import time

import conf_local

def main():
    """ USAGE
    (.venv) $ python auth.py <username>
    """

    user_name = sys.argv[1]

    if not user_exists(user_name):
        print(f"User {user_name} does not exist here.")
        sys.exit(1)

    filename = f"{user_name}-tokens.json"

    print("Checking auth status")
    auth_status = check_auth_status(filename)

    if auth_status == False:
        print(f"{user_name} is not authenticated. Authenticating now...")
        auth_status = authenticate_user(user_name)
    
    if auth_status == True:
        print(f"{user_name} is authenticated and token is valid for at least two minutes. Stored tokens in\n{filename}")
    else:
        print(f"The lights are on but noone is home.")


def authenticate_user(user_name) -> bool:

    cognito = boto3.client("cognito-idp")

    response = cognito.initiate_auth(
        AuthFlow = "USER_PASSWORD_AUTH",
        AuthParameters = {
            "USERNAME": user_name,
            "PASSWORD": conf_local.users.get(user_name)
        },
        ClientId = conf_local.cognito_client_id
    )

    result = response.get("AuthenticationResult")

    if result.get("AccessToken") and result.get("IdToken"):
        filename = f"{user_name}-tokens.json"
        with open(filename, mode="w") as f:
            f.write(json.dumps(result))

        return True

    return False


def check_auth_status(filename) -> bool:
    try:
        with open(filename, mode="r") as f:
            tokens = json.load(f)

    except FileNotFoundError:
        return False

    access_token = tokens.get("AccessToken")

    if access_token:
        decoded_data = jwt.decode(jwt=access_token, options={"verify_signature": False})
        time_now = int(time.time())
        exp_time = decoded_data.get("exp")

        # Checking, if token is valid for at least two minutes
        if exp_time - time_now < 120:
            return False

        return True

    return False


def user_exists(user_name) -> bool:
    if conf_local.users.get(user_name):
        return True

    return False


if __name__ == "__main__":
    main()
