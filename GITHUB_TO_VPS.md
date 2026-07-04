# الخطوات من GitHub إلى VPS - دليل مفصل

## الجزء 1: رفع المشروع على GitHub (من جهازك)

### الخطوة 1: إنشاء repository على GitHub
1. اذهب إلى GitHub: https://github.com
2. سجل الدخول بحسابك
3. اضغط على زر **New repository** أو **+** ثم **New repository**
4. اسمي Repository مثلاً: `verdebeautyclinic-attendance`
5. اختر **Private** أو **Public** (أفضل Private لحماية البيانات)
6. **لا** تقم باختيار "Initialize this repository with a README" (لأننا سنقوم برفع الملفات من جهازك)
7. اضغط على **Create repository**

### الخطوة 2: تهيئة Git على جهازك (إذا لم تكن مهيأة)
```bash
# افتح terminal/CMD على جهازك
# (إذا كنت على ويندوز، استخدم Git Bash أو PowerShell)

# اذهب إلى مجلد المشروع
cd g:\DrMohammed\AttendanceManagementSystem

# تهيئة Git (إذا لم تقم بذلك من قبل)
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

### الخطوة 3: رفع المشروع على GitHub
```bash
# Initialize Git repository (إذا لم يكن initialized)
git init

# Add all files (ماعداً الملفات في .gitignore)
git add .

# Commit changes
git commit -m "Initial commit for verdebeautyclinic attendance system"

# ربط repository الخاص بك
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
# مثال: git remote add origin https://github.com/ahmedmousa/verdebeautyclinic-attendance.git

# Push to GitHub
git branch -M main
git push -u origin main
```

## الجزء 2: إعداد VPS وتثبيت Docker

### الخطوة 4: الاتصال بالـ VPS
1. استخدم SSH لاتصال بـ VPS:
   ```bash
   ssh root@YOUR_VPS_IP
   # أو إذا كان لديك مستخدم آخر
   ssh your_user@YOUR_VPS_IP
   ```

### الخطوة 5: تثبيت Docker و Docker Compose على VPS
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker dependencies
sudo apt install -y apt-transport-https ca-certificates curl software-properties-common

# Add Docker GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Add Docker repository
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
sudo apt update && sudo apt install -y docker-ce docker-ce-cli containerd.io

# Add your user to docker group
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker --version
docker-compose --version
```

**تسجيل الخروج وإعادة الاتصال بالـ VPS** بعد تثبيت Docker لتحديث المجموعة.

## الجزء 3: تحميل المشروع من GitHub إلى VPS وتشغيله

### الخطوة 6: تحميل المشروع من GitHub إلى VPS
```bash
# اذهب إلى مجلدك (مثلاً /home/ubuntu)
cd /home/ubuntu

# Clone repository من GitHub
git clone https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
# مثال: git clone https://github.com/ahmedmousa/verdebeautyclinic-attendance.git

# اذهب إلى مجلد المشروع
cd YOUR_REPO_NAME
# مثال: cd verdebeautyclinic-attendance
```

### الخطوة 7: إنشاء ملف .env على VPS
ملف .env لم يتم رفعه على GitHub لأسباب أمنية، لذلك سنقوم بإنشائه على VPS مباشرة.
```bash
# أنشئ ملف .env على VPS
nano .env
```

**نسخ والصق هذا النص في الملف (قم بتعديل القيم):**
```env
# Application Settings
APP_NAME=Employee Attendance Management System
APP_ENV=production
SECRET_KEY=change-me-to-a-long-random-secret-key-123456789
ACCESS_TOKEN_EXPIRE_MINUTES=480

# Admin User
ADMIN_USERNAME=admin
ADMIN_PASSWORD=Admin@123

# Company/Clinic Name
COMPANY_NAME=verdebeautyclinic

# PostgreSQL Database
POSTGRES_USER=postgres
POSTGRES_PASSWORD=secure_postgres_password_here!
POSTGRES_DB=attendance_db
DATABASE_URL=postgresql+psycopg2://postgres:secure_postgres_password_here!@db:5432/attendance_db
```

**بعد الانتهاء:**
- اضغط `Ctrl + O` لحفظ
- اضغط `Enter` للتأكيد
- اضغط `Ctrl + X` للخروج من nano

### الخطوة 8: تشغيل النظام باستخدام Docker Compose
```bash
# Build and run all services in background
docker-compose up -d --build

# Check that all containers are running
docker-compose ps

# View logs (to make sure everything works correctly)
docker-compose logs -f
```

## الجزء 4: الوصول إلى النظام

### الروابط المتاحة:
1. **النظام الرئيسي (الحضور والانصراف):**
   ```
   http://YOUR_VPS_IP:8000
   ```

2. **Portainer (إدارة Docker):**
   ```
   https://YOUR_VPS_IP:9443
   ```
   - لأول مرة، ستحتاج إلى إنشاء مستخدم admin على Portainer

## أوامر مفيدة على VPS:
```bash
# إيقاف جميع الخدمات
docker-compose down

# تشغيل الخدمات مرة أخرى
docker-compose up -d

# رؤية logs لخدمة معينة
docker-compose logs -f app

# تحديث المشروع من GitHub (بعد أن تقوم برفع تحديثات على GitHub)
git pull origin main
# ثم قم بإعادة بناء وبدء الخدمات
docker-compose up -d --build

# نسخ احتياطي لقاعدة البيانات
docker-compose exec db pg_dumpall -U postgres > backup_$(date +%Y%m%d).sql
```

## النصائح الأمنية:
1. استخدم Private repository على GitHub
2. لا تقم برفع ملف .env على GitHub
3. استخدم كلمات مرور قوية في ملف .env على VPS
4. إذا كان لديك نطاق، استخدم Nginx أو Traefik ل SSL (HTTPS)
