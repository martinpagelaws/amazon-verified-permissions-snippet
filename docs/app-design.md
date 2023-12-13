# Simple Posts App Design

## Permission assumptions

* any authenticated user can publish text snippets, called posts
* any authenticated user can see all the posts that have been published on the platform
* post owners can delete posts
* users can have an "appRole" attribute: admin
* users with the admin appRole can delete any post. But they cannot create any.

## Data format of the posts
```json
{
    "time": "<epoc_timestamp>",
    "text": "<some_text>",
    "postId": "<uuid>",
    "userId": "<user_pool_id>|<user_sub>",
    "author": "<username>|<first_four_chars_of_sub>"
}
```
All data is stored in DynamoDB
* userId is the partition key and defines ownership over a post
* postId is the sort key
* author is a small handle that is derived from the sub, so we can query for posts by a specific user, without exposing the userId in the front-end

## Using the application
* `GET /` - returns all existing posts
* `GET /posts?author=<author_tag>` - returns all posts of the specified author
* `POST /posts` - creates a new post, requires json body `{"text": <post content>}`
* `DELETE /posts/<postId>` - deletes a post
