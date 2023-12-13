#!/usr/bin/env python3
import os

import aws_cdk as cdk

from cdk.stack import SimplePostsStack 


app = cdk.App()
SimplePostsStack(app, "SimplePostsStack")

app.synth()
