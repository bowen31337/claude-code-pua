# deploy-config

Config resolution for our services. Run with:

    APP_ENV=staging python3 main.py

Precedence is supposed to be: real env vars > environment yaml > baked defaults.
