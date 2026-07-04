# حل مشكلة الحجم الكبير على GitHub

## المشكلة
السبب الرئيسي هو مجلد `venv/` و `__pycache__` هو اللي بياخد مساحة كبيرة جدًا!

## الحل - الخطوات:

### الخطوة 1: التأكد من أن Git لا يتتبع المجلدات غير المرادها
تأكد أن ملف `.gitignore` موجود و يحتوي على هذي السطور (اللي هو موجود بالفعل):
```
venv/
__pycache__/
```

### الخطوة 2: تنظيف git cache (لو كان git بيتبع venv/__pycache__ من قبل)
```bash
# اذهب إلى مجلد المشروع
cd g:\DrMohammed\AttendanceManagementSystem

# حذف venv/__pycache__ من git tracking بدون حذف الملفات من جهازك
git rm -r --cached venv
git rm -r --cached app/__pycache__
git rm -r --cached app/core/__pycache__
git rm -r --cached app/models/__pycache__
git rm -r --cached app/schemas/__pycache__
git rm -r --cached scripts/__pycache__
# إذا كان لديك مجلد backups/ أيضاً
git rm -r --cached backups/backups
```

### الخطوة 3: إعادة الـ commit جديد
```bash
# إضافة جميع التغييرات
git add .

# الـ commit
git commit -m "Remove venv and pycache from tracking"

# بعد كده الـ push هتعمل بسهولة!
git push -u origin main
```

### إذا ما زل المشكلة:
إذا الـ repo كمان مشكلة في الـ push، يمكنك الـ push أجزاء:
```bash
# زيادة الحد الأقصى لحجم الـ push
git config http.postBuffer 524288000

# ثم الـ push تاني
git push -u origin main
```
