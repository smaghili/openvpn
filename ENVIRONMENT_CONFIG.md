# Environment Configuration Guide

## فایل تنظیمات محیطی (environment.env)

این فایل برای مدیریت راحت تنظیمات سیستم مانیتورینگ ترافیک OpenVPN استفاده می‌شود.

### 📁 مکان فایل
```
/path/to/your/openvpn/project/environment.env
```

### ⚙️ تنظیمات موجود

#### 🌐 Management Interface
- `OPENVPN_MANAGEMENT_HOST`: آدرس IP برای اتصال به management interface (پیش‌فرض: 127.0.0.1)
- `OPENVPN_MANAGEMENT_PORT`: پورت management interface (پیش‌فرض: 7505)

#### ⏱️ تنظیمات مانیتورینگ
- `MONITOR_INTERVAL`: فاصله زمانی چک کردن ترافیک بر حسب ثانیه (30-60) (پیش‌فرض: 45)
- `MAX_LOG_SIZE`: حداکثر سایز فایل لاگ بر حسب بایت (پیش‌فرض: 10485760 = 10MB)

#### 📄 مسیرهای فایل
- `OPENVPN_LOG_FILE`: مسیر فایل لاگ (پیش‌فرض: /var/log/openvpn/traffic_monitor.log)
- `PROJECT_ROOT`: مسیر اصلی پروژه (خودکار تشخیص داده می‌شود)

### 🔧 نحوه استفاده

1. **ویرایش تنظیمات:**
   ```bash
   nano environment.env
   ```

2. **اعمال تغییرات:**
   ```bash
   sudo systemctl restart openvpn-uds-monitor
   ```

3. **بررسی وضعیت:**
   ```bash
   sudo systemctl status openvpn-uds-monitor
   ```

### 📝 مثال تغییر تنظیمات

برای تغییر فاصله زمانی چک کردن به 30 ثانیه:
```bash
# در فایل environment.env
MONITOR_INTERVAL=30
```

سپس:
```bash
sudo systemctl restart openvpn-uds-monitor
```

### ⚠️ نکات مهم

- مقادیر `MONITOR_INTERVAL` باید بین 30 تا 60 ثانیه باشد
- پس از تغییر هر تنظیم، حتماً سرویس را restart کنید
- فایل به صورت خودکار هنگام راه‌اندازی خوانده می‌شود
- اگر فایل وجود نداشته باشد، از مقادیر پیش‌فرض استفاده می‌شود

### 🔍 عیب‌یابی

برای مشاهده لاگ‌های سرویس:
```bash
sudo journalctl -u openvpn-uds-monitor -f
```

برای مشاهده لاگ‌های مانیتورینگ:
```bash
sudo tail -f /var/log/openvpn/traffic_monitor.log
```