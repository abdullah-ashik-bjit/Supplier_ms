# Docker Setup for `supplier_ms` Odoo 17 Custom Module

---

## Project Structure

```
docker-setup/
│── config/
│   ├── odoo.conf         # Odoo configuration file
│── enterprise/           # Odoo 17 Enterprise source code
│── supplier_ms/          # Custom module directory
│   ├── .gitignore        # Git ignore file
│   ├── docker-compose.yaml  # Docker Compose configuration
│   ├── Dockerfile        # Dockerfile for Odoo setup
│   ├── nginx.conf        # Nginx reverse proxy configuration
```

---


### Prerequisites

Ensure you have the following installed:

- **Docker**
- **Docker Compose**

---

### Setup & Installation

1. **Clone or navigate to the project directory:**
   ```bash
   cd /path/to/docker-setup
   ```

2. **Build the Docker image:**
   ```bash
   docker build .
   ```

3. **Start the containers using Docker Compose:**
   ```bash
   docker-compose up -d
   ```

4. **Access Odoo 17 Enterprise:**
   - Open your browser and go to: [http://localhost](http://localhost)
   - Odoo will be running on **port 8017** as per `nginx.conf`.

---

## Configuration Details

### Odoo Configuration (`config/odoo.conf`)

The `odoo.conf` file contains database and XML-RPC configurations:

```ini
[options]
admin_passwd = Bjit#1234
db_host = db
db_port = 5432
db_user = odoo
db_password = odoo
xmlrpc_port = 8017
addons_path = /mnt/odoo_17.0+e.latest/odoo-17.0+e.20240903/odoo/addons,/mnt/extra-addons
```

---

### Reverse Proxy Setup (`supplier_ms/nginx.conf`)

Nginx is configured as a reverse proxy to forward requests to the Odoo instance:

```nginx
server {
    listen 80;
    server_name localhost;

    location / {
        proxy_pass http://odoo-app:8017;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 720s;
        proxy_connect_timeout 720s;
    }
}
```

---

## Managing Containers

### Restart Odoo
```bash
docker-compose restart odoo
```

### Stop Containers
```bash
docker-compose down
```

### View Logs
```bash
docker-compose logs -f
```

---

## Notes

- The **Enterprise edition of Odoo 17** should be placed inside the `enterprise/` folder. And mapped the path accodingly in Dockerfile for copying.
- The custom module **supplier_ms** should be inside `supplier_ms/` and mapped in `addons_path`.
- Ensure correct database credentials in `odoo.conf`.

---

