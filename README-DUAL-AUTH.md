# 🚀 Enhanced OpenVPN with Dual Authentication (Ubuntu Only)

این نسخه بهبود یافته از اسکریپت angristan/openvpn-install پشتیبانی همزمان از دو روش authentication ارائه می‌دهد.



## 🔐 انواع احراز هویت

### 1. Certificate-based (حرفه‌ای)
- **مناسب برای:** کاربران حرفه‌ای، VPN های شرکتی
- **امنیت:** بسیار بالا (PKI + TLS)
- **راه‌اندازی:** پیچیده‌تر، هر کاربر certificate مخصوص
- **فایل config:** `user.ovpn` (مخصوص هر نفر)
- **پورت پیش‌فرض:** 1194/UDP

### 2. Username/Password (ساده)
- **مناسب برای:** کاربران عادی، خانوادگی
- **امنیت:** خوب (PAM + TLS)
- **راه‌اندازی:** آسان، فقط یوزر/پس تعریف
- **فایل config:** `shared-login.ovpn` (مشترک برای همه)
- **پورت پیش‌فرض:** 1195/UDP

## 📋 منوی جدید

```bash
./install.sh
```

```
1) Add a new cert-based client     # ایجاد کلاینت certificate-based
2) Add a new login-based user      # ایجاد کاربر username/password  
3) Revoke existing client          # حذف کلاینت/کاربر
4) List all clients                # لیست همه کلاینت‌ها
5) Remove OpenVPN                  # حذف کامل OpenVPN
6) Exit                           # خروج
```

## 🛠 راه‌اندازی اولیه

### گام 1: نصب اولیه OpenVPN
```bash
sudo ./install.sh
```

### گام 2: نتیجه نصب
پس از نصب، هر دو روش authentication به طور خودکار راه‌اندازی می‌شوند:
   - **Certificate-based:** 1194/UDP (حرفه‌ای)
   - **Username/Password:** 1195/UDP (ساده)
   - **Shared config:** `/root/shared-login.ovpn` تولید می‌شود

### گام 3: اضافه کردن کاربران
برای اضافه کردن کاربران، مجدداً اسکریپت را اجرا کنید:
```bash
sudo ./install.sh
```

## 👥 مدیریت کاربران

### ایجاد کاربر Certificate-based
```bash
# گزینه 1 از منو
1) Add a new cert-based client
```
- نام کلاینت وارد کنید
- انتخاب password protection
- فایل `.ovpn` در `/root/` ایجاد می‌شود

### ایجاد کاربر Login-based
```bash
# گزینه 2 از منو  
2) Add a new login-based user
```
- نام کاربری وارد کنید
- رمز عبور تنظیم کنید
- فایل مشترک `shared-login.ovpn` به‌روزرسانی می‌شود
- همه کاربران login از همین فایل استفاده می‌کنند

## 🔧 تنظیمات شبکه

### Certificate-based Server
- **Interface:** tun0
- **Subnet:** 10.8.0.0/24
- **Config:** `/etc/openvpn/server-cert.conf`
- **Service:** `openvpn@server-cert`

### Login-based Server  
- **Interface:** tun1
- **Subnet:** 10.9.0.0/24
- **Config:** `/etc/openvpn/server-login.conf`
- **Service:** `openvpn@server-login`

## 📊 مانیتورینگ

### بررسی وضعیت سرویس‌ها
```bash
systemctl status openvpn@server-cert
systemctl status openvpn@server-login
```

### مشاهده لاگ‌ها
```bash
tail -f /var/log/openvpn/status-cert.log
tail -f /var/log/openvpn/status-login.log
```

### بررسی کانکشن‌های فعال
```bash
cat /var/log/openvpn/status-cert.log | grep "CLIENT_LIST"
cat /var/log/openvpn/status-login.log | grep "CLIENT_LIST"
```

## 🛡 امنیت

### Firewall Rules
اسکریپت به طور خودکار قوانین iptables را اضافه می‌کند:
- Certificate-based: پورت انتخابی شما
- Login-based: پورت انتخابی شما

### Authentication Methods
- **Certificate:** ECDSA/RSA + TLS 1.2+
- **Login:** PAM + TLS 1.2+ + Certificate validation

## 🚨 عیب‌یابی

### PAM Plugin نصب نشده
```bash
# Ubuntu/Debian
apt-get install openvpn-auth-pam

# CentOS/RHEL
yum install openvpn-auth-pam

# Fedora
dnf install openvpn-auth-pam
```

### سرویس راه‌اندازی نمی‌شود
```bash
# بررسی syntax کانفیگ
openvpn --config /etc/openvpn/server-cert.conf --test-crypto
openvpn --config /etc/openvpn/server-login.conf --test-crypto

# بررسی journalctl
journalctl -u openvpn@server-cert -f
journalctl -u openvpn@server-login -f
```

### کلاینت متصل نمی‌شود
1. بررسی firewall سرور
2. چک کردن پورت‌ها با `netstat -tulpn`
3. تست اتصال با `telnet SERVER_IP PORT`

## 📱 کلاینت‌ها

### Certificate-based
- **Windows:** OpenVPN GUI
- **macOS:** Tunnelblick
- **iOS:** OpenVPN Connect
- **Android:** OpenVPN for Android
- **Linux:** openvpn package

### Login-based
همان کلاینت‌های بالا، ولی:
- فایل config مشترک
- گزینه "Enter username/password" فعال
- بدون نیاز به certificate import

## 🔄 Migration

### از Single به Dual
اگر قبلاً OpenVPN نصب کرده‌اید:
1. گزینه `5` (Setup dual authentication)
2. Certificate server موجود حفظ می‌شود
3. Login server جدید اضافه می‌شود

### Backup
```bash
# Backup certificates
tar -czf openvpn-backup.tar.gz /etc/openvpn/easy-rsa/

# Backup configs  
cp /etc/openvpn/*.conf /backup/
```

## 🎯 Use Cases

### شرکتی
- **Admin/IT:** Certificate-based (امنیت بالا)
- **کارمندان:** Login-based (راحتی استفاده)

### خانوادگی
- **والدین:** Certificate-based (کنترل کامل)
- **بچه‌ها:** Login-based (محدودیت آسان)

### سازمانی
- **سرویس‌ها:** Certificate-based (automated)
- **کاربران:** Login-based (self-service)

---

## 📞 پشتیبانی

در صورت مشکل:
1. ابتدا بخش عیب‌یابی را مطالعه کنید
2. لاگ‌ها را بررسی کنید
3. از `./install.sh` گزینه 4 (List clients) استفاده کنید

**نسخه:** Enhanced v1.0 (بر اساس angristan/openvpn-install)