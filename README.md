# Disclaimer
Some of the design choices are purely based on the goal to keep this as simple as possible. Do not run this anywhere near production and especially not with real user data / personal identifiable information. Feel free to reach out, if you want to discuss options to move forward with a version that could exist in the real world.

# What is this about?
This is a small application to demo Amazon Verified Permissions. The application is a simplified social media platform, on which users can create text posts. Check the `docs/app-design.md` for all assumptions and design decisions.

# Achitecture overview
![Architecture diagram](docs/architecture.svg)
* all requests need to go through the API Gateway
* all requests need to include access and identity token in the header (refer to the "See how it works" section below) - that means a user needs to acquire those credentials before making any request
 * the access token is used to authorize the request on the API Gateway layer
 * the identity token is used to authorize the request with Amazon Verified Permissions on the application layer
* an AWS Lambda Function handles all API requests, authorizes them with Verified Permissions and returns the results in json
* all data is stored in an Amazon DynamoDB table

# Deploy this stack

## Install layer files first
```
pip install -r ./lambda/main/requirements.txt --target ./layers/main/python --only-binary=":all:" --platform manylinux2014_x86_64
```
## Prepare Python environment
```
$ python3 -m venv .venv

$ . .venv/bin/activate

$ pip install -r requirements.txt
```

## Deploy
If you use an aws cli profile, specify it in your env: `export AWS_PROFILE=<yourprofile>`
```
$ cdk deploy
```

# Create users in Cognito to be able to run requests against the API

```
USER_POOL_ID=<retrieve_from_stack_outputs>
USER_NAME=<some_username>

aws cognito-idp admin-create-user --user-pool-id $USER_POOL_ID --username $USER_NAME
```
By default, Cognito users are required to reset their password when they login for the first time - to prevent this behavior, run:

```
USER_PW=<some_password>
aws cognito-idp admin-set-user-password --user-pool-id $USER_POOL_ID --username $USER_NAME --password $USER_PW --permanent
```
Users can be assigned a special "appRole" attribute. As of now the only value considered is "admin". Assign the attribute to an existing user:

```
aws cognito-idp admin-update-user-attributes --user-pool-id $USER_POOL_ID --username $USER_NAME --user-attributes "Name=custom:appRole,Value=admin"
```
Note: The user needs to acquire a fresh identity token, once the attribute is set!

# See how it works
The `./scipts` directory contains what could be considered the front-end application. A front-end that lives in your commandline. Requirements are installed with the core requirements for cdk. 

First, copy the conf.py to a file called conf_local.py and populate it with details from the steps before. 

You can then use the scripts to:
* authenticate a user, e.g. alice, run `$ python auth.py alice`
* make an api call with this pattern - `$ python  api_call.py <username> <method> <api_route> "<some_text>"` (only username is required, rest optional and dependend on what you want to do - yes, very dirty setup, not meant to stay). Here are some examples:
	* get all posts as alice: `$ python api_call.py alice`
	* create a new post as alice `$ python api_call.py alice post /posts "My first post"`
	* get posts from bob as alive `$ python api_call.py alice get "/posts?author=<bobs author tag>"`
	* delete a post `$ python api_call.py alice delete "/posts/<postId>"`

If you want to use curl, make sure to set these headers (access and identity token can be found in a local json file after running auth.py script):
```
Authorization: Bearer <access_token>
IdToken: <identity_token>
Content-Type: application/json
```
