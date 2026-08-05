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


