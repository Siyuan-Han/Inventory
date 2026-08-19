// Smoke tests: every view and component mounts and renders live data
// without a runtime error, using a stubbed API layer.
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'

import App from '../App.vue'
import DashboardView from '../views/DashboardView.vue'
import DressListView from '../views/DressListView.vue'
import DressDetailView from '../views/DressDetailView.vue'
import AddDressView from '../views/AddDressView.vue'
import DressCard from '../components/DressCard.vue'
import OrderForm from '../components/OrderForm.vue'
import SaleForm from '../components/SaleForm.vue'
import { useInventoryStore } from '../stores/inventory'

const STATUSES = [
  { value: 'ordered', label: 'Ordered', field: 'ordered_at' },
  { value: 'shipped_from_factory', label: 'Shipped from factory', field: 'shipped_from_factory_at' },
  { value: 'arrived_shipping_center', label: 'At shipping center', field: 'arrived_shipping_center_at' },
  { value: 'arrived_us', label: 'Arrived in US', field: 'arrived_us_at' },
  { value: 'received', label: 'Received', field: 'received_at' },
]

const ORDER = {
  id: 1,
  dress_id: 1,
  order_date: '2026-08-19',
  quantity: 2,
  unit_cost: '75.00',
  status: 'arrived_us',
  notes: 'split shipment',
  ordered_at: '2026-08-01T10:00:00',
  shipped_from_factory_at: '2026-08-05T10:00:00',
  arrived_shipping_center_at: '2026-08-10T10:00:00',
  arrived_us_at: '2026-08-15T10:00:00',
  received_at: null,
  created_at: '2026-08-01T10:00:00',
}

const SALE = {
  id: 1,
  dress_id: 1,
  order_id: 1,
  sale_date: '2026-08-18',
  sale_price: '400.00',
  is_cash: true,
  notes: null,
  created_at: '2026-08-18T10:00:00',
}

const DRESS = {
  id: 1,
  dress_code: 'WD001',
  style_name: 'White Lace',
  photo_url: null,
  supplier: 'Shanghai Factory',
  base_cost: '150.00',
  created_at: '2026-08-01T10:00:00',
  total_ordered: 2,
  total_received: 0,
  total_sold: 1,
  in_stock: 0,
  pending_orders: 1,
  total_revenue: '400.00',
  total_cost: '150.00',
  latest_status: 'arrived_us',
  orders: [ORDER],
  sales: [SALE],
}

const STATS = {
  total_dresses: 1,
  total_ordered: 2,
  total_received: 0,
  total_sold: 1,
  in_stock: 0,
  pending_orders: 1,
  total_revenue: '400.00',
  total_cost: '150.00',
  profit: '250.00',
  cash_sales: 1,
  status_breakdown: {
    ordered: 0,
    shipped_from_factory: 0,
    arrived_shipping_center: 0,
    arrived_us: 1,
    received: 0,
  },
}

vi.mock('../api', () => {
  const api = {
    statuses: vi.fn(async () => STATUSES),
    stats: vi.fn(async () => STATS),
    listDresses: vi.fn(async () => [DRESS]),
    getDress: vi.fn(async () => DRESS),
    createDress: vi.fn(async () => DRESS),
    updateDress: vi.fn(async () => DRESS),
    deleteDress: vi.fn(async () => null),
    listOrders: vi.fn(async () => [ORDER]),
    createOrder: vi.fn(async () => ORDER),
    updateOrder: vi.fn(async () => ORDER),
    deleteOrder: vi.fn(async () => null),
    listSales: vi.fn(async () => [SALE]),
    createSale: vi.fn(async () => SALE),
    deleteSale: vi.fn(async () => null),
  }
  return { api, default: api }
})

function makeRouter() {
  return createRouter({
    history: createWebHistory(),
    routes: [
      { path: '/', name: 'dashboard', component: { template: '<div />' } },
      { path: '/dresses', name: 'dresses', component: { template: '<div />' } },
      { path: '/dresses/new', name: 'dress-new', component: { template: '<div />' } },
      { path: '/dresses/:id', name: 'dress-detail', component: { template: '<div />' } },
      { path: '/dresses/:id/edit', name: 'dress-edit', component: { template: '<div />' } },
    ],
  })
}

async function mountWith(component, options = {}) {
  const router = makeRouter()
  await router.push(options.route || '/')
  await router.isReady()
  const wrapper = mount(component, {
    ...options,
    global: { plugins: [createPinia(), router], ...(options.global || {}) },
  })
  await flushPromises()
  return wrapper
}

describe('views and components render', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.spyOn(console, 'warn').mockImplementation(() => {})
  })

  it('App shell renders navigation', async () => {
    const wrapper = await mountWith(App)
    expect(wrapper.text()).toContain('Dress Inventory')
    expect(wrapper.text()).toContain('Dashboard')
  })

  it('Dashboard shows stat cards and the pipeline', async () => {
    const wrapper = await mountWith(DashboardView)
    expect(wrapper.text()).toContain('Dresses')
    expect(wrapper.text()).toContain('$400.00') // revenue
    expect(wrapper.text()).toContain('$250.00') // profit
    expect(wrapper.text()).toContain('Arrived in US')
  })

  it('Dress list renders a card per dress', async () => {
    const wrapper = await mountWith(DressListView)
    expect(wrapper.findAllComponents(DressCard)).toHaveLength(1)
    expect(wrapper.text()).toContain('WD001')
  })

  it('Dress detail renders the order timeline and sales', async () => {
    const wrapper = await mountWith(DressDetailView, {
      props: { id: '1' },
      route: '/dresses/1',
    })
    expect(wrapper.text()).toContain('WD001')
    expect(wrapper.text()).toContain('Shanghai Factory')
    // The next unreached stage is offered as an action.
    expect(wrapper.text()).toContain('Mark received')
    expect(wrapper.text()).toContain('Cash')
  })

  it('Dress detail opens the order and sale modals', async () => {
    const wrapper = await mountWith(DressDetailView, {
      props: { id: '1' },
      route: '/dresses/1',
    })
    const buttons = wrapper.findAll('button')
    await buttons.find((b) => b.text() === 'Add order').trigger('click')
    expect(wrapper.findComponent(OrderForm).exists()).toBe(true)

    await buttons.find((b) => b.text() === 'Record sale').trigger('click')
    expect(wrapper.findComponent(SaleForm).exists()).toBe(true)
  })

  it('Add dress form validates a missing code', async () => {
    const wrapper = await mountWith(AddDressView, { route: '/dresses/new' })
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(wrapper.text()).toContain('A dress code is required.')
  })

  it('Edit dress prefills from the API', async () => {
    const wrapper = await mountWith(AddDressView, {
      props: { id: '1' },
      route: '/dresses/1/edit',
    })
    expect(wrapper.find('input').element.value).toBe('WD001')
    expect(wrapper.text()).toContain('Save changes')
  })
})

describe('inventory store', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('surfaces API errors instead of throwing past the caller', async () => {
    const store = useInventoryStore()
    const { api } = await import('../api')
    api.listDresses.mockRejectedValueOnce(new Error('boom'))
    await expect(store.fetchDresses()).rejects.toThrow('boom')
    expect(store.error).toBe('boom')
    expect(store.loading).toBe(false)
  })

  it('labels statuses through the pipeline', async () => {
    const store = useInventoryStore()
    await store.loadStatuses()
    expect(store.statusLabel('arrived_us')).toBe('Arrived in US')
    expect(store.statusIndex('received')).toBe(4)
  })
})
