import React, { useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Settings,
  Palette,
  Globe,
  Shield,
  Key,
  Save,
  RefreshCw,
  Copy,
  Eye,
  EyeOff
} from 'lucide-react'
import toast from 'react-hot-toast'
import { useTheme } from '@/contexts/ThemeContext'
import { generateId } from '@/lib/utils'

export function GeneralSettingsPage() {
  const { t, i18n } = useTranslation()
  const { theme, setTheme } = useTheme()
  const [showApiKey, setShowApiKey] = useState(false)
  const [currentApiKey] = useState('openvpn_' + generateId())
  const [ipRestrictions, setIpRestrictions] = useState('')
  const [saving, setSaving] = useState(false)

  const handleLanguageChange = (newLang: string) => {
    i18n.changeLanguage(newLang)
    localStorage.setItem('openvpn_language', newLang)
    toast.success(t('settings.settings_saved'))
  }

  const handleThemeChange = (newTheme: 'light' | 'dark') => {
    setTheme(newTheme)
    toast.success(t('settings.settings_saved'))
  }

  const generateNewApiKey = () => {
    const newKey = 'openvpn_' + generateId()
    navigator.clipboard.writeText(newKey)
    toast.success('New API key generated and copied to clipboard')
  }

  const copyApiKey = () => {
    navigator.clipboard.writeText(currentApiKey)
    toast.success('API key copied to clipboard')
  }

  const handleSaveSettings = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    
    try {
      // Mock save operation
      await new Promise(resolve => setTimeout(resolve, 1000))
      toast.success(t('settings.settings_saved'))
    } catch (error) {
      toast.error('Failed to save settings')
    } finally {
      setSaving(false)
    }
  }

  const settingSections = [
    {
      id: 'appearance',
      title: t('settings.appearance'),
      icon: Palette,
      content: (
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
              Theme
            </label>
            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={() => handleThemeChange('light')}
                className={`p-4 rounded-lg border-2 transition-colors ${
                  theme === 'light'
                    ? 'border-primary-600 bg-primary-50 dark:bg-primary-900'
                    : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                }`}
              >
                <div className="text-center">
                  <div className="w-8 h-8 bg-white border border-gray-300 rounded mx-auto mb-2"></div>
                  <span className="text-sm font-medium">{t('settings.light_theme')}</span>
                </div>
              </button>
              
              <button
                onClick={() => handleThemeChange('dark')}
                className={`p-4 rounded-lg border-2 transition-colors ${
                  theme === 'dark'
                    ? 'border-primary-600 bg-primary-50 dark:bg-primary-900'
                    : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                }`}
              >
                <div className="text-center">
                  <div className="w-8 h-8 bg-gray-800 border border-gray-600 rounded mx-auto mb-2"></div>
                  <span className="text-sm font-medium">{t('settings.dark_theme')}</span>
                </div>
              </button>
            </div>
          </div>
        </div>
      )
    },
    {
      id: 'language',
      title: t('settings.language_region'),
      icon: Globe,
      content: (
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
              Language
            </label>
            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={() => handleLanguageChange('en')}
                className={`p-4 rounded-lg border-2 transition-colors text-left ${
                  i18n.language === 'en'
                    ? 'border-primary-600 bg-primary-50 dark:bg-primary-900'
                    : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                }`}
              >
                <div className="flex items-center space-x-3">
                  <div className="text-2xl">🇺🇸</div>
                  <div>
                    <div className="font-medium">{t('settings.english')}</div>
                    <div className="text-sm text-gray-500">English</div>
                  </div>
                </div>
              </button>
              
              <button
                onClick={() => handleLanguageChange('fa')}
                className={`p-4 rounded-lg border-2 transition-colors text-left ${
                  i18n.language === 'fa'
                    ? 'border-primary-600 bg-primary-50 dark:bg-primary-900'
                    : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                }`}
              >
                <div className="flex items-center space-x-3">
                  <div className="text-2xl">🇮🇷</div>
                  <div>
                    <div className="font-medium">{t('settings.persian')}</div>
                    <div className="text-sm text-gray-500">فارسی</div>
                  </div>
                </div>
              </button>
            </div>
          </div>
        </div>
      )
    },
    {
      id: 'api',
      title: t('settings.api_management'),
      icon: Key,
      content: (
        <div className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              {t('settings.current_api_key')}
            </label>
            <div className="flex items-center space-x-2">
              <div className="flex-1 relative">
                <input
                  type={showApiKey ? 'text' : 'password'}
                  value={currentApiKey}
                  readOnly
                  className="input-field pr-20"
                />
                <div className="absolute right-2 top-1/2 transform -translate-y-1/2 flex space-x-1">
                  <button
                    type="button"
                    onClick={() => setShowApiKey(!showApiKey)}
                    className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
                  >
                    {showApiKey ? (
                      <EyeOff className="w-4 h-4" />
                    ) : (
                      <Eye className="w-4 h-4" />
                    )}
                  </button>
                  <button
                    type="button"
                    onClick={copyApiKey}
                    className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
                  >
                    <Copy className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          </div>
          
          <div>
            <button
              onClick={generateNewApiKey}
              className="btn-secondary flex items-center space-x-2"
            >
              <RefreshCw className="w-4 h-4" />
              <span>{t('settings.generate_new_key')}</span>
            </button>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
              Warning: Generating a new key will invalidate the current one
            </p>
          </div>
        </div>
      )
    },
    {
      id: 'security',
      title: t('settings.security'),
      icon: Shield,
      content: (
        <form onSubmit={handleSaveSettings} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              {t('settings.ip_restrictions')}
            </label>
            <textarea
              value={ipRestrictions}
              onChange={(e) => setIpRestrictions(e.target.value)}
              placeholder="192.168.1.0/24&#10;10.0.0.0/8&#10;172.16.0.0/12"
              rows={4}
              className="input-field resize-none"
            />
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              Enter allowed IP ranges, one per line. Leave empty to allow all IPs.
            </p>
          </div>
          
          <button
            type="submit"
            disabled={saving}
            className="btn-primary flex items-center space-x-2"
          >
            {saving ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                <span>Saving...</span>
              </>
            ) : (
              <>
                <Save className="w-4 h-4" />
                <span>{t('common.save')}</span>
              </>
            )}
          </button>
        </form>
      )
    }
  ]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
          {t('settings.title')}
        </h1>
        <p className="text-gray-600 dark:text-gray-400 mt-2">
          Customize your OpenVPN Manager experience
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {settingSections.map((section) => {
          const Icon = section.icon
          return (
            <div key={section.id} className="card p-6">
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
                <Icon className="w-5 h-5 mr-2" />
                {section.title}
              </h2>
              {section.content}
            </div>
          )
        })}
      </div>

      {/* Additional System Information */}
      <div className="card p-6">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
          <Settings className="w-5 h-5 mr-2" />
          System Information
        </h2>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
            <div className="text-sm text-gray-500 dark:text-gray-400">Version</div>
            <div className="font-medium text-gray-900 dark:text-white">v1.0.0</div>
          </div>
          
          <div className="p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
            <div className="text-sm text-gray-500 dark:text-gray-400">API Status</div>
            <div className="font-medium text-green-600 dark:text-green-400">Connected</div>
          </div>
          
          <div className="p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
            <div className="text-sm text-gray-500 dark:text-gray-400">Last Updated</div>
            <div className="font-medium text-gray-900 dark:text-white">
              {new Date().toLocaleDateString()}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}