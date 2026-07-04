# دليل نشر نظام الحضور على VPS باستخدام Docker

## المتطلبات الأساسية
- VPS يعمل بنظام Linux (مثلاً Ubuntu 22.04 أو 20.04)
- Docker مثبت على الـ VPS
- Docker Compose مثبت على الـ VPS

## الخطوة 1: تثبيت Docker و Docker Compose على الـ VPS

### تثبيت Docker:
```bash
# Update packages
sudo apt update && sudo apt upgrade -y

# Install Docker dependencies
sudo apt install -y apt-transport-https ca-certificates curl software-properties-common

# Add Docker GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Add Docker repository
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
sudo apt update && sudo apt install -y docker-ce docker-ce-cli containerd.io

# Add your user to docker group (to run docker without sudo)
sudo usermod -aG docker $USER
newgrp docker
```

### تثبيت Docker Compose:
```bash
# Download Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose

# Make it executable
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker-compose --version
```

## الخطوة 2: رفع الملفات إلى الـ VPS

1. رفع جميع ملفات المشروع إلى مجلد على الـ VPS (مثلاً `/home/ubuntu/verdebeautyclinic`)
2. تأكد من أن الملفات التالية موجودة:
   - `Dockerfile`
   - `docker-compose.yml`
   - `.env` (قم بتعديله إذا أردت تغيير كلمات المرور أو الإعدادات)
   - جميع ملفات المشروع (app/, requirements.txt, إلخ)

## الخطوة 3: تشغيل النظام باستخدام Docker Compose

```bash
# اذهب إلى مجلد المشروع
cd /home/ubuntu/verdebeautyclinic

# تشغيل جميع الخدمات في الخلفية
docker-compose up -d --build

# لرؤية الحالة والـ logs
docker-compose ps
docker-compose logs -f
```

## الوصول إلى النظام بعد التثبيت:
- **النظام الرئيسي**: http://[IP_ADDRESS_OF_VPS]:8000
- **Portainer (إدارة Docker)**: https://[IP_ADDRESS_OF_VPS]:9443

## إعدادات مهمة:
- في ملف `.env` تأكد من تغيير:
  1. `SECRET_KEY` لقيمة آمنة طويلة
  2. `POSTGRES_PASSWORD` لكلمة مرور آمنة لقاعدة البيانات
  3. `ADMIN_PASSWORD` لكلمة مرور المدير في النظام

## أوامر مفيدة:
- إيقاف جميع الخدمات:
  ```bash
  docker-compose down
  ```
- تشغيل الخدمات مرة أخرى:
  ```bash
  docker-compose up -d
  ```
- رؤية logs لخدمة معينة:
  ```bash
  docker-compose logs -f app
  ```
- نسخ احتياطي لقاعدة البيانات:
  ```bash
  docker-compose exec db pg_dumpall -U postgres > backup.sql
  ```
- استعادة نسخة احتياطية لقاعدة البيانات:
  ```bash
  cat backup.sql | docker-compose exec -T db psql -U postgres -d attendance_db
  ```
