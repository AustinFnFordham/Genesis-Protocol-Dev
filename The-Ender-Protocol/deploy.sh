#!/bin/bash

# Deploy The Ender Protocol Lambda functions
sam build
sam deploy --guided --stack-name ender-protocol
