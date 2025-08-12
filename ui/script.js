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
    actions: 'اکشن‌ها'
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
    actions: 'Actions'
  }
};

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
