import axios, { AxiosInstance, AxiosResponse } from 'axios'
import toast from 'react-hot-toast'
import { User, SystemStatus, UserQuotaStatus, OpenVPNSettings } from '@/types'

class ApiClient {
  private client: AxiosInstance
  private apiKey: string | null = null

  constructor() {
    this.client = axios.create({
      baseURL: '/api',
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    })

    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          this.clearAuth()
          window.location.href = '/login'
        }
        return Promise.reject(error)
      }
    )
  }

  setApiKey(key: string) {
    this.apiKey = key
    this.client.defaults.headers['X-API-Key'] = key
    localStorage.setItem('openvpn_api_key', key)
  }

  clearAuth() {
    this.apiKey = null
    delete this.client.defaults.headers['X-API-Key']
    localStorage.removeItem('openvpn_api_key')
  }

  loadStoredAuth() {
    const stored = localStorage.getItem('openvpn_api_key')
    if (stored) {
      this.setApiKey(stored)
    }
  }

  isAuthenticated(): boolean {
    return !!this.apiKey
  }

  async testConnection(): Promise<boolean> {
    try {
      await this.client.get('/health')
      return true
    } catch {
      return false
    }
  }

  async login(apiKey: string): Promise<boolean> {
    try {
      const tempClient = axios.create({
        baseURL: '/api',
        headers: { 'X-API-Key': apiKey }
      })
      
      await tempClient.get('/health')
      this.setApiKey(apiKey)
      return true
    } catch (error: any) {
      if (error.response?.status === 401) {
        throw new Error('Invalid API key')
      }
      throw new Error('Connection failed')
    }
  }

  // User Management
  async getUsers(): Promise<User[]> {
    const response = await this.client.get('/users')
    return response.data.users || []
  }

  async createUser(username: string, password?: string): Promise<any> {
    const response = await this.client.post('/users', {
      username,
      password: password || undefined
    })
    return response.data
  }

  async removeUser(username: string): Promise<void> {
    await this.client.delete(`/users/${username}`)
  }

  async changeUserPassword(username: string, newPassword: string): Promise<void> {
    await this.client.put(`/users/${username}/password`, {
      new_password: newPassword
    })
  }

  async getUserConfig(username: string): Promise<string> {
    const response = await this.client.get(`/users/${username}/config`)
    return response.data.config
  }

  async getSharedConfig(): Promise<string> {
    const response = await this.client.get('/users/shared-config')
    return response.data.config
  }

  // Quota Management
  async setUserQuota(username: string, quotaGB: number): Promise<void> {
    await this.client.put(`/quota/${username}`, {
      quota_gb: quotaGB
    })
  }

  async getUserStatus(username: string): Promise<UserQuotaStatus> {
    const response = await this.client.get(`/quota/${username}`)
    return response.data.status
  }

  // System Management
  async getSystemStatus(): Promise<SystemStatus> {
    const response = await this.client.get('/system/status')
    return {
      installed: response.data.installed,
      users_count: response.data.users_count,
      settings: response.data.settings
    }
  }

  async createBackup(password: string, backupDir?: string): Promise<string> {
    const response = await this.client.post('/system/backup', {
      password,
      backup_dir: backupDir
    })
    return response.data.backup_file
  }

  async restoreSystem(backupPath: string, password: string): Promise<void> {
    await this.client.post('/system/restore', {
      backup_path: backupPath,
      password
    })
  }

  async uninstallSystem(): Promise<void> {
    await this.client.delete('/system/uninstall', {
      data: { confirm: true }
    })
  }

  // Mock endpoints for features not yet implemented in backend
  async getSystemStats() {
    // This would be implemented in the backend
    return {
      cpu_usage: Math.random() * 100,
      ram_usage: Math.random() * 100,
      storage_usage: Math.random() * 100,
      online_users: Math.floor(Math.random() * 10),
      active_users: Math.floor(Math.random() * 20),
      total_users: Math.floor(Math.random() * 50)
    }
  }

  async getServiceStatus() {
    return [
      { name: 'OpenVPN', status: 'running', uptime: '2d 5h 30m' },
      { name: 'Monitoring', status: 'running', uptime: '2d 5h 29m' },
      { name: 'API', status: 'running', uptime: '2d 5h 30m' }
    ]
  }

  async restartService(serviceName: string): Promise<void> {
    // Mock implementation
    await new Promise(resolve => setTimeout(resolve, 1000))
  }

  async getTrafficData(timeRange: string) {
    // Mock traffic data
    const days = timeRange === 'weekly' ? 7 : timeRange === 'monthly' ? 30 : 1
    const data = []
    
    for (let i = days - 1; i >= 0; i--) {
      const date = new Date()
      date.setDate(date.getDate() - i)
      data.push({
        date: date.toISOString().split('T')[0],
        upload: Math.random() * 1000,
        download: Math.random() * 2000,
        total: Math.random() * 3000
      })
    }
    
    return data
  }

  async updateOpenVPNSettings(settings: Partial<OpenVPNSettings>): Promise<void> {
    // This would be implemented in the backend
    await new Promise(resolve => setTimeout(resolve, 1000))
  }
}

export const api = new ApiClient()

// Initialize stored auth on app load
api.loadStoredAuth()