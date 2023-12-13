import boto3
import os

from typing import Optional

avp_client = boto3.client("verifiedpermissions")
policy_store_id = os.environ.get("PolicyStoreId")


def format_entity(entity_type, entity_id):
    return {"entityType": f"SimplePosts::{entity_type}", "entityId": entity_id}


def format_action(action_id):
    return {"actionType": "SimplePosts::Action", "actionId": action_id}


def check_permission(token: str, action: str, resource:Optional[dict]) -> bool:

    user_action = format_action(action)
    requested_resource = format_entity("Application", "app")
    print("PERMISSION CHECK:")
    print(f"ACTION {user_action}")
    print(f"DEFAULT RESOURCE: {requested_resource}")

    args = {
        "policyStoreId": policy_store_id,
        "identityToken": token,
        "action": user_action,
        "resource": requested_resource
    }
    print(f"DEFAULT ARGS: {args}")

    if resource:
        requested_resource = format_entity("Post", resource.get("postId"))
        entities = {
            "entityList": [
                {
                    "identifier": requested_resource,
                    "attributes": {
                        "owner": {
                            "entityIdentifier": format_entity("User", resource.get("userId"))
                        }
                    }
                }
            ]
        }
        args["entities"] = entities

        args["resource"] = requested_resource
        print(f"ARGS WITH RESOURCE: {args}")

    avp_response = avp_client.is_authorized_with_token(**args)

    print(f"FULL AVP RESPONSE: {avp_response}")

    return avp_response.get("decision")
