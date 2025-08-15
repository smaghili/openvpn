export default {
  sidebar_title: 'پنل VPN',
  nav_overview: 'اوریوو',
  nav_users: 'یوزرز',
  nav_openvpn: 'تنظیمات OpenVPN',
  nav_wireguard: 'تنظیمات WireGuard',
  nav_settings: 'تنظیمات کلی',
  nav_logout: 'خروج',
  modal_yes: 'بله',
  modal_no: 'خیر',
  login_title: 'ورود به پنل مدیریت VPN',
  label_username: 'نام کاربری',
  label_password: 'رمز عبور',
  remember_me: 'مرا به خاطر بسپار',
  btn_login: 'ورود',
  btn_theme: 'تم',
  btn_language: 'زبان',
  lang_fa: 'FA',
  lang_en: 'EN',
  modal_no: 'خیر',
  login_title: 'ورود به پنل مدیریت VPN',
  label_username: 'نام کاربری',
  label_password: 'رمز عبور',
  remember_me: 'مرا به خاطر بسپار',
  btn_login: 'ورود',
  overview_title: 'اوریوو',
  last_update: 'زمان آخرین بروزرسانی',
  users_title: 'یوزرز',
  search_placeholder: 'جستجو',
  total_label: 'کل',
  online_label: 'آنلاین',
  active_label: 'فعال',
  openvpn_label: 'OpenVPN',
  wg_label: 'WG',
  users_header: 'کاربران',
  protocol: 'پروتکل',
  status: 'وضعیت',
  data: 'دیتا',
  total_users: 'کل کاربران',
  total_usage: 'حجم مصرفی کل',
  service: 'سرویس',
  uptime: 'زمان کارکرد',
  resource_usage: 'مصرف منابع',
  overview: {
    header: { 
      title: 'اوریوو',
      subtitle: 'نمای کلی سیستم'
    },
    stats: { 
      totalUsers: 'کاربران کل', 
      totalUsage: 'مصرف کل',
      systemUptime: 'زمان کارکرد سیستم',
      activeConnections: 'اتصالات فعال'
    },
    charts: {
      cpu: 'مصرف CPU',
      memory: 'مصرف حافظه',
      network: 'ترافیک شبکه',
      storage: 'فضای ذخیره‌سازی'
    }
  },
  services: {
    title: 'وضعیت سرویس‌ها',
    card: { 
      status: { 
        active: 'فعال', 
        inactive: 'غیرفعال', 
        failed: 'خطا',
        up: 'فعال',
        down: 'متوقف',
        error: 'خطا',
        unknown: 'نامشخص',
        loading: 'در حال بارگذاری...'
      } 
    },
    actions: { 
      start: 'شروع', 
      stop: 'توقف', 
      restart: 'راه‌اندازی مجدد',
      starting: 'در حال شروع...',
      stopping: 'در حال توقف...',
      restarting: 'در حال راه‌اندازی مجدد...'
    },
    names: {
              'openvpn@server-cert': 'OpenVPN (گواهی)',
        'openvpn@server-login': 'OpenVPN (نام کاربری و رمز عبور)',
      'wireguard': 'وایرگارد',
      'openvpn-uds-monitor': 'پایش ترافیک'
    }
  },
  logs: {
    title: 'لاگ‌ها',
    modal: { 
      title: 'نمایش لاگ', 
      downloadTxt: 'دانلود TXT', 
      refresh: 'تازه‌سازی', 
      live: 'نمایش زنده',
      close: 'بستن',
      empty: 'لاگی موجود نیست',
      loading: 'در حال بارگذاری...'
    },
    services: {
      openvpn: 'لاگ OpenVPN',
      wireguard: 'لاگ WireGuard',
      uds: 'لاگ UDS Monitor',
      system: 'لاگ سیستم'
    }
  },
  backup: {
    title: 'بکاپ و ریستور',
    create: 'ایجاد بکاپ',
    restore: 'ریستور',
    createWithStored: 'ایجاد بکاپ (ذخیره‌شده)',
    creating: 'در حال ایجاد...',
    prompt: { 
      password: 'رمز عبور بکاپ را وارد کنید', 
      rememberPassword: 'این رمز برای دفعات بعد ذخیره شود؟',
      confirmPassword: 'تأیید رمز عبور'
    },
    success: 'فایل بکاپ آماده دانلود است.',
    restoring: 'در حال ریستور...'
  },
  restore: {
    prompt: { 
      selectFile: 'انتخاب فایل بکاپ', 
      password: 'رمز عبور ریستور را وارد کنید'
    },
    confirm: { 
      restartSystem: 'پس از ریستور، سیستم ری‌استارت می‌شود. ادامه می‌دهید؟'
    }
  },
  messages: {
    loading: 'در حال بارگذاری...',
    error: 'خطا',
    success: 'موفق',
    warning: 'هشدار',
    confirm: 'تأیید',
    cancel: 'انصراف',
    save: 'ذخیره',
    delete: 'حذف',
    edit: 'ویرایش',
    close: 'بستن'
  },
  errors: {
    network: 'خطا در اتصال به شبکه',
    server: 'خطا در سرور',
    auth: 'خطا در احراز هویت',
    permission: 'عدم دسترسی'
  },
  toasts: {
    systemStatsError: 'خطا در بارگذاری آمار سیستم',
    serviceStatusError: 'خطا در بارگذاری وضعیت سرویس‌ها',
    serviceActionError: 'خطا در عملیات سرویس',
    logDownloadSuccess: 'فایل لاگ دانلود شد',
    logDownloadError: 'خطا در دانلود فایل لاگ',
    backupError: 'خطا در ایجاد بکاپ',
    restoreStarted: 'ریستور شروع شد. سیستم ری‌استارت می‌شود...',
    restoreError: 'خطا در ریستور',
    loginError: 'خطا در ورود به سیستم'
  },
    time: {
    days: 'روز',
    hours: 'ساعت',
    minutes: 'دقیقه',
    uptimeFormat: '{days} روز، {hours} ساعت، {minutes} دقیقه'
  },
  login: {
    validation: {
      required: 'لطفاً نام کاربری و رمز عبور را وارد کنید'
    }
  },
  brand_title: 'پنل VPN',
  logout: 'خروج',
  users_title: 'یوزرز',
  create_user: 'ایجاد کاربر+',
  search_placeholder: 'جستجو',
  total_label: 'کل',
  online_label: 'آنلاین',
  active_label: 'فعال',
  openvpn_label: 'OpenVPN',
  wg_label: 'WG',
  protocol: 'پروتکل',
  status: 'وضعیت',
  data: 'دیتا',
  username: 'نام کاربری',
  all: 'همه',
  sort: 'مرتب‌سازی',
  last_act: 'آخرین فعالیت',
  set_quota: 'تعیین سهمیه',
  delete: 'حذف',
  user_details: 'جزئیات کاربر',
  close: 'بستن',
  drawer_sections: 'پروفایل/نقش | کلیدها | سهمیه/انقضا | نشست‌های فعال | لاگ‌ها',
  disconnect: 'قطع اتصال',
  reset_password: 'بازنشانی رمز',
  regenerate_keys: 'بازسازی کلیدها',
  save_btn: 'ذخیره',
  wireguard_title: 'تنظیمات WireGuard',
  status_stopped: 'وضعیت: ○ خاکستری Stopped',
  start: 'Start ▶',
  stop: 'Stop ■',
  restart: 'Restart ⟳',
  logs_btn: 'Logs 🗎',
  placeholder_msg: 'در این نسخه تنظیمات پیشرفته لازم نیست؛ فقط کنترل و لاگ.',
  settings_title: 'تنظیمات کلی',
  admin_account: 'حساب مدیر',
  change: 'تغییر',
  change_reset: 'تغییر/ریست',
  display_language: 'نمایش و زبان',
  dark: 'دارک',
  light: 'لایت',
  timezone: 'منطقه زمانی',
  tz: 'TZ',
  network_ports: 'شبکه/پورت‌ها',
  panel_port: 'پورت پنل/لاگین',
  apply: 'اعمال',
  apply_confirm: 'اعمال؟',
  applied: 'اعمال شد',
  agents: 'نماینده‌ها',
  add_agent: '+ افزودن نماینده',
  name_code: 'نام/کد',
  permissions: 'مجوزها',
  actions: 'اکشن‌ها',
  reset_confirm: 'ریست؟',
  reset: 'ریست'
};