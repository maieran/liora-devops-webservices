# Important notions on nginx configuration file
PrestaShop assets problem came from the redirecting the requests to a subpath when using the path-based routing `http:\\mydomain.com\prestashop`


However, we have solved this problem in one of three possibly and to us knowingly ways by configuring the nginx as: 
```
location / {
    proxy_pass http://prestashop;
}
```
With above said, we see that our PrestaShop sits at the root now.
This will redirect all paths that were not previously intercepted to PrestaShop, for example:
```
/themes/...
/modules/...
/img/...
/6-accessories
```
This should make the previously missing CSS, JavaScript, and image files accessible.

## Implications

This has two consequences:

PrestaShop effectively owns the entire root namespace.<br>
Even unknown paths are initially routed to PrestaShop.

This is acceptable for the current Compose prototype, but should be documented through testing. <br> 
Before moving to Kubernetes, **_we’ll need to decide later:_** <br>

### Option A:
PrestaShop remains responsible for root paths. (**_Our current choice_**)

### Option B:
PrestaShop is configured entirely under /prestashop/.

### Option C:
WordPress and PrestaShop are assigned their own hostnames. <br>

For the initial test environment, we will test the current behavior without making any changes at this time.


## Proxy details for later use

This line in our nginx configuration:
```
proxy_set_header X-Forwarded-Port $server_port;
```
typically returns port 80 within the container, even though the user is currently using port 8080. <br> 
Therefore, our tests must ensure that generated links still use the correct external host and port.

In addition, the following line:
```
proxy_set_header X-Forwarded-Proto $scheme;
```
may overwrite the original **HTTPS protocol** with **HTTP when a Kubernetes Ingress is placed upstream**, because the connection between the **Ingress and Nginx runs internally over HTTP**. <br> 
This isn't a Compose blocker yet, but it will be added to our Kubernetes compatibility tasks.

## Test Architecture
```
tests/
├── conftest.py
├── requirements-test.txt
│
├── fixtures/
│   └── env/
│       ├── dev.env
│       └── prod.env
│
├── support/
│   ├── __init__.py
│   ├── assets.py
│   ├── compose.py
│   └── urls.py
│
├── unit/
│   ├── test_assets.py
│   └── test_urls.py
│
├── config/
│   ├── test_compose_config.py
│   └── test_nginx_config.py
│
├── integration/
│   ├── test_health.py
│   ├── test_routes.py
│   ├── test_redirects.py
│   └── test_assets.py
│
├── runtime/
│   └── test_compose_runtime.py
│
└── run-tests.sh
```

At the root of folder structure, we are having:
```
pyproject.toml
```

The project document requires at least unit tests and recommends integration, API, and end-to-end tests.<br> 
The tests must be run later in the CI/CD pipeline before build, push, and deployment.