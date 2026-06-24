#!/bin/bash

state_id=$(head -c 12 /dev/urandom | basenc --base64url)
state_id=i7ufGBFB5TUN7gnS
#body=$(printf '{"print_format":"a4","print_orientation":"landscape","print_resolution":96,"print_scale":25000,"state_id":"%s","print_legend":true,"print_grid":false,"print_lang":"de"}' "${state_id}")
body=$(printf '{"print_format":"a0","print_orientation":"portrait","print_resolution":96,"print_scale":25000,"state_id":"%s","print_legend":true,"print_grid":false,"print_lang":"de"}' "${state_id}")

#curl -i --location --request POST 'https://www.dev.sgdi.tech/api/wps/v1/print/jobs' \
curl -i --location --request POST 'http://localhost:3000/api/wps/v1/print/jobs' \
--header 'Content-Type: application/json' \
--data-raw "${body}"
