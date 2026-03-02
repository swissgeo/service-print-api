#!/bin/bash

# TODO finally it all goes over the endpoint jobs
# https://oz7fx3cpky.apidog.io/create-print-job-10282053e0
#curl --location --request POST 'https://map.geo.admin.ch/api/print/jobs' \
random_payload=$(head -200 /dev/urandom | cksum | cut -f1 -d " ")
#random_payload=42
# currently there are 2 views: print_legend and print_map
#view=print_legend
view=print_map
#curl --location --request POST 'https://5jel4tqfhdrsz3yriu3yz7wbvm0poynq.lambda-url.eu-central-1.on.aws/jobs' \
curl -i --location --request POST 'http://localhost:3000/jobs' \
--header 'Content-Type: application/json' \
--data-raw '{
    "format": "a4",
    "orientation": "landscape",
    "resolution": 96,
    "scale": 25000,
    "view": "'${view}'",
    "query": "center=2600000%2C1200000&bgLayer=ch.swisstopo.pixelkarte-farbe&topic=ech&layers=ch.meteoschweiz.messwerte-niederschlag-1d%3Bch.astra.wanderland-sperrungen_umleitungen%3Bch.swisstopo.swisstlm3d-wanderwege&z=7&random='${random_payload}'"
}'
