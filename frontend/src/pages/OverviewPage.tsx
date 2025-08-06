import React, { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Cpu,
  HardDrive,
  MemoryStick,
  Users,
  UserCheck,
  UserPlus,
  AlertTriangle,
  Download,
  RotateCcw,
  Activity
} from 'lucide-react'
import toast from 'react-hot-toast'
import { api } from '@/lib/api'
import { StatCard } from '@/components/ui/StatCard'
import { ServiceStatusCard } from '@/components/ui/ServiceStatusCard'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { formatPercentage } from '@/lib/utils'
import { SystemStats, ServiceStatus, Alert } from '@/types'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

export function OverviewPage() {
  const { t } = useTranslation()
  const [stats, setStats] = useState<SystemStats | null>(null)
  const [services, setServices] = useState<ServiceStatus[]>([])
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [trafficData, setTrafficData] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [restartingService, setRestartingService] = useState<string | null>(null)

  useEffect(() => {
    loadData()
    const interval = setInterval(loadData, 30000) // Refresh every 30 seconds
    return () => clearInterval(interval)
  }, [])

  const loadData = async () => {
    try {
      const [statsData, servicesData, trafficDataRes] = await Promise.all([
        api.getSystemStats(),
        api.getServiceStatus(),
        api.getTrafficData('daily')
      ])

      setStats(statsData)
      setServices(servicesData)
      setTrafficData(trafficDataRes.slice(-24)) // Last 24 hours

      // Mock alerts - would come from backend
      setAlerts([
        {
          id: '1',
          type: 'warning',
          title: 'High CPU Usage',
          message: 'CPU usage is above 80%',
          timestamp: new Date()
        },
        {
          id: '2',
          type: 'info',
          title: 'Backup Completed',
          message: 'System backup completed successfully',
          timestamp: new Date(Date.now() - 3600000)
        }
      ])
    } catch (error: any) {
      toast.error('Failed to load system data')
      console.error('Error loading overview data:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleServiceRestart = async (serviceName: string) => {
    setRestartingService(serviceName)
    try {
      await api.restartService(serviceName)
      toast.success(`${serviceName} restarted successfully`)
      await loadData() // Refresh data
    } catch (error: any) {
      toast.error(`Failed to restart ${serviceName}`)
    } finally {
      setRestartingService(null)
    }
  }

  const handleBackup = async () => {
    try {
      const password = prompt('Enter backup password:')
      if (!password) return

      toast.loading('Creating backup...', { id: 'backup' })
      const backupFile = await api.createBackup(password)
      toast.success(`Backup created: ${backupFile}`, { id: 'backup' })
    } catch (error: any) {
      toast.error('Backup failed', { id: 'backup' })
    }
  }

  const handleRestore = async () => {
    try {
      const backupPath = prompt('Enter backup file path:')
      const password = prompt('Enter backup password:')
      if (!backupPath || !password) return

      toast.loading('Restoring system...', { id: 'restore' })
      await api.restoreSystem(backupPath, password)
      toast.success('System restored successfully', { id: 'restore' })
      await loadData()
    } catch (error: any) {
      toast.error('Restore failed', { id: 'restore' })
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
          {t('overview.title')}
        </h1>
        <p className="text-gray-600 dark:text-gray-400 mt-2">
          Monitor your OpenVPN system status and performance
        </p>
      </div>

      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-6">
        <StatCard
          title={t('overview.cpu_usage')}
          value={formatPercentage(stats?.cpu_usage || 0)}
          icon={Cpu}
        />
        <StatCard
          title={t('overview.ram_usage')}
          value={formatPercentage(stats?.ram_usage || 0)}
          icon={MemoryStick}
        />
        <StatCard
          title={t('overview.storage_usage')}
          value={formatPercentage(stats?.storage_usage || 0)}
          icon={HardDrive}
        />
        <StatCard
          title={t('overview.online_users')}
          value={stats?.online_users || 0}
          icon={UserCheck}
        />
        <StatCard
          title={t('overview.active_users')}
          value={stats?.active_users || 0}
          icon={Users}
        />
        <StatCard
          title={t('overview.total_users')}
          value={stats?.total_users || 0}
          icon={UserPlus}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Alerts */}
        <div className="card p-6">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
            <AlertTriangle className="w-5 h-5 mr-2" />
            {t('overview.alerts_notifications')}
          </h2>
          <div className="space-y-3">
            {alerts.length === 0 ? (
              <p className="text-gray-500 dark:text-gray-400 text-sm">
                No alerts at this time
              </p>
            ) : (
              alerts.map((alert) => (
                <div
                  key={alert.id}
                  className={`p-3 rounded-lg border-l-4 ${
                    alert.type === 'error'
                      ? 'bg-red-50 dark:bg-red-900/20 border-red-400'
                      : alert.type === 'warning'
                      ? 'bg-yellow-50 dark:bg-yellow-900/20 border-yellow-400'
                      : alert.type === 'success'
                      ? 'bg-green-50 dark:bg-green-900/20 border-green-400'
                      : 'bg-blue-50 dark:bg-blue-900/20 border-blue-400'
                  }`}
                >
                  <p className="font-medium text-sm text-gray-900 dark:text-white">
                    {alert.title}
                  </p>
                  <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                    {alert.message}
                  </p>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Services Status */}
        <div className="card p-6">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
            <Activity className="w-5 h-5 mr-2" />
            {t('overview.services_status')}
          </h2>
          <div className="space-y-3">
            {services.map((service) => (
              <ServiceStatusCard
                key={service.name}
                service={service}
                onRestart={handleServiceRestart}
                restarting={restartingService === service.name}
              />
            ))}
          </div>
        </div>

        {/* Quick Actions */}
        <div className="card p-6">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
            {t('overview.quick_actions')}
          </h2>
          <div className="space-y-3">
            <button
              onClick={handleBackup}
              className="w-full btn-primary flex items-center justify-center space-x-2"
            >
              <Download className="w-4 h-4" />
              <span>{t('overview.backup_now')}</span>
            </button>
            <button
              onClick={handleRestore}
              className="w-full btn-secondary flex items-center justify-center space-x-2"
            >
              <RotateCcw className="w-4 h-4" />
              <span>{t('overview.restore_system')}</span>
            </button>
          </div>
        </div>
      </div>

      {/* Traffic Chart */}
      {trafficData.length > 0 && (
        <div className="card p-6">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
            Traffic Overview (Last 24 Hours)
          </h2>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trafficData}>
                <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
                <XAxis 
                  dataKey="date" 
                  tickFormatter={(value) => new Date(value).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  className="text-xs"
                />
                <YAxis className="text-xs" />
                <Tooltip
                  labelFormatter={(value) => new Date(value).toLocaleString()}
                  formatter={(value: number, name: string) => [
                    `${(value / 1024 / 1024).toFixed(2)} MB`,
                    name
                  ]}
                />
                <Line
                  type="monotone"
                  dataKey="upload"
                  stroke="#ef4444"
                  strokeWidth={2}
                  name="Upload"
                />
                <Line
                  type="monotone"
                  dataKey="download"
                  stroke="#3b82f6"
                  strokeWidth={2}
                  name="Download"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  )
}