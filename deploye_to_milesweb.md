python

source virtualenv/quantleap/3.13/bin/activate

## .htaccess

Do NOT upload a `.htaccess` file to the app's public root on Milesweb.
cPanel's Setup Python App (Python Selector) already configures Passenger
routing at the vhost level for this domain. Adding `.htaccess` with
`PassengerEnabled`/`PassengerAppType`/rewrite directives conflicts with that
vhost config and causes every request to 500 with a generic LiteSpeed error
page, regardless of what else is in the file. Confirmed 2026-07-12: removing
`.htaccess` entirely fixed health check, CORS preflight, and login — all
worked correctly with no `.htaccess` present.
