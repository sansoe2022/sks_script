#!/bin/bash

# Credit to https://gist.github.com/Tras2/cba88201b17d765ec065ccbedfb16d9a
# A bash script to update a Cloudflare DNS A record with the external IP of the source machine
# Cloudflare zone is the zone which holds the record

zone=  # the domain name
# dnsrecord is the A record which will be updated
dnsrecord= # the domain name

## Cloudflare authentication details
## keep these private
cloudflare_auth_email="youremail@wherever.com" # the one you use to login at Cloudlfare
# cloudflare_auth_token="The auth token you generated from within cloudflare specific to this domain"
cloudflare_auth_key=84bc9ca4ljasdff80asdffasdf23234%asdfasd  # the Global API key from cloudflare

# Get the current external IP address
ip=$(dig +short myip.opendns.com @resolver1.opendns.com)

echo "Current IP is $ip"

if host $dnsrecord 1.1.1.1 | grep "has address" | grep "$ip"; then
  echo "$dnsrecord is currently set to $ip; no changes needed"
  return
fi

# if here, the dns record needs updating

# get the zone id for the requested zone
zoneid=$(curl -s -X GET "https://api.cloudflare.com/client/v4/zones?name=$zone&status=active" \
  -H "X-Auth-Email: $cloudflare_auth_email" \
  -H "X-Auth-Key: $cloudflare_auth_key" \
  -H "Content-Type: application/json" | jq -r '{"result"}[] | .[0] | .id')

echo "Zoneid for $zone is $zoneid"

# get the dns record id
dnsrecordid=$(curl -s -X GET "https://api.cloudflare.com/client/v4/zones/$zoneid/dns_records?type=A&name=$dnsrecord" \
  -H "X-Auth-Email: $cloudflare_auth_email" \
  -H "X-Auth-Key: $cloudflare_auth_key" \
  -H "Content-Type: application/json" | jq -r '{"result"}[] | .[0] | .id')

echo "DNSrecordid for $dnsrecord is $dnsrecordid"

# update the record
curl -s -X PUT "https://api.cloudflare.com/client/v4/zones/$zoneid/dns_records/$dnsrecordid" \
  -H "X-Auth-Email: $cloudflare_auth_email" \
  -H "X-Auth-Key: $cloudflare_auth_key" \
  -H "Content-Type: application/json" \
  --data "{\"type\":\"A\",\"name\":\"$dnsrecord\",\"content\":\"$ip\",\"ttl\":1,\"proxied\":false}" | jq
