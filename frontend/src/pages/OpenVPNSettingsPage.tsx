import React, { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Shield, AlertTriangle, Save, RefreshCw } from 'lucide-react'
import toast from 'react-hot-toast'
import { api } from '@/lib/api'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { validatePort, validateIP } from '@/lib/utils'
import { OpenVPNSettings } from '@/types'

export function OpenVPNSettingsPage() {
  const { t } = useTranslation()
  const [settings, setSettings] = useState<OpenVPNSettings | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [formData, setFormData] = useState<Partial<OpenVPNSettings>>({})
  const [hasChanges, setHasChanges] = useState(false)

  useEffect(() => {
    loadSettings()
  }, [])

  const loadSettings = async () => {
    try {
      const systemStatus = await api.getSystemStatus()
      if (systemStatus.settings) {
        setSettings(systemStatus.settings)
        setFormData(systemStatus.settings)
      }
    } catch (error: any) {
      toast.error('Failed to load OpenVPN settings')
      console.error('Error loading settings:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleInputChange = (field: keyof OpenVPNSettings, value: string | number) => {
    const newFormData = { ...formData, [field]: value }
    setFormData(newFormData)
    setHasChanges(JSON.stringify(newFormData) !== JSON.stringify(settings))
  }

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    
    // Validation
    if (formData.cert_port && !validatePort(formData.cert_port)) {
      toast.error('Certificate port must be between 1024 and 65535')
      return
    }
    
    if (formData.login_port && !validatePort(formData.login_port)) {
      toast.error('Login port must be between 1024 and 65535')
      return
    }
    
    if (formData.public_ip && !validateIP(formData.public_ip)) {
      toast.error('Invalid IP address format')
      return
    }

    if (formData.cert_port === formData.login_port) {
      toast.error('Certificate and login ports must be different')
      return
    }

    setSaving(true)
    try {
      await api.updateOpenVPNSettings(formData)
      toast.success(t('openvpn.settings_saved'))
      setSettings({ ...settings, ...formData } as OpenVPNSettings)
      setHasChanges(false)
    } catch (error: any) {
      toast.error('Failed to save settings')
    } finally {
      setSaving(false)
    }
  }

  const handleReset = () => {
    if (settings) {
      setFormData(settings)
      setHasChanges(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  if (!settings) {
    return (
      <div className="text-center py-12">
        <Shield className="w-12 h-12 text-gray-400 mx-auto mb-4" />
        <p className="text-gray-500 dark:text-gray-400">
          OpenVPN is not installed or configured
        </p>
      </div>
    )
  }

  const dnsOptions = [
    { value: '1', label: t('openvpn.dns_options.1') },
    { value: '2', label: t('openvpn.dns_options.2') },
    { value: '3', label: t('openvpn.dns_options.3') },
    { value: '4', label: t('openvpn.dns_options.4') },
    { value: '5', label: t('openvpn.dns_options.5') }
  ]

  const protocolOptions = [
    { value: 'udp', label: 'UDP' },
    { value: 'tcp', label: 'TCP' }
  ]

  const cipherOptions = [
    { value: 'AES-256-GCM', label: 'AES-256-GCM (Recommended)' },
    { value: 'AES-128-GCM', label: 'AES-128-GCM' },
    { value: 'AES-256-CBC', label: 'AES-256-CBC' },
    { value: 'AES-128-CBC', label: 'AES-128-CBC' }
  ]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
          {t('openvpn.title')}
        </h1>
        <p className="text-gray-600 dark:text-gray-400 mt-2">
          Configure OpenVPN server settings and network parameters
        </p>
      </div>

      {hasChanges && (
        <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
          <div className="flex items-center">
            <AlertTriangle className="w-5 h-5 text-yellow-600 dark:text-yellow-400 mr-2" />
            <p className="text-yellow-800 dark:text-yellow-200">
              {t('openvpn.restart_required')}
            </p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Current Settings Display */}
        <div className="card p-6">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
            <Shield className="w-5 h-5 mr-2" />
            {t('openvpn.current_settings')}
          </h2>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                {t('openvpn.public_ip')}
              </label>
              <p className="text-gray-900 dark:text-white font-mono">
                {settings.public_ip}
              </p>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  {t('openvpn.cert_port')}
                </label>
                <p className="text-gray-900 dark:text-white font-mono">
                  {settings.cert_port} ({settings.cert_proto.toUpperCase()})
                </p>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  {t('openvpn.login_port')}
                </label>
                <p className="text-gray-900 dark:text-white font-mono">
                  {settings.login_port} ({settings.login_proto.toUpperCase()})
                </p>
              </div>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                {t('openvpn.dns_settings')}
              </label>
              <p className="text-gray-900 dark:text-white">
                {dnsOptions.find(opt => opt.value === settings.dns)?.label || settings.dns}
              </p>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                {t('openvpn.cipher')}
              </label>
              <p className="text-gray-900 dark:text-white font-mono">
                {settings.cipher}
              </p>
            </div>
          </div>
        </div>

        {/* Settings Form */}
        <div className="card p-6">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
            Update Settings
          </h2>
          
          <form onSubmit={handleSave} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                {t('openvpn.public_ip')}
              </label>
              <input
                type="text"
                value={formData.public_ip || ''}
                onChange={(e) => handleInputChange('public_ip', e.target.value)}
                className="input-field"
                placeholder="192.168.1.100"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  {t('openvpn.cert_port')}
                </label>
                <input
                  type="number"
                  min="1024"
                  max="65535"
                  value={formData.cert_port || ''}
                  onChange={(e) => handleInputChange('cert_port', parseInt(e.target.value))}
                  className="input-field"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Certificate Protocol
                </label>
                <select
                  value={formData.cert_proto || ''}
                  onChange={(e) => handleInputChange('cert_proto', e.target.value)}
                  className="input-field"
                >
                  {protocolOptions.map(option => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  {t('openvpn.login_port')}
                </label>
                <input
                  type="number"
                  min="1024"
                  max="65535"
                  value={formData.login_port || ''}
                  onChange={(e) => handleInputChange('login_port', parseInt(e.target.value))}
                  className="input-field"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Login Protocol
                </label>
                <select
                  value={formData.login_proto || ''}
                  onChange={(e) => handleInputChange('login_proto', e.target.value)}
                  className="input-field"
                >
                  {protocolOptions.map(option => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                {t('openvpn.dns_settings')}
              </label>
              <select
                value={formData.dns || ''}
                onChange={(e) => handleInputChange('dns', e.target.value)}
                className="input-field"
              >
                {dnsOptions.map(option => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                {t('openvpn.cipher')}
              </label>
              <select
                value={formData.cipher || ''}
                onChange={(e) => handleInputChange('cipher', e.target.value)}
                className="input-field"
              >
                {cipherOptions.map(option => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex justify-end space-x-3">
              <button
                type="button"
                onClick={handleReset}
                disabled={!hasChanges}
                className="btn-secondary disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
              >
                <RefreshCw className="w-4 h-4" />
                <span>Reset</span>
              </button>
              
              <button
                type="submit"
                disabled={!hasChanges || saving}
                className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
              >
                {saving ? (
                  <>
                    <LoadingSpinner size="sm" />
                    <span>Saving...</span>
                  </>
                ) : (
                  <>
                    <Save className="w-4 h-4" />
                    <span>{t('common.save')}</span>
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}