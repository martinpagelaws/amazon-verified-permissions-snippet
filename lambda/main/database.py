import boto3
import os
import time
import uuid

from boto3.dynamodb.conditions import Key

table_name = os.environ.get("TableName")

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(table_name)


def get_post_details(postid):
    post = table.query(
        IndexName = "postid_time_index",
        KeyConditionExpression = Key("postId").eq(postid)
    )

    if post:
        return post["Items"]

    return None


def get_all_posts():
    items = table.scan()["Items"]

    return [item for item in items]


def get_user_posts(author):
    items = table.query(
        IndexName = "author_postid_index",
        KeyConditionExpression = Key("author").eq(author)
    )["Items"]

    return items


def create_post(userid, text, author):
    timestamp = str(int(time.time()))
    post_id = str(uuid.uuid4())

    attributes = table.put_item(
        Item = {
            "userId": userid,
            "time": timestamp,
            "text": text,
            "postId": post_id,
            "author": author
        }
    )#["Attributes"]

    return attributes


def delete_post(post_owner, postid):
    table.delete_item(
        Key = {"userId" : post_owner, "postId": postid}
    )

    return "Done"
