import json
import sys
import requests

import auth
import conf_local as conf


def main():

    # Collect request details
    details = get_args(sys.argv)
    username = details.get("username")
    method = details.get("method", "get")
    resource = details.get("resource", "/")
    text = details.get("text")

    # Check token file and if tokens are valid
    token_file = f"{username}-tokens.json"
    auth_status = auth.check_auth_status(token_file)

    print(f"Checking login status of {username}")
    if auth_status == False:
        print(f"User not logged in. Run \"auth.py {username}\"")
        sys.exit(1)

    # Get access and identity token
    with open(token_file, "r") as f:
        tokens = json.load(f)
        access_token = tokens.get("AccessToken")
        identity_token = tokens.get("IdToken")

    # Define request headers
    headers = {}
    headers["Authorization"] = f"Bearer {access_token}"
    headers["IdToken"] = identity_token
    headers["Content-Type"] = "application/json"
    headers["Accept"] = "application/json"

    # Make requests based on defined method
    if method.lower() == "get":
        r = requests.get(conf.api + resource, headers = headers)

    if method.lower() == "post":
        body = {"text": text}
        r = requests.post(conf.api + resource, headers = headers, json = body)

    if method.lower() == "delete":
        r = requests.delete(conf.api + resource, headers = headers)

    if "r" in locals():
        print(f"Request status: {r.status_code}")
        
        print(f"Request result:\n{json.dumps(r.json(), indent = 4)}")
    else:
        print(f"Not implemented or not captured for: {username}, {method}, {resource}")

def get_args(args) -> dict:
    result = {}
    if args[1]:
        result["username"] = args[1]

    if len(args) >= 3:
        result["method"] = args[2]

    if len(args) >= 4:
        result["resource"] = args[3]

    if len(args) >= 5:
        result["text"] = args[4]

    return result

if __name__ == "__main__":
    main()
