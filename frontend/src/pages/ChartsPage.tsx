import React, { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { BarChart3, Download, Calendar, TrendingUp, Users, Activity } from 'lucide-react'
import toast from 'react-hot-toast'
import { api } from '@/lib/api'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { formatBytes } from '@/lib/utils'
import { TrafficData } from '@/types'
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend
} from 'recharts'

type TimeRange = 'daily' | 'weekly' | 'monthly'

export function ChartsPage() {
  const { t } = useTranslation()
  const [trafficData, setTrafficData] = useState<TrafficData[]>([])
  const [timeRange, setTimeRange] = useState<TimeRange>('weekly')
  const [loading, setLoading] = useState(true)
  const [userActivityData, setUserActivityData] = useState<any[]>([])
  const [systemHealthData, setSystemHealthData] = useState<any[]>([])

  useEffect(() => {
    loadChartData()
  }, [timeRange])

  const loadChartData = async () => {
    setLoading(true)
    try {
      const [traffic, users] = await Promise.all([
        api.getTrafficData(timeRange),
        api.getUsers()
      ])

      setTrafficData(traffic)

      // Generate mock user activity data
      const activityData = users.slice(0, 10).map((user, index) => ({
        username: user.username,
        sessions: Math.floor(Math.random() * 50) + 10,
        duration: Math.floor(Math.random() * 24) + 1,
        data_used: user.bytes_used
      }))
      setUserActivityData(activityData)

      // Generate mock system health data
      const healthData = [
        { name: 'CPU', value: Math.random() * 100, color: '#3b82f6' },
        { name: 'RAM', value: Math.random() * 100, color: '#10b981' },
        { name: 'Storage', value: Math.random() * 100, color: '#f59e0b' },
        { name: 'Network', value: Math.random() * 100, color: '#ef4444' }
      ]
      setSystemHealthData(healthData)

    } catch (error: any) {
      toast.error('Failed to load chart data')
      console.error('Error loading charts:', error)
    } finally {
      setLoading(false)
    }
  }

  const exportData = () => {
    const csvContent = [
      ['Date', 'Upload (MB)', 'Download (MB)', 'Total (MB)'],
      ...trafficData.map(item => [
        item.date,
        (item.upload / 1024 / 1024).toFixed(2),
        (item.download / 1024 / 1024).toFixed(2),
        (item.total / 1024 / 1024).toFixed(2)
      ])
    ].map(row => row.join(',')).join('\n')

    const blob = new Blob([csvContent], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `traffic-data-${timeRange}.csv`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    toast.success('Data exported successfully')
  }

  const formatXAxisTick = (value: string) => {
    const date = new Date(value)
    if (timeRange === 'daily') {
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    } else if (timeRange === 'weekly') {
      return date.toLocaleDateString([], { weekday: 'short' })
    } else {
      return date.toLocaleDateString([], { month: 'short', day: 'numeric' })
    }
  }

  const formatTooltipValue = (value: number, name: string) => {
    return [formatBytes(value), name]
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
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            {t('charts.title')}
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-2">
            Analyze traffic patterns and system performance
          </p>
        </div>
        
        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-2 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-1">
            {(['daily', 'weekly', 'monthly'] as TimeRange[]).map((range) => (
              <button
                key={range}
                onClick={() => setTimeRange(range)}
                className={`px-3 py-1 text-sm rounded-md transition-colors ${
                  timeRange === range
                    ? 'bg-primary-600 text-white'
                    : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
                }`}
              >
                {t(`charts.${range}`)}
              </button>
            ))}
          </div>
          
          <button
            onClick={exportData}
            className="btn-secondary flex items-center space-x-2"
          >
            <Download className="w-4 h-4" />
            <span>{t('charts.export_data')}</span>
          </button>
        </div>
      </div>

      {/* Traffic Overview */}
      <div className="card p-6">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
          <TrendingUp className="w-5 h-5 mr-2" />
          {t('charts.traffic_overview')}
        </h2>
        
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={trafficData}>
              <defs>
                <linearGradient id="uploadGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#ef4444" stopOpacity={0.8}/>
                  <stop offset="95%" stopColor="#ef4444" stopOpacity={0.1}/>
                </linearGradient>
                <linearGradient id="downloadGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.8}/>
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.1}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
              <XAxis 
                dataKey="date" 
                tickFormatter={formatXAxisTick}
                className="text-xs"
              />
              <YAxis 
                tickFormatter={(value) => formatBytes(value)}
                className="text-xs"
              />
              <Tooltip
                labelFormatter={(value) => new Date(value).toLocaleString()}
                formatter={formatTooltipValue}
                contentStyle={{
                  backgroundColor: 'rgba(255, 255, 255, 0.95)',
                  border: '1px solid #e5e7eb',
                  borderRadius: '0.5rem'
                }}
              />
              <Legend />
              <Area
                type="monotone"
                dataKey="upload"
                stackId="1"
                stroke="#ef4444"
                fill="url(#uploadGradient)"
                name={t('charts.upload')}
              />
              <Area
                type="monotone"
                dataKey="download"
                stackId="1"
                stroke="#3b82f6"
                fill="url(#downloadGradient)"
                name={t('charts.download')}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* User Activity */}
        <div className="card p-6">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
            <Users className="w-5 h-5 mr-2" />
            {t('charts.user_activity')}
          </h2>
          
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={userActivityData} layout="horizontal">
                <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
                <XAxis type="number" className="text-xs" />
                <YAxis 
                  type="category" 
                  dataKey="username" 
                  className="text-xs"
                  width={80}
                />
                <Tooltip
                  formatter={(value, name) => [
                    name === 'data_used' ? formatBytes(value as number) : value,
                    name === 'data_used' ? 'Data Used' : 'Sessions'
                  ]}
                  contentStyle={{
                    backgroundColor: 'rgba(255, 255, 255, 0.95)',
                    border: '1px solid #e5e7eb',
                    borderRadius: '0.5rem'
                  }}
                />
                <Bar dataKey="sessions" fill="#3b82f6" name="Sessions" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* System Health */}
        <div className="card p-6">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
            <Activity className="w-5 h-5 mr-2" />
            {t('charts.system_health')}
          </h2>
          
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={systemHealthData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {systemHealthData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(value) => [`${(value as number).toFixed(1)}%`, 'Usage']}
                  contentStyle={{
                    backgroundColor: 'rgba(255, 255, 255, 0.95)',
                    border: '1px solid #e5e7eb',
                    borderRadius: '0.5rem'
                  }}
                />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Traffic Statistics Table */}
      <div className="card">
        <div className="p-6 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white flex items-center">
            <BarChart3 className="w-5 h-5 mr-2" />
            Traffic Statistics
          </h2>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 dark:bg-gray-700">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Date
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  {t('charts.upload')}
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  {t('charts.download')}
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  {t('charts.total')}
                </th>
              </tr>
            </thead>
            <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
              {trafficData.slice(-10).reverse().map((item, index) => (
                <tr key={index} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                    {new Date(item.date).toLocaleDateString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                    {formatBytes(item.upload)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                    {formatBytes(item.download)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">
                    {formatBytes(item.total)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}