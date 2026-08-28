import { defineStore } from 'pinia'
import api from '../api'

export const useInventoryStore = defineStore('inventory', {
  state: () => ({
    dresses: [],
    dress: null, // the dress currently open in the detail view
    stats: null,
    monthlyStats: null,
    statuses: [],
    suppliers: [],
    search: '',
    showArchived: false,
    supplierFilter: '',
    statusFilter: '',
    loading: false,
    saving: false,
    error: null,
  }),

  getters: {
    statusLabel: (state) => (value) =>
      state.statuses.find((s) => s.value === value)?.label || value || '—',
    statusIndex: (state) => (value) => state.statuses.findIndex((s) => s.value === value),
    /** The status right after `value` in the pipeline, or null if there isn't one. */
    nextStatus: (state) => (value) => {
      const index = state.statuses.findIndex((s) => s.value === value)
      return index >= 0 && index < state.statuses.length - 1 ? state.statuses[index + 1] : null
    },
  },

  actions: {
    /** Run an API call with shared loading/error handling. */
    async run(fn, { flag = 'loading' } = {}) {
      this[flag] = true
      this.error = null
      try {
        return await fn()
      } catch (err) {
        this.error = err.message
        throw err
      } finally {
        this[flag] = false
      }
    },

    async loadStatuses() {
      if (this.statuses.length) return this.statuses
      this.statuses = await api.statuses()
      return this.statuses
    },

    async nextDressCode(category) {
      const { dress_code } = await api.nextDressCode(category)
      return dress_code
    },

    async fetchSuppliers(category) {
      this.suppliers = await api.suppliers(category)
      return this.suppliers
    },

    async fetchStats() {
      return this.run(async () => {
        this.stats = await api.stats()
      })
    },

    async fetchMonthlyStats(month) {
      return this.run(async () => {
        this.monthlyStats = await api.monthlyStats(month)
        return this.monthlyStats
      })
    },

    async fetchDresses(filters = {}) {
      const {
        search = this.search,
        archived = this.showArchived,
        supplier = this.supplierFilter,
        status = this.statusFilter,
        category,
      } = filters
      this.search = search
      this.showArchived = archived
      this.supplierFilter = supplier
      this.statusFilter = status
      return this.run(async () => {
        this.dresses = await api.listDresses({ search, archived, supplier, status, category })
      })
    },

    async fetchDress(id) {
      return this.run(async () => {
        this.dress = await api.getDress(id)
        return this.dress
      })
    },

    async createDress(data) {
      return this.run(async () => {
        const created = await api.createDress(data)
        this.dresses.push(created)
        return created
      }, { flag: 'saving' })
    },

    async createSecondhandDress(data) {
      return this.run(async () => {
        const created = await api.createSecondhandDress(data)
        this.dresses.push(created)
        return created
      }, { flag: 'saving' })
    },

    async updateDress(id, data) {
      return this.run(async () => {
        this.dress = await api.updateDress(id, data)
        this.replaceInList(this.dress)
        return this.dress
      }, { flag: 'saving' })
    },

    async deleteDress(id) {
      return this.run(async () => {
        await api.deleteDress(id)
        this.dresses = this.dresses.filter((d) => d.id !== Number(id))
        if (this.dress?.id === Number(id)) this.dress = null
      }, { flag: 'saving' })
    },

    async archiveDress(id) {
      return this.run(async () => {
        this.dress = await api.archiveDress(id)
        // An archived dress drops out of whichever list is currently active.
        this.dresses = this.dresses.filter((d) => d.id !== Number(id))
        return this.dress
      }, { flag: 'saving' })
    },

    async restoreDress(id) {
      return this.run(async () => {
        this.dress = await api.restoreDress(id)
        this.dresses = this.dresses.filter((d) => d.id !== Number(id))
        return this.dress
      }, { flag: 'saving' })
    },

    async createOrder(data) {
      return this.run(async () => {
        await api.createOrder(data)
        await this.refreshDress(data.dress_id)
      }, { flag: 'saving' })
    },

    async setOrderStatus(orderId, status, dressId, statusDate, trackingNumber) {
      return this.updateOrder(orderId, dressId, {
        status,
        status_date: statusDate || undefined,
        ...(trackingNumber !== undefined ? { tracking_number: trackingNumber || null } : {}),
      })
    },

    /** Generic partial order update, e.g. { tracking_number } on its own. */
    async updateOrder(orderId, dressId, patch) {
      return this.run(async () => {
        await api.updateOrder(orderId, patch)
        await this.refreshDress(dressId)
      }, { flag: 'saving' })
    },

    /** Advance several orders (all currently at the same status) together. */
    async bulkAdvanceOrders(orderIds, status, statusDate) {
      return this.run(async () => {
        const updated = await api.bulkUpdateOrderStatus({
          order_ids: orderIds,
          status,
          status_date: statusDate || undefined,
        })
        this.stats = null // rollups changed; the dashboard will refetch
        return updated
      }, { flag: 'saving' })
    },

    async deleteOrder(orderId, dressId) {
      return this.run(async () => {
        await api.deleteOrder(orderId)
        await this.refreshDress(dressId)
      }, { flag: 'saving' })
    },

    async createSale(data) {
      return this.run(async () => {
        await api.createSale(data)
        await this.refreshDress(data.dress_id)
      }, { flag: 'saving' })
    },

    async deleteSale(saleId, dressId) {
      return this.run(async () => {
        await api.deleteSale(saleId)
        await this.refreshDress(dressId)
      }, { flag: 'saving' })
    },

    /** Re-read one dress and keep the cached list row in sync with it. */
    async refreshDress(dressId) {
      this.dress = await api.getDress(dressId)
      this.replaceInList(this.dress)
      this.stats = null // rollups changed; the dashboard will refetch
      return this.dress
    },

    replaceInList(dress) {
      const index = this.dresses.findIndex((d) => d.id === dress.id)
      if (index !== -1) this.dresses.splice(index, 1, { ...this.dresses[index], ...dress })
    },

    clearError() {
      this.error = null
    },
  },
})
