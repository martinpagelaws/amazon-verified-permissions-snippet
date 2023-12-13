import json
import jwt

import actions
import database
import permissions


def handler(event, context):

    """
    Retrieve event details
    """


    print(f"EVENT DETAILS\n{event}")

    parameters = event.get("queryStringParameters")
    headers = event["headers"]
    print(f"HEADERS\n{headers}")

    request_details = event.get("routeKey").split(" ")
    path_params = event.get("pathParameters")


    """
    Define principal, action and method from request details
    """

    # Get action and resource from the actual API call

    resource = request_details[1]
    method = request_details[0]
    print(f"RESOURCE\n{resource}\nMETHOD\n{method}")


    # Map API call to available actions

    action = actions.ACTIONS.get((resource, method), "Unknown")
    if action == "Unknown":
        return format_response({"message": "Unknown API call"}, 404)


    # Get user details from tokens

    access_token = headers.get("authorization").split(" ")[1]
    print(f"ACCESS TOKEN\n{access_token}")

    identity_token = headers.get("idtoken")
    print(f"IDENTITY TOKEN\n{identity_token}")

    jwt_claims = jwt.decode(access_token, options = {"verify_signature": False})
    print(f"JWT CLAIMS\n{jwt_claims}")

    userid = f"{jwt_claims.get('iss').split('/')[3]}|{jwt_claims.get('sub')}"
    author = f"{jwt_claims.get('username')}|{jwt_claims.get('sub')[:8]}"


    # Setting some defaults in case they are not set in the request

    postid = None
    text = None
    post_owner = None
    post_details = None


    # Override defaults in case they are set in the request

    if path_params:
        postid = path_params.get("postId")

    if parameters:
        author = parameters.get("author") if "author" in parameters else author

    if postid:
        post_details = database.get_post_details(postid)[0]
        print(post_details)

        if not post_details:
            return format_response({"message": "Invalid input, item does not exist"}, 400)

        post_owner = post_details.get("userId")


    """
    Authorize the request - return 401 if check fails
    """

    if permissions.check_permission(identity_token, action, post_details) == "DENY":
        return format_response({"message": "Access denied - permission check failed"}, 401)


    """
    Capture optional request details
    """

    if event.get("body"):
        body = json.loads(event.get("body"))
        print(f"JSON BODY\n{body}")
        text = body.get("text") if "text" in body else None

    print(f"TEXT\n{text}")


    """
    Send request to the database
    """

    if action == "GetAllPosts":
        return get_all_posts()

    if action == "GetUserPosts":
        return get_user_posts(author)

    if action == "CreatePost":
        if not text:
            return format_response({"message": "Invalid input, text required."}, 400)

        return create_post(userid, text, author)

    if action == "DeletePost":
        return format_response({"message": delete_post(post_owner, postid)})

    return format_response({"message": "nothing to do but everything alright - or is it?"})


"""
Helper functions for the database to keep main function clean
"""


def get_all_posts():
    return database.get_all_posts()


def get_user_posts(author):
    return database.get_user_posts(author)


def create_post(userid, text, author):
    return database.create_post(userid, text, author)


def delete_post(post_owner, postid):
    return database.delete_post(post_owner, postid)


def format_response(body, status_code = 200):
    result = {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps(body)
    }

    return result
