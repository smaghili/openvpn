function toggleTheme() {
  document.documentElement.classList.toggle('dark');
}

const translations = {
  fa: {
    sidebar_title: 'پنل VPN',
    nav_overview: 'اوریوو',
    nav_users: 'یوزرز',
    nav_openvpn: 'تنظیمات OpenVPN',
    nav_wireguard: 'تنظیمات WireGuard',
    nav_settings: 'تنظیمات کلی',
    nav_logout: 'خروج',
    btn_theme: 'تم',
    btn_language: 'زبان',
    modal_yes: 'بله',
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
    users_header: 'Users',
    protocol: 'پروتکل',
    status: 'وضعیت',
    data: 'دیتا',
    total_users: 'کل کاربران',
    total_usage: 'حجم مصرفی کل',
    service: 'سرویس',
    log_based: 'Log-based',
    service_based: 'Service-based',
    last_event: 'آخرین رخداد',
    openvpn_title: 'تنظیمات OpenVPN',
    service_config: 'پیکربندی سرویس',
    login_config: 'پیکربندی لاگین',
    logs: 'لاگ‌ها',
    settings_title: 'تنظیمات کلی',
    admin_account: 'حساب مدیر',
    display_language: 'نمایش و زبان',
    network_ports: 'شبکه/پورت‌ها',
    agents: 'نماینده‌ها',
    save_all: 'ذخیرهٔ همه تغییرات',
    cancel: 'لغو',
    add_agent: '+ افزودن نماینده',
    wireguard_title: 'تنظیمات WireGuard',
    placeholder_msg: 'در این نسخه تنظیمات پیشرفته لازم نیست؛ فقط کنترل و لاگ.',
    status_running: 'وضعیت: ● سبز Running',
    status_stopped: 'وضعیت: ○ خاکستری Stopped',
    start: 'Start ▶',
    stop: 'Stop ■',
    restart: 'Restart ⟳',
    logs_btn: 'Logs 🗎',
    username: 'نام کاربری',
    create_user: 'ایجاد کاربر+',
    name_code: 'نام/کد',
    permissions: 'مجوزها',
    actions: 'اکشن‌ها',
    change: 'تغییر',
    change_reset: 'تغییر/ریست',
    timezone: 'منطقه زمانی',
    panel_port: 'پورت پنل/لاگین',
    apply: 'اعمال',
    apply_confirm: 'اعمال؟',
    edit: 'ویرایش',
    delete: 'حذف',
    perm_create: 'ایجاد',
    perm_edit: 'ویرایش',
    perm_delete: 'حذف',
    perm_view_log: 'مشاهده لاگ',
    reset: 'ریست',
    reset_confirm: 'ریست؟',
    applied: 'اعمال شد',
    saved: 'ذخیره شد',
    canceled: 'لغو شد',
    user_details: 'جزئیات کاربر',
    close: 'بستن',
    drawer_sections: 'پروفایل/نقش | کلیدها | سهمیه/انقضا | نشست‌های فعال | لاگ‌ها',
    disconnect: 'قطع اتصال',
    reset_password: 'بازنشانی رمز',
    regenerate_keys: 'بازسازی کلیدها',
    save_btn: 'ذخیره',
    sort: 'مرتب‌سازی',
    last_act: 'آخرین فعالیت',
    all: 'همه',
    status_active: 'فعال',
    expire_5d: 'انقضا:5روز',
    quota_exceeded: 'سهمیه تمام شد',
    dot_green: '● سبز',
    dot_gray: '● خاکستری',
    service_port: 'پورت سرویس',
    login_port: 'پورت لاگین',
    on: 'روشن',
    off: 'خاموش',
    test_port: 'تست پورت',
    open_firewall: 'باز کردن در فایروال',
    alert_sample: '⚠︎ OpenVPN: ارتباط تونل X قطع شد (5m ago)\nℹ︎ WireGuard: کلید جدید برای کاربر ali ایجاد شد',
    dark: 'دارک',
    light: 'لایت',
    lang_fa: 'فارسی',
    lang_en: 'انگلیسی',
    lang_ru: 'روسی',
    udp: 'UDP',
    tcp: 'TCP',
    tz: 'TZ'
  },
  en: {
    sidebar_title: 'VPN Panel',
    nav_overview: 'Overview',
    nav_users: 'Users',
    nav_openvpn: 'OpenVPN Settings',
    nav_wireguard: 'WireGuard Settings',
    nav_settings: 'General Settings',
    nav_logout: 'Logout',
    btn_theme: 'Theme',
    btn_language: 'Language',
    modal_yes: 'Yes',
    modal_no: 'No',
    login_title: 'Login to VPN Admin Panel',
    label_username: 'Username',
    label_password: 'Password',
    remember_me: 'Remember me',
    btn_login: 'Login',
    overview_title: 'Overview',
    last_update: 'Last Update',
    users_title: 'Users',
    search_placeholder: 'Search',
    total_label: 'Total',
    online_label: 'Online',
    active_label: 'Active',
    openvpn_label: 'OpenVPN',
    wg_label: 'WG',
    users_header: 'Users',
    protocol: 'Protocol',
    status: 'Status',
    data: 'Data',
    total_users: 'Total Users',
    total_usage: 'Total Usage',
    service: 'Service',
    log_based: 'Log-based',
    service_based: 'Service-based',
    last_event: 'Last Event',
    openvpn_title: 'OpenVPN Settings',
    service_config: 'Service Config',
    login_config: 'Login Config',
    logs: 'Logs',
    settings_title: 'General Settings',
    admin_account: 'Admin Account',
    display_language: 'Display & Language',
    network_ports: 'Network/Ports',
    agents: 'Agents',
    save_all: 'Save All Changes',
    cancel: 'Cancel',
    add_agent: '+ Add Agent',
    wireguard_title: 'WireGuard Settings',
    placeholder_msg: 'In this version only basic control and logs are needed.',
    status_running: 'Status: ● Green Running',
    status_stopped: 'Status: ○ Grey Stopped',
    start: 'Start ▶',
    stop: 'Stop ■',
    restart: 'Restart ⟳',
    logs_btn: 'Logs 🗎',
    username: 'Username',
    create_user: 'Create User +',
    name_code: 'Name/ID',
    permissions: 'Permissions',
    actions: 'Actions',
    change: 'Change',
    change_reset: 'Change/Reset',
    timezone: 'Timezone',
    panel_port: 'Panel/Login Port',
    apply: 'Apply',
    apply_confirm: 'Apply?',
    edit: 'Edit',
    delete: 'Delete',
    perm_create: 'Create',
    perm_edit: 'Edit',
    perm_delete: 'Delete',
    perm_view_log: 'View Log',
    reset: 'Reset',
    reset_confirm: 'Reset?',
    applied: 'Applied',
    saved: 'Saved',
    canceled: 'Canceled',
    user_details: 'User Details',
    close: 'Close',
    drawer_sections: 'Profile/Role | Keys | Quota/Expiry | Active Sessions | Logs',
    disconnect: 'Disconnect',
    reset_password: 'Reset Password',
    regenerate_keys: 'Regenerate Keys',
    save_btn: 'Save',
    sort: 'Sort',
    last_act: 'Last Act',
    all: 'All',
    status_active: 'Active',
    expire_5d: 'Expire:5d',
    quota_exceeded: 'Quota Exceeded',
    dot_green: '● Green',
    dot_gray: '● Gray',
    service_port: 'Service Port',
    login_port: 'Login Port',
    on: 'On',
    off: 'Off',
    test_port: 'Test Port',
    open_firewall: 'Open in Firewall',
    alert_sample: '⚠︎ OpenVPN: Tunnel X disconnected (5m ago)\nℹ︎ WireGuard: New key generated for user ali',
    dark: 'Dark',
    light: 'Light',
    lang_fa: 'FA',
    lang_en: 'EN',
    lang_ru: 'RU',
    udp: 'UDP',
    tcp: 'TCP',
    tz: 'TZ'
  }
};

