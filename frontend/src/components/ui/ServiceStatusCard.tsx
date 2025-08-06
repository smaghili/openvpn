import React from 'react'
import { RefreshCw, Play, Square } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { ServiceStatus } from '@/types'
import { cn } from '@/lib/utils'

interface ServiceStatusCardProps {
  service: ServiceStatus
  onRestart: (serviceName: string) => void
  restarting: boolean
}

export function ServiceStatusCard({ service, onRestart, restarting }: ServiceStatusCardProps) {
  const { t } = useTranslation()

  return (
    <div className="flex items-center justify-between p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
      <div className="flex items-center space-x-3">
        <div
          className={cn(
            'w-3 h-3 rounded-full',
            service.status === 'running'
              ? 'bg-green-500'
              : 'bg-red-500'
          )}
        />
        <div>
          <p className="font-medium text-gray-900 dark:text-white">
            {service.name}
          </p>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {service.status === 'running' 
              ? `${t('overview.service_running')} • ${service.uptime}` 
              : t('overview.service_stopped')
            }
          </p>
        </div>
      </div>
      
      <button
        onClick={() => onRestart(service.name)}
        disabled={restarting}
        className="btn-secondary text-sm flex items-center space-x-2 disabled:opacity-50"
      >
        {restarting ? (
          <RefreshCw className="w-4 h-4 animate-spin" />
        ) : service.status === 'running' ? (
          <RefreshCw className="w-4 h-4" />
        ) : (
          <Play className="w-4 h-4" />
        )}
        <span>{t('overview.restart')}</span>
      </button>
    </div>
  )
}