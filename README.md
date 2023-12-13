# What is this about?
This a small application to demo Amazon Verified Permissions. The application is a simplified social media platform, on which users can create text posts. Check the app design doc for the different assumptions.

# Achitecture overview
![Architecture diagram](docs/architecture.svg)
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

# Create users in Cognito to test authN and authZ

```
USER_POOL_ID=<retrieve_from_stack_outputs>
USER_NAME=<some_username>

aws cognito-idp admin-create-user --user-pool-id $USER_POOL_ID --username $USER_NAME
```
Users are required to reset their password when they login for the first time - to prevent it, run:

```
USER_PW=<some_password>
aws cognito-idp admin-set-user-password --user-pool-id $USER_POOL_ID --username $USER_NAME --password $USER_PW --permanent
```
Users can be assigned a special "appRole" attribute. As of now the only value considered is "admin". Assign the attribute to an existing user:

```
aws cognito-idp admin-update-user-attributes --user-pool-id $USER_POOL_ID --username $USER_NAME --user-attributes "Name=custom:appRole,Value=admin"
```
Note: The user needs to acquire a fresh identity token, once the attribute is set!

# Test this
Stuff for testing lives in the ./scipts directory. Requirements are installed with the core requirements for cdk. First, copy the conf.py to a file called conf_local.py and populate it with details from the steps before. You can then use the scripts to:
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
