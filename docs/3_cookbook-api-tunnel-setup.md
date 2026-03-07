# Create a Stable Named Tunnel for Cloudflared

Finish the named tunnel setup once, so indie-pigeon-api works every time.

## 1) Login to Cloudflare from your current machine
Run:
```
cloudflared tunnel login
```

This should open a browser. Choose your Cloudflare account and authorize the zone/domain name you are working with.

When it succeeds, **cloudflared** will download a cert file, usually here:
> ~/.cloudflared/cert.pem

## 2) Verify the cert exists

Run:
```
ls ~/.cloudflared
```
You should see **cert.pem** plus any tunnel credential json files.

## 3) Create a New Tunnel or Verify existing  

### 3.1 Create a tunnel exists
Run:
```
cloudflared tunnel create indie-pigeon-api
```
Expected result: Cloudflared will create the tunnel and output:
- the tunnel UUID
- the credentials file path
Example:
> Tunnel credentials written to /Users/dee/.cloudflared/<TUNNEL_ID>.json
This JSON file is required to run the named tunnel from your current machine later.

### 3.2 Verify the tunnel exists

Run:
```bash
cloudflared tunnel list
```

## 4) Reserve and configure an API subdomain.domain to attach the Tunnel

Run:
```
cloudflared tunnel route dns indie-pigeon-api api.unschooldiscoveries.com
```

Expected output on terminal #2 
>Added CNAME api.unschooldiscoveries.com which will route to this tunnel tunnelID=<ID CHAIN DISPLAYED>
You can also confirm on the Cloudflare dash in Tunnels. 

The Tunnel is now Routed to the production subdomain
> indie-pigeon-api : api.unschooldiscoveries.com

Confirm it is connected 
Run:
```
cloudflared tunnel list
```
You should see:
>ID                                   NAME             CREATED              CONNECTIONS 
> <ID CHAIN DISPLAYED> indie-pigeon-api

## 5) Create the Config File

### Get your json file from the cert.perm 
Run:
```
ls ~/.cloudflared
```
ou should see:
> cert.pem
> one long .json filename
Copy the .json filename.

### Create the config file
Run:
```
nano ~/.cloudflared/config.yml
```

**A YAML text editor will open**
Edit & Paste `PASTE-YOUR-TUNNEL-JSON-FILENAME-HERE` with the copied .json file
YAML
```
tunnel: indie-pigeon-api
credentials-file: /Users/dee/.cloudflared/PASTE-YOUR-TUNNEL-JSON-FILENAME-HERE.json

ingress:
  - hostname: api.unschooldiscoveries.com
    service: http://localhost:8000
  - service: http_status:404
```

Then SAVE by pressing:
> CTRL + O (o not zero)
> Enter Key
> CTRL + X

## 6) Start your app
** This step continues to REQUIRE the 2 terminal workflow **

`Terminal 1:`
bash
```
cd ~/WorkingCode/indie-pigeon
source venv/bin/activate
python -m uvicorn app.main:app --reload --port 8000
```

`Terminal 2:`
**Leave it running.**
bash
```
cloudflared tunnel run indie-pigeon-api
```

## 7) Test It: Try the Tunnel 
Open:
> https://api.unschooldiscoveries.com/health

Expected:
> {"ok": true}