// future Russian translations default to English
translations.ru = { ...translations.en };

let currentLang = localStorage.getItem('lang') || 'fa';

function setLanguage(lang) {
  if (!translations[lang]) return;
  currentLang = lang;
  localStorage.setItem('lang', lang);
  document.documentElement.dir = lang === 'fa' ? 'rtl' : 'ltr';
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.getAttribute('data-i18n');
    const txt = translations[lang][key];
    if (txt) {
      if (el.tagName === 'INPUT' && el.placeholder !== undefined) {
        el.placeholder = txt;
      } else {
        el.textContent = txt;
      }
    }
  });
  const selector = document.getElementById('langSelect');
  if (selector) selector.value = lang;
}

function toggleLanguage() {
  const langs = Object.keys(translations);
  const idx = langs.indexOf(currentLang);
  const next = langs[(idx + 1) % langs.length];
  setLanguage(next);
}

document.addEventListener('DOMContentLoaded', () => {
  setLanguage(currentLang);
});
function showToast(message, type='info') {
  const container = document.querySelector('.toast-container');
  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(()=>toast.remove(), 3000);
}
function showModal(message, onConfirm) {
  const modal = document.querySelector('.modal');
  const text = modal.querySelector('.modal-message');
  text.textContent = message;
  modal.style.display = 'flex';
  const yes = modal.querySelector('.yes');
  const no = modal.querySelector('.no');
  yes.onclick = () => { modal.style.display='none'; if(onConfirm) onConfirm(); };
  no.onclick = () => { modal.style.display='none'; };
}
function openDrawer(id) {
  const drawer = document.getElementById(id);
  drawer.classList.add('open');
}
function closeDrawer(id) {
  const drawer = document.getElementById(id);
  drawer.classList.remove('open');
}
