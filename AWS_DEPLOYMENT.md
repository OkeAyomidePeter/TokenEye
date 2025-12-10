# AWS Deployment Guide for TokenEye

Step-by-step guide to deploy TokenEye on AWS Free Tier.

---

## Prerequisites Completed ✅

| Item                  | Status                             |
| --------------------- | ---------------------------------- |
| Dockerfile            | ✅ Working (`tokeneye_app:latest`) |
| docker-compose.yml    | ✅ Tested locally                  |
| .env.example          | ✅ Template ready                  |
| scripts/export_db.py  | ✅ Parquet export working          |
| DATABASE_URL from env | ✅ config.py updated               |

---

## AWS Free Tier Limits

| Resource        | Free Tier (12 months)       |
| --------------- | --------------------------- |
| EC2 t2.micro    | 750 hrs/month (~31 days)    |
| RDS db.t3.micro | 750 hrs/month, 20GB storage |
| S3              | 5GB storage                 |
| Data Transfer   | 100GB/month outbound        |

---

## Step 1: AWS Account Setup

### 1.1 Create AWS Account

1. Go to https://aws.amazon.com/free
2. Sign up with email and payment method (won't be charged if you stay in free tier)
3. Wait for account activation (can take a few hours)

### 1.2 Create IAM User (Recommended)

1. AWS Console → IAM → Users → Create User
2. User name: `tokeneye-admin`
3. Attach policies: `AdministratorAccess` (or more restrictive later)
4. Create access key → Download CSV with Access Key ID and Secret

### 1.3 Install AWS CLI Locally

```bash
# Install
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Configure
aws configure
# Enter: Access Key ID, Secret Access Key, Region (us-east-1), Output format (json)
```

---

## Step 2: Create S3 Bucket (For Backups)

```bash
# Create bucket (name must be globally unique)
aws s3 mb s3://tokeneye-backups-ayomide --region us-east-1

# Verify
aws s3 ls
```

---

## Step 3: Create RDS PostgreSQL Database

### Via AWS Console (Easier)

1. AWS Console → RDS → Create Database
2. Choose:
   - **Engine**: PostgreSQL
   - **Template**: Free tier
   - **DB instance identifier**: `tokeneye-db`
   - **Master username**: `postgres`
   - **Master password**: (save this!)
   - **DB instance class**: db.t3.micro
   - **Storage**: 20 GB
   - **Public access**: Yes (for initial setup, can disable later)
3. Under "Additional configuration":
   - **Initial database name**: `tokenscout`
4. Create database (takes 5-10 minutes)

### Via CLI (Alternative)

```bash
aws rds create-db-instance \
  --db-instance-identifier tokeneye-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --engine-version 15 \
  --master-username postgres \
  --master-user-password YOUR_SECURE_PASSWORD \
  --allocated-storage 20 \
  --db-name tokenscout \
  --publicly-accessible \
  --backup-retention-period 7
```

### Get RDS Endpoint

```bash
aws rds describe-db-instances --db-instance-identifier tokeneye-db \
  --query 'DBInstances[0].Endpoint.Address' --output text
```

Output will be like: `tokeneye-db.abc123xyz.us-east-1.rds.amazonaws.com`

---

## Step 4: Create EC2 Instance

### 4.1 Create Key Pair

```bash
aws ec2 create-key-pair --key-name tokeneye-key --query 'KeyMaterial' --output text > tokeneye-key.pem
chmod 400 tokeneye-key.pem
```

### 4.2 Create Security Group

```bash
# Create security group
aws ec2 create-security-group \
  --group-name tokeneye-sg \
  --description "TokenEye security group"

# Allow SSH (port 22)
aws ec2 authorize-security-group-ingress \
  --group-name tokeneye-sg \
  --protocol tcp --port 22 --cidr 0.0.0.0/0

# Allow API (port 8000)
aws ec2 authorize-security-group-ingress \
  --group-name tokeneye-sg \
  --protocol tcp --port 8000 --cidr 0.0.0.0/0
```

### 4.3 Launch EC2 Instance

```bash
# Get latest Amazon Linux 2023 AMI ID
AMI_ID=$(aws ec2 describe-images \
  --owners amazon \
  --filters "Name=name,Values=al2023-ami-*-x86_64" "Name=state,Values=available" \
  --query 'sort_by(Images, &CreationDate)[-1].ImageId' \
  --output text)

# Launch instance
aws ec2 run-instances \
  --image-id $AMI_ID \
  --instance-type t2.micro \
  --key-name tokeneye-key \
  --security-groups tokeneye-sg \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=tokeneye-server}]'
```

### 4.4 Get Public IP

```bash
aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=tokeneye-server" \
  --query 'Reservations[0].Instances[0].PublicIpAddress' --output text
```

---

## Step 5: Deploy to EC2

### 5.1 SSH into Instance

```bash
ssh -i tokeneye-key.pem ec2-user@YOUR_EC2_PUBLIC_IP
```

### 5.2 Install Docker on EC2

```bash
# Update system
sudo yum update -y

# Install Docker
sudo yum install docker -y
sudo systemctl start docker
sudo systemctl enable docker

# Add user to docker group
sudo usermod -aG docker ec2-user

# Log out and back in for group change
exit
```

### 5.3 Re-connect and Clone Project

```bash
ssh -i tokeneye-key.pem ec2-user@YOUR_EC2_PUBLIC_IP

# Install git
sudo yum install git -y

# Clone your repo (or use scp to upload)
git clone https://github.com/YOUR_USERNAME/TokenEye.git
cd TokenEye
```

### 5.4 Create .env File on EC2

```bash
cat > .env << 'EOF'
# Telegram
TELEGRAM_BOT_TOKEN=8314034578:AAGtGocDxVuBmleObMu8U-tMTGAKsuQLn6A
TELEGRAM_ALERT_CHANNEL=-1003277871734
TELEGRAM_PRO_ALERT_CHANNEL=-1003231042684

# Helius (use your actual keys)
HELIUS_API_KEY_1=69fe00b3-fabb-464c-ab0b-3a837cc69a4f
HELIUS_API_KEY_2=f47c5e9c-e802-44d2-97db-a4ef70bb3209
HELIUS_API_KEY_3=99943024-11c0-4ca5-b2f2-4db27bae9e93
HELIUS_API_KEY_4=f1c2ca31-86a8-42db-a705-31a7bf5adc6d

# Database (RDS endpoint)
DATABASE_URL=postgresql+psycopg2://postgres:YOUR_RDS_PASSWORD@tokeneye-db.abc123xyz.us-east-1.rds.amazonaws.com:5432/tokenscout
EOF
```

### 5.5 Build and Run Docker

```bash
# Build image
docker build -t tokeneye .

# Run container
docker run -d \
  --name tokeneye \
  --restart unless-stopped \
  -p 8000:8000 \
  --env-file .env \
  tokeneye

# Check logs
docker logs -f tokeneye
```

### 5.6 Verify Deployment

```bash
# From EC2
curl http://localhost:8000/

# From your local machine
curl http://YOUR_EC2_PUBLIC_IP:8000/
```

---

## Step 6: Set Up Weekly Backup Cron

SSH into EC2 and set up weekly exports:

```bash
# Install Python dependencies for export script
sudo yum install python3-pip -y
pip3 install pandas pyarrow boto3 sqlalchemy psycopg2-binary python-dotenv

# Test export
cd ~/TokenEye
python3 scripts/export_db.py --output ./exports/

# Add cron job (every Sunday at 2 AM)
crontab -e
# Add this line:
0 2 * * 0 cd /home/ec2-user/TokenEye && python3 scripts/export_db.py --upload-s3 --s3-bucket tokeneye-backups-ayomide
```

---

## Step 7: Download Backups Locally

On your local machine:

```bash
# Sync from S3
aws s3 sync s3://tokeneye-backups-ayomide/exports/ ~/tokeneye-data/

# Or use the script
./scripts/sync_from_s3.sh
```

---

## Quick Reference

| Resource     | Value                                 |
| ------------ | ------------------------------------- |
| EC2 IP       | `YOUR_EC2_PUBLIC_IP`                  |
| RDS Endpoint | `tokeneye-db.xxx.rds.amazonaws.com`   |
| S3 Bucket    | `tokeneye-backups-ayomide`            |
| API URL      | `http://YOUR_EC2_PUBLIC_IP:8000`      |
| SSH          | `ssh -i tokeneye-key.pem ec2-user@IP` |

---

## Estimated Monthly Cost

| Resource        | Free Tier | After 12 months   |
| --------------- | --------- | ----------------- |
| EC2 t2.micro    | $0        | ~$8.50/month      |
| RDS db.t3.micro | $0        | ~$15/month        |
| S3 (1GB)        | $0        | ~$0.02/month      |
| **Total**       | **$0**    | **~$23.50/month** |
