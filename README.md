# Disclaimer
Some of the design choices are purely based on the goal to keep this as simple as possible. Do not run this anywhere near production and especially not with real user data / personal identifiable information. Feel free to reach out, if you want to discuss options to move forward with a version that could exist in the real world.

# What is this about?
This is a small application to demo Amazon Verified Permissions. The application is a simplified social media platform, on which users can create text posts. Check the `docs/app-design.md` for all assumptions and design decisions. If you just want to dig into the code, check the [Inspect the code](#inspect-the-code) section.

# Achitecture overview
![Architecture diagram](docs/architecture.svg)
* all requests need to go through the API Gateway
* all requests need to include access- and identity-token in the header (refer to the "See how it works" section below) - that means a user needs to acquire those credentials before making any request
* users are managed with Amazon Cognito - credentials can be acquired by calling the initiateAuth API of Cognito
    * the access token is used to authorize the request on the API Gateway layer
    * the access token is also used to identify the calling user on the application layer
    * the identity token is used to authorize the request with Amazon Verified Permissions on the application layer
* the application layer is an AWS Lambda Function, which handles all API requests, authorizes them with Verified Permissions and returns the results as json
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
## Make some calls and observe behavior
The `scripts/` directory contains what could be considered the front-end application. A front-end that lives in your commandline. Requirements are installed with the core requirements for cdk. 

First, copy the `conf.py` to a file called `conf_local.py` and populate it with details from the steps before. 

You can then use the scripts to:
* authenticate a user, e.g. alice, run `$ python auth.py alice`
* make an api call with this pattern - `$ python  api_call.py <username> <method> <api_route> "<some_text>"` - only username is required, rest optional and depends on what you want to do. Here are some examples:
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

## Inspect the code
* start at the `lambda/main/main.py` - the entry point for all requests
* observe how the request details are captured from the event and how principal, action and resource are defined
* observe how the function returns early, if the permission check fails by checking for the "DENY" string in the authorization result
* navigate to `lambda/main/permissions.py` to see how the request to Verified Permissions is constructed
* all policies are managed with CDK - check the `cdk/policy_store` directory:
    * the schema.json specifies what kind of principals, actions and resources with what kind of attributes can exist in the context of the Verified Permissions policy store - schema validation is set to STRICT in this example so when you want to create new policies, you need to make sure that they adhere to the schema; otherwise the creation will fail
    * the `.cedar` files contain the actual policies - they define what is possible and what not; refer to the `docs/app-design.md` to understand the assumptions behind the policies
    * there is one policy that explicitely denies a certain action from happening - this is to show how policies are evaluated:
        * an explicit deny (forbid) beats any explicit allow (permit)
        * there is no implicit allow - anything you want to allow needs to be specified with a permit statement

## A note on pricing
Everything is serverless. Billing is influenced by how many requests are done and how many microseconds the Lambda function runs. When you run this to check out the moving parts, with a couple of hundred requests in a month, you should not expect to see anything above 1$ in your bill for all the components combined.

If you want to understand what this would look like in a real world scenario, you can take your expected request rate, go to the [calculator](https://calculator.aws) and add the services, which are mentioned in the architecture overview.
