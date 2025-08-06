import React, { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Users,
  UserPlus,
  Search,
  MoreVertical,
  Download,
  Key,
  Settings,
  Trash2,
  UserCheck,
  UserX
} from 'lucide-react'
import toast from 'react-hot-toast'
import { api } from '@/lib/api'
import { StatCard } from '@/components/ui/StatCard'
import { Modal } from '@/components/ui/Modal'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { formatBytes, validateUsername } from '@/lib/utils'
import { User } from '@/types'

export function UsersPage() {
  const { t } = useTranslation()
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showPasswordModal, setShowPasswordModal] = useState(false)
  const [showQuotaModal, setShowQuotaModal] = useState(false)
  const [selectedUser, setSelectedUser] = useState<string | null>(null)
  const [dropdownOpen, setDropdownOpen] = useState<string | null>(null)

  // Form states
  const [newUsername, setNewUsername] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [quotaGB, setQuotaGB] = useState('')

  useEffect(() => {
    loadUsers()
  }, [])

  const loadUsers = async () => {
    try {
      const usersData = await api.getUsers()
      setUsers(usersData)
    } catch (error: any) {
      toast.error('Failed to load users')
      console.error('Error loading users:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!validateUsername(newUsername)) {
      toast.error('Invalid username format')
      return
    }

    try {
      await api.createUser(newUsername, newPassword || undefined)
      toast.success(t('users.user_created'))
      setShowCreateModal(false)
      setNewUsername('')
      setNewPassword('')
      await loadUsers()
    } catch (error: any) {
      toast.error(error.response?.data?.message || 'Failed to create user')
    }
  }

  const handleDeleteUser = async (username: string) => {
    if (!confirm(`Are you sure you want to delete user "${username}"?`)) return

    try {
      await api.removeUser(username)
      toast.success(t('users.user_deleted'))
      await loadUsers()
    } catch (error: any) {
      toast.error('Failed to delete user')
    }
  }

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedUser || !newPassword.trim()) return

    try {
      await api.changeUserPassword(selectedUser, newPassword)
      toast.success(t('users.password_changed'))
      setShowPasswordModal(false)
      setNewPassword('')
      setSelectedUser(null)
    } catch (error: any) {
      toast.error('Failed to change password')
    }
  }

  const handleSetQuota = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedUser) return

    const quota = parseFloat(quotaGB) || 0
    if (quota < 0) {
      toast.error('Quota cannot be negative')
      return
    }

    try {
      await api.setUserQuota(selectedUser, quota)
      toast.success(t('users.quota_updated'))
      setShowQuotaModal(false)
      setQuotaGB('')
      setSelectedUser(null)
      await loadUsers()
    } catch (error: any) {
      toast.error('Failed to update quota')
    }
  }

  const handleDownloadConfig = async (username: string) => {
    try {
      const config = await api.getUserConfig(username)
      const blob = new Blob([config], { type: 'text/plain' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${username}.ovpn`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
      toast.success('Config downloaded')
    } catch (error: any) {
      toast.error('Failed to download config')
    }
  }

  const filteredUsers = users.filter(user =>
    user.username.toLowerCase().includes(searchTerm.toLowerCase())
  )

  const stats = {
    online_users: users.filter(u => u.status === 'active').length,
    active_users: users.length,
    total_users: users.length
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
            {t('users.title')}
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-2">
            Manage OpenVPN users and their access
          </p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="btn-primary flex items-center space-x-2"
        >
          <UserPlus className="w-4 h-4" />
          <span>{t('users.create_user')}</span>
        </button>
      </div>

      {/* Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <StatCard
          title={t('overview.online_users')}
          value={stats.online_users}
          icon={UserCheck}
        />
        <StatCard
          title={t('overview.active_users')}
          value={stats.active_users}
          icon={Users}
        />
        <StatCard
          title={t('overview.total_users')}
          value={stats.total_users}
          icon={UserPlus}
        />
      </div>

      {/* Search and Table */}
      <div className="card">
        <div className="p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="relative">
            <Search className="w-5 h-5 absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder={t('common.search')}
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="input-field pl-10"
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 dark:bg-gray-700">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  {t('common.username')}
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  {t('common.status')}
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Auth Types
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  {t('users.data_usage')}
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  {t('users.quota')}
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  {t('common.actions')}
                </th>
              </tr>
            </thead>
            <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
              {filteredUsers.map((user) => (
                <tr key={user.username} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <div className="w-8 h-8 bg-primary-100 dark:bg-primary-900 rounded-full flex items-center justify-center">
                        <span className="text-sm font-medium text-primary-600 dark:text-primary-400">
                          {user.username.charAt(0).toUpperCase()}
                        </span>
                      </div>
                      <div className="ml-3">
                        <div className="text-sm font-medium text-gray-900 dark:text-white">
                          {user.username}
                        </div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                      user.status === 'active'
                        ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                        : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                    }`}>
                      {user.status === 'active' ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                    {user.auth_types.join(', ') || 'None'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                    {formatBytes(user.bytes_used)}
                    {user.usage_percentage !== undefined && (
                      <div className="w-full bg-gray-200 rounded-full h-1 mt-1">
                        <div
                          className="bg-primary-600 h-1 rounded-full"
                          style={{ width: `${Math.min(user.usage_percentage, 100)}%` }}
                        />
                      </div>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                    {user.quota_bytes > 0 ? formatBytes(user.quota_bytes) : t('users.unlimited')}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <div className="relative">
                      <button
                        onClick={() => setDropdownOpen(dropdownOpen === user.username ? null : user.username)}
                        className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
                      >
                        <MoreVertical className="w-4 h-4" />
                      </button>
                      
                      {dropdownOpen === user.username && (
                        <div className="absolute right-0 mt-2 w-48 bg-white dark:bg-gray-800 rounded-md shadow-lg z-10 border border-gray-200 dark:border-gray-700">
                          <button
                            onClick={() => {
                              handleDownloadConfig(user.username)
                              setDropdownOpen(null)
                            }}
                            className="w-full text-left px-4 py-2 text-sm hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center space-x-2"
                          >
                            <Download className="w-4 h-4" />
                            <span>{t('users.download_config')}</span>
                          </button>
                          <button
                            onClick={() => {
                              setSelectedUser(user.username)
                              setShowPasswordModal(true)
                              setDropdownOpen(null)
                            }}
                            className="w-full text-left px-4 py-2 text-sm hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center space-x-2"
                          >
                            <Key className="w-4 h-4" />
                            <span>{t('users.change_password')}</span>
                          </button>
                          <button
                            onClick={() => {
                              setSelectedUser(user.username)
                              setQuotaGB((user.quota_bytes / (1024 * 1024 * 1024)).toString())
                              setShowQuotaModal(true)
                              setDropdownOpen(null)
                            }}
                            className="w-full text-left px-4 py-2 text-sm hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center space-x-2"
                          >
                            <Settings className="w-4 h-4" />
                            <span>{t('users.set_quota')}</span>
                          </button>
                          <button
                            onClick={() => {
                              handleDeleteUser(user.username)
                              setDropdownOpen(null)
                            }}
                            className="w-full text-left px-4 py-2 text-sm hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center space-x-2 text-red-600 dark:text-red-400"
                          >
                            <Trash2 className="w-4 h-4" />
                            <span>{t('common.delete')}</span>
                          </button>
                        </div>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {filteredUsers.length === 0 && (
            <div className="text-center py-12">
              <UserX className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-500 dark:text-gray-400">
                {searchTerm ? 'No users found matching your search' : 'No users created yet'}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Create User Modal */}
      <Modal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        title={t('users.new_user')}
      >
        <form onSubmit={handleCreateUser} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              {t('common.username')}
            </label>
            <input
              type="text"
              value={newUsername}
              onChange={(e) => setNewUsername(e.target.value)}
              className="input-field"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              {t('common.password')} (Optional)
            </label>
            <input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="input-field"
            />
          </div>
          <div className="flex justify-end space-x-3">
            <button
              type="button"
              onClick={() => setShowCreateModal(false)}
              className="btn-secondary"
            >
              {t('common.cancel')}
            </button>
            <button type="submit" className="btn-primary">
              {t('common.create')}
            </button>
          </div>
        </form>
      </Modal>

      {/* Change Password Modal */}
      <Modal
        isOpen={showPasswordModal}
        onClose={() => setShowPasswordModal(false)}
        title={t('users.change_password')}
      >
        <form onSubmit={handleChangePassword} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              {t('users.new_password')}
            </label>
            <input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="input-field"
              required
            />
          </div>
          <div className="flex justify-end space-x-3">
            <button
              type="button"
              onClick={() => setShowPasswordModal(false)}
              className="btn-secondary"
            >
              {t('common.cancel')}
            </button>
            <button type="submit" className="btn-primary">
              {t('common.save')}
            </button>
          </div>
        </form>
      </Modal>

      {/* Set Quota Modal */}
      <Modal
        isOpen={showQuotaModal}
        onClose={() => setShowQuotaModal(false)}
        title={t('users.set_quota')}
      >
        <form onSubmit={handleSetQuota} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              {t('users.quota_gb')}
            </label>
            <input
              type="number"
              min="0"
              step="0.1"
              value={quotaGB}
              onChange={(e) => setQuotaGB(e.target.value)}
              className="input-field"
              placeholder={t('users.zero_unlimited')}
              required
            />
          </div>
          <div className="flex justify-end space-x-3">
            <button
              type="button"
              onClick={() => setShowQuotaModal(false)}
              className="btn-secondary"
            >
              {t('common.cancel')}
            </button>
            <button type="submit" className="btn-primary">
              {t('common.save')}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  )
}