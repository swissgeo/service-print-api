#!/bin/bash

random_payload=$(head -200 /dev/urandom | cksum | cut -f1 -d " ")
state=$(printf '{"center":[2600000,1200000],"bgLayer":"ch.swisstopo.pixelkarte-farbe","layers":"ch.meteoschweiz.messwerte-niederschlag-1d","z":7,"random":'"${random_payload}"'}' | base64 -w 0)
body=$(printf '{"print_format":"a4","print_orientation":"landscape","print_resolution":96,"print_scale":25000,"state":"%s"}' "${state}")

curl -i --location --request POST 'http://localhost:3000/api/wps/v1/print/jobs' \
--header 'Content-Type: application/json' \
--data-raw "${body}"
