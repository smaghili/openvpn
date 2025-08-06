import React from 'react'
import { NavLink } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
  LayoutDashboard,
  Users,
  Settings,
  BarChart3,
  Cog,
  Globe,
  Sun,
  Moon,
  LogOut,
  Shield
} from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { useTheme } from '@/contexts/ThemeContext'
import { cn } from '@/lib/utils'

const navigationItems = [
  {
    key: 'overview',
    icon: LayoutDashboard,
    path: '/overview'
  },
  {
    key: 'users',
    icon: Users,
    path: '/users'
  },
  {
    key: 'openvpn_settings',
    icon: Shield,
    path: '/openvpn-settings'
  },
  {
    key: 'charts_usage',
    icon: BarChart3,
    path: '/charts'
  },
  {
    key: 'general_settings',
    icon: Cog,
    path: '/settings'
  }
]

export function Sidebar() {
  const { t, i18n } = useTranslation()
  const { logout } = useAuth()
  const { theme, toggleTheme } = useTheme()

  const toggleLanguage = () => {
    const newLang = i18n.language === 'en' ? 'fa' : 'en'
    i18n.changeLanguage(newLang)
    localStorage.setItem('openvpn_language', newLang)
  }

  return (
    <div className="w-64 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 flex flex-col">
      {/* Logo */}
      <div className="p-6 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 bg-primary-600 rounded-lg flex items-center justify-center">
            <Shield className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900 dark:text-white">
              OpenVPN
            </h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Manager
            </p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-2">
        {navigationItems.map((item) => {
          const Icon = item.icon
          return (
            <NavLink
              key={item.key}
              to={item.path}
              className={({ isActive }) =>
                cn(
                  'sidebar-item',
                  isActive && 'active'
                )
              }
            >
              <Icon className="w-5 h-5 mr-3" />
              <span className="font-medium">
                {t(`nav.${item.key}`)}
              </span>
            </NavLink>
          )
        })}
      </nav>

      {/* Bottom Actions */}
      <div className="p-4 border-t border-gray-200 dark:border-gray-700 space-y-2">
        {/* Language Toggle */}
        <button
          onClick={toggleLanguage}
          className="sidebar-item w-full"
          title={t('nav.language')}
        >
          <Globe className="w-5 h-5 mr-3" />
          <span className="font-medium">
            {i18n.language === 'en' ? 'فارسی' : 'English'}
          </span>
        </button>

        {/* Theme Toggle */}
        <button
          onClick={toggleTheme}
          className="sidebar-item w-full"
          title={t('nav.theme')}
        >
          {theme === 'light' ? (
            <>
              <Moon className="w-5 h-5 mr-3" />
              <span className="font-medium">{t('settings.dark_theme')}</span>
            </>
          ) : (
            <>
              <Sun className="w-5 h-5 mr-3" />
              <span className="font-medium">{t('settings.light_theme')}</span>
            </>
          )}
        </button>

        {/* Logout */}
        <button
          onClick={logout}
          className="sidebar-item w-full text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20"
        >
          <LogOut className="w-5 h-5 mr-3" />
          <span className="font-medium">{t('nav.logout')}</span>
        </button>
      </div>
    </div>
  )
}