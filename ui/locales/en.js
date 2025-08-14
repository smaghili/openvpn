export default {
  sidebar_title: 'VPN Panel',
  nav_overview: 'Overview',
  nav_users: 'Users',
  nav_openvpn: 'OpenVPN Settings',
  nav_wireguard: 'WireGuard Settings',
  nav_settings: 'General Settings',
  nav_logout: 'Logout',
  modal_yes: 'Yes',
  modal_no: 'No',
  login_title: 'Login to VPN Admin Panel',
  label_username: 'Username',
  label_password: 'Password',
  remember_me: 'Remember me',
  btn_login: 'Login',
  btn_theme: 'Theme',
  btn_language: 'Language',
  lang_fa: 'FA',
  lang_en: 'EN',
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
  uptime: 'Uptime',
  resource_usage: 'Resource Usage',
  overview: {
    header: { 
      title: 'Overview',
      subtitle: 'System Overview'
    },
    stats: { 
      totalUsers: 'Total Users', 
      totalUsage: 'Total Usage',
      systemUptime: 'System Uptime',
      activeConnections: 'Active Connections'
    },
    charts: {
      cpu: 'CPU Usage',
      memory: 'Memory Usage',
      network: 'Network Traffic',
      storage: 'Storage Usage'
    }
  },
  services: {
    title: 'Service Status',
    card: { 
      status: { 
        active: 'Active', 
        inactive: 'Inactive', 
        failed: 'Failed',
        up: 'Active',
        down: 'Stopped',
        error: 'Error',
        unknown: 'Unknown'
      } 
    },
    actions: { 
      start: 'Start', 
      stop: 'Stop', 
      restart: 'Restart',
      starting: 'Starting...',
      stopping: 'Stopping...',
      restarting: 'Restarting...'
    },
    names: {
      'openvpn-server@server-cert': 'OpenVPN (Certificate)',
      'openvpn-server@server-login': 'OpenVPN (Login)',
      'wg-quick@wg0': 'WireGuard',
      'openvpn-uds-monitor': 'UDS Monitor'
    }
  },
  logs: {
    title: 'Logs',
    modal: { 
      title: 'View Log', 
      downloadTxt: 'Download TXT', 
      refresh: 'Refresh', 
      live: 'Live tail',
      close: 'Close',
      empty: 'No logs available',
      loading: 'Loading...'
    },
    services: {
      openvpn: 'OpenVPN Logs',
      wireguard: 'WireGuard Logs',
      uds: 'UDS Monitor Logs',
      system: 'System Logs'
    }
  },
  backup: {
    title: 'Backup & Restore',
    create: 'Create Backup',
    restore: 'Restore',
    createWithStored: 'Create Backup (Stored)',
    creating: 'Creating...',
    prompt: { 
      password: 'Enter backup password', 
      rememberPassword: 'Remember this password for future backups?',
      confirmPassword: 'Confirm password'
    },
    success: 'Backup file is ready to download.',
    restoring: 'Restoring...'
  },
  restore: {
    prompt: { 
      selectFile: 'Choose backup file', 
      password: 'Enter restore password'
    },
    confirm: { 
      restartSystem: 'The system will restart after restore. Continue?'
    }
  },
  messages: {
    loading: 'Loading...',
    error: 'Error',
    success: 'Success',
    warning: 'Warning',
    confirm: 'Confirm',
    cancel: 'Cancel',
    save: 'Save',
    delete: 'Delete',
    edit: 'Edit',
    close: 'Close'
  },
  errors: {
    network: 'Network connection error',
    server: 'Server error',
    auth: 'Authentication error',
    permission: 'Permission denied'
  },
  toasts: {
    systemStatsError: 'Error loading system stats',
    serviceStatusError: 'Error loading service status',
    serviceActionError: 'Service operation error',
    logDownloadSuccess: 'Log file downloaded',
    logDownloadError: 'Error downloading log file',
    backupError: 'Error creating backup',
    restoreStarted: 'Restore started. System will restart...',
    restoreError: 'Error in restore',
    loginError: 'Login error'
  },
  time: {
    days: 'days',
    hours: 'hours',
    minutes: 'minutes',
    uptimeFormat: '{days} days, {hours} hours, {minutes} minutes'
  },
  login: {
    validation: {
      required: 'Please enter username and password'
    }
  },
  brand_title: 'VPN Panel',
  logout: 'Logout',
  users_title: 'Users',
  create_user: 'Create User +',
  search_placeholder: 'Search',
  total_label: 'Total',
  online_label: 'Online',
  active_label: 'Active',
  openvpn_label: 'OpenVPN',
  wg_label: 'WG',
  protocol: 'Protocol',
  status: 'Status',
  data: 'Data',
  username: 'Username',
  all: 'All',
  sort: 'Sort',
  last_act: 'Last Act',
  set_quota: 'Set Quota',
  delete: 'Delete',
  user_details: 'User Details',
  close: 'Close',
  drawer_sections: 'Profile/Role | Keys | Quota/Expiry | Active Sessions | Logs',
  disconnect: 'Disconnect',
  reset_password: 'Reset Password',
  regenerate_keys: 'Regenerate Keys',
  save_btn: 'Save',
  wireguard_title: 'WireGuard Settings',
  status_stopped: 'Status: ○ Grey Stopped',
  start: 'Start ▶',
  stop: 'Stop ■',
  restart: 'Restart ⟳',
  logs_btn: 'Logs 🗎',
  placeholder_msg: 'In this version only basic control and logs are needed.',
  settings_title: 'General Settings',
  admin_account: 'Admin Account',
  change: 'Change',
  change_reset: 'Change/Reset',
  display_language: 'Display & Language',
  dark: 'Dark',
  light: 'Light',
  timezone: 'Timezone',
  tz: 'TZ',
  network_ports: 'Network/Ports',
  panel_port: 'Panel/Login Port',
  apply: 'Apply',
  apply_confirm: 'Apply?',
  applied: 'Applied',
  agents: 'Agents',
  add_agent: '+ Add Agent',
  name_code: 'Name/ID',
  permissions: 'Permissions',
  actions: 'Actions',
  reset_confirm: 'Reset?',
  reset: 'Reset'
};