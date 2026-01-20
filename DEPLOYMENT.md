# TokenEye Deployment Guide (Single EC2 Instance)

This guide provides steps to deploy TokenEye on a single AWS EC2 instance. This setup hosts both the **FastAPI application** and the **PostgreSQL database** on the same server, simplifying the architecture for testing and demonstration.

---

## 1. Launch EC2 Instance

1. **Log in** to the AWS Console and navigate to **EC2**.
2. Click **Launch instance**.
3. **Name**: `TokenEye-Server`.
4. **OS**: Amazon Linux 2023 or Ubuntu 22.04 LTS.
5. **Instance Type**: `t3.small` (recommended) or `t2.micro` (free tier, but may be slow for processing).
6. **Key Pair**: Select an existing key or create a new one (`.pem`).
7. **Security Group**:
   - Allow **SSH** (Port 22) from your IP.
   - Allow **Custom TCP** (Port 8000) from anywhere (or your IP).
8. **Storage**: 20 GB (General Purpose SSD).
9. Click **Launch**.

---

## 2. Server Setup

Connect to your instance via SSH:

```bash
ssh -i "your-key.pem" ec2-user@YOUR_INSTANCE_IP
```

### Install Dependencies

```bash
sudo apt-get update -y
sudo apt-get install git postgresql postgresql-contrib -y
```

---

## 3. Database Setup (Local PostgreSQL)

1. **Start & Enable PostgreSQL**:

   ```bash
   sudo systemctl start postgresql
   sudo systemctl enable postgresql
   ```

2. **Configure Database**:
   ```bash
   sudo -u postgres psql
   ```
   Inside the PostgreSQL prompt:
   ```sql
   CREATE DATABASE tokenscout;
   CREATE USER ayomide WITH PASSWORD 'your_secure_password';
   GRANT ALL PRIVILEGES ON DATABASE tokenscout TO ayomide;
   \q
   ```

---

## 4. Application Setup

1. **Clone the Repository**:

   ```bash
   git clone https://github.com/OkeAyomidePeter/TokenEye.git
   cd TokenEye
   ```

2. **Setup with uv**:
   Since you already have `uv` installed:

   ```bash
   # Create a virtual environment and install dependencies
   uv venv
   source .venv/bin/activate
   uv pip install -r requirements.txt
   ```

3. **Configure Environment Variables**:
   ```bash
   cp .env.example .env
   nano .env
   ```
   Update the following in `.env`:
   - `DATABASE_URL=postgresql+psycopg2://ayomide:your_secure_password@localhost:5432/tokenscout`
   - `TELEGRAM_BOT_TOKEN=...`
   - `HELIUS_API_KEY_1=...`

---

## 5. Running the Application

### Using Screen (Simple)

To keep the app running after you disconnect:

```bash
screen -S tokeneye
source venv/bin/activate
python run.py
# Press Ctrl+A, then D to detach
```

### Using Systemd (Recommended for Production)

Create a service file:

```bash
sudo nano /etc/systemd/system/tokeneye.service
```

Paste the following:

```ini
[Unit]
Description=TokenEye FastAPI Service
After=network.target postgresql.service

[Service]
User=ec2-user
WorkingDirectory=/home/ec2-user/TokenEye
ExecStart=/home/ec2-user/TokenEye/.venv/bin/python run.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl start tokeneye
sudo systemctl enable tokeneye
```

---

## 6. Verification

Visit `http://YOUR_INSTANCE_IP:8000/` in your browser. You should see `{"status":"ok"}`.
Check logs using:

```bash
journalctl -u tokeneye -f
```
