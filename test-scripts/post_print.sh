#!/bin/bash

state_id=$(head -c 12 /dev/urandom | basenc --base64url)
body=$(printf '{"print_format":"a4","print_orientation":"landscape","print_resolution":96,"print_scale":25000,"state_id":"%s","print_legend":true,"print_grid":false,"print_lang":"de"}' "${state_id}")

curl -i --location --request POST 'http://localhost:3000/api/wps/v1/print/jobs' \
--header 'Content-Type: application/json' \
--data-raw "${body}"
