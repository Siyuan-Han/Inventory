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
import ComboBox from '../components/ComboBox.vue'
import { useInventoryStore } from '../stores/inventory'

const STATUSES = [
  { value: 'ordered', label: 'Ordered', field: 'ordered_at' },
  { value: 'shipped_from_factory', label: 'Shipped from factory', field: 'shipped_from_factory_at' },
  { value: 'arrived_shipping_center', label: 'Shipped from shipping center', field: 'arrived_shipping_center_at' },
  { value: 'received', label: 'Received', field: 'received_at' },
]

const ORDER = {
  id: 1,
  dress_id: 1,
  order_date: '2026-08-19',
  quantity: 2,
  unit_cost: '75.00',
  status: 'arrived_shipping_center',
  notes: 'split shipment',
  ordered_at: '2026-08-01T10:00:00',
  shipped_from_factory_at: '2026-08-05T10:00:00',
  arrived_shipping_center_at: '2026-08-10T10:00:00',
  arrived_us_at: null,
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
  cash_amount: null,
  notes: null,
  created_at: '2026-08-18T10:00:00',
}

const SPLIT_SALE = {
  id: 2,
  dress_id: 1,
  order_id: null,
  sale_date: '2026-08-19',
  sale_price: '200.00',
  is_cash: false,
  cash_amount: '120.00',
  notes: null,
  created_at: '2026-08-19T10:00:00',
}

const DRESS = {
  id: 1,
  dress_code: 'WD001',
  style_name: 'White Lace',
  photo_url: null,
  supplier: 'Shanghai Factory',
  base_cost: '150.00',
  created_at: '2026-08-01T10:00:00',
  archived_at: null,
  total_ordered: 2,
  total_received: 0,
  total_sold: 1,
  in_stock: 0,
  pending_orders: 1,
  total_revenue: '400.00',
  total_cost: '150.00',
  latest_status: 'arrived_shipping_center',
  orders: [ORDER],
  sales: [SALE, SPLIT_SALE],
}

const STATS = {
  total_dresses: 1,
  total_ordered: 2,
  total_received: 0,
  total_sold: 2,
  in_stock: 0,
  pending_orders: 1,
  total_revenue: '600.00',
  total_cost: '150.00',
  cost_of_goods_sold: '150.00',
  inventory_value: '0',
  profit: '450.00',
  cash_sales: 1,
  cash_revenue: '520.00',
  card_revenue: '80.00',
  status_breakdown: {
    ordered: 0,
    shipped_from_factory: 0,
    arrived_shipping_center: 1,
    received: 0,
  },
}

const MONTHLY_STATS = {
  month: '2026-08',
  orders_count: 1,
  sales_count: 2,
  revenue: '600.00',
  cost: '150.00',
  inventory_spend: '75.00',
  profit: '450.00',
  cash_sales: 1,
  cash_revenue: '520.00',
  card_revenue: '80.00',
}

vi.mock('../api', () => {
  const api = {
    statuses: vi.fn(async () => STATUSES),
    stats: vi.fn(async () => STATS),
    monthlyStats: vi.fn(async () => MONTHLY_STATS),
    listDresses: vi.fn(async () => [DRESS]),
    nextDressCode: vi.fn(async () => ({ dress_code: 'WD002' })),
    suppliers: vi.fn(async () => ['Shanghai Factory', 'Beijing Silks']),
    getDress: vi.fn(async () => DRESS),
    createDress: vi.fn(async () => DRESS),
    updateDress: vi.fn(async () => DRESS),
    archiveDress: vi.fn(async () => ({ ...DRESS, archived_at: '2026-08-19T10:00:00' })),
    restoreDress: vi.fn(async () => ({ ...DRESS, archived_at: null })),
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

  it('Dashboard shows stat cards, cash/card revenue, the pipeline and a month dropdown', async () => {
    const wrapper = await mountWith(DashboardView)
    expect(wrapper.text()).toContain('Dresses')
    expect(wrapper.text()).toContain('$600.00') // all-time revenue
    expect(wrapper.text()).toContain('Cost')
    expect(wrapper.text()).toContain('sold dresses only')
    expect(wrapper.text()).toContain('Inventory')
    expect(wrapper.text()).toContain('unsold stock, at cost')
    expect(wrapper.text()).toContain('$450.00') // all-time profit (revenue - cost of goods sold)
    expect(wrapper.text()).toContain('Revenue by payment')
    expect(wrapper.text()).toContain('$520.00') // cash
    expect(wrapper.text()).toContain('$80.00') // card
    expect(wrapper.text()).toContain('Shipped from shipping center')
    expect(wrapper.text()).toContain('Monthly summary')
    expect(wrapper.text()).toContain('$75.00') // monthly inventory spend
    expect(wrapper.text()).toContain('spent on new stock')
    expect(wrapper.text()).toContain('2 sale(s)')
    // Month picker is a dropdown, not prev/next arrows.
    const select = wrapper.findAll('select').at(-1)
    expect(select.findAll('option').length).toBeGreaterThan(1)
  })

  it('Dress list renders a card per dress and toggles archived', async () => {
    const wrapper = await mountWith(DressListView)
    expect(wrapper.findAllComponents(DressCard)).toHaveLength(1)
    expect(wrapper.text()).toContain('WD001')

    const { api } = await import('../api')
    await wrapper.findAll('button').find((b) => b.text() === 'Archived').trigger('click')
    await flushPromises()
    expect(api.listDresses).toHaveBeenLastCalledWith(
      expect.objectContaining({ archived: true }),
    )
  })

  it('Dress list filters by supplier and by status', async () => {
    const wrapper = await mountWith(DressListView)
    const { api } = await import('../api')

    const [supplierSelect, statusSelect] = wrapper.findAll('select')
    await supplierSelect.setValue('Shanghai Factory')
    await flushPromises()
    expect(api.listDresses).toHaveBeenLastCalledWith(
      expect.objectContaining({ supplier: 'Shanghai Factory' }),
    )

    await statusSelect.setValue('arrived_shipping_center')
    await flushPromises()
    expect(api.listDresses).toHaveBeenLastCalledWith(
      expect.objectContaining({ status: 'arrived_shipping_center' }),
    )
  })

  it('Dress detail renders the order timeline and sales, including a split payment', async () => {
    const wrapper = await mountWith(DressDetailView, {
      props: { id: '1' },
      route: '/dresses/1',
    })
    expect(wrapper.text()).toContain('WD001')
    expect(wrapper.text()).toContain('Shanghai Factory')
    // The next unreached stage is offered as an action.
    expect(wrapper.text()).toContain('Mark received')
    expect(wrapper.text()).toContain('Cash')
    // The split sale shows both portions, not just one badge.
    expect(wrapper.text()).toContain('$120.00 cash + $80.00 card')
    // No raw order id leaks into the sales list.
    expect(wrapper.text()).not.toContain('#1')
  })

  it('Dress detail asks for a date before advancing an order status', async () => {
    const wrapper = await mountWith(DressDetailView, {
      props: { id: '1' },
      route: '/dresses/1',
    })
    const { api } = await import('../api')
    await wrapper.findAll('button').find((b) => b.text() === 'Mark received').trigger('click')
    expect(wrapper.find('input[type="date"]').exists()).toBe(true)

    await wrapper.findAll('button').find((b) => b.text() === 'Confirm').trigger('click')
    await flushPromises()
    expect(api.updateOrder).toHaveBeenCalledWith(
      1,
      expect.objectContaining({ status: 'received', status_date: expect.any(String) }),
    )
  })

  it('Dress detail can archive a dress', async () => {
    const wrapper = await mountWith(DressDetailView, {
      props: { id: '1' },
      route: '/dresses/1',
    })
    const { api } = await import('../api')
    // stub the confirm() dialog
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    await wrapper.findAll('button').find((b) => b.text() === 'Archive').trigger('click')
    await flushPromises()
    expect(api.archiveDress).toHaveBeenCalledWith(1)
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

  it('SaleForm order options omit the raw order id', async () => {
    const wrapper = mount(SaleForm, {
      props: { dressId: 1, orders: [ORDER] },
      global: { plugins: [createPinia()] },
    })
    const optionText = wrapper.find('option[value="1"]').text()
    expect(optionText).not.toContain('#1')
    expect(optionText).toContain('2026-08-19')
  })

  it('SaleForm records a split cash/card payment', async () => {
    const wrapper = mount(SaleForm, {
      props: { dressId: 1, orders: [] },
      global: { plugins: [createPinia()] },
    })
    const { api } = await import('../api')

    await wrapper.find('input[type="date"]').setValue('2026-08-19')
    const [priceInput] = wrapper.findAll('input[type="number"]')
    await priceInput.setValue('200')

    await wrapper.findAll('button').find((b) => b.text() === 'Split').trigger('click')
    const cashInput = wrapper.findAll('input[type="number"]').at(-1)
    await cashInput.setValue('120')
    expect(wrapper.text()).toContain('$80.00 card')

    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(api.createSale).toHaveBeenCalledWith(
      expect.objectContaining({ sale_price: 200, cash_amount: 120 }),
    )
  })

  it('Add dress form shows a server-assigned code and does not require typing one', async () => {
    const wrapper = await mountWith(AddDressView, { route: '/dresses/new' })
    expect(wrapper.text()).toContain('WD002')
    expect(wrapper.text()).toContain('assigned automatically')
    // No dress-code text input in the add flow.
    expect(wrapper.find('input[required]').exists()).toBe(false)
  })

  it('Add dress form suggests existing suppliers and accepts a new one', async () => {
    const wrapper = await mountWith(AddDressView, { route: '/dresses/new' })
    const { api } = await import('../api')
    expect(api.suppliers).toHaveBeenCalled()

    const supplierInput = wrapper.findComponent(ComboBox).find('input')
    await supplierInput.trigger('focus')
    // Both known suppliers show up as options.
    expect(wrapper.text()).toContain('Shanghai Factory')
    expect(wrapper.text()).toContain('Beijing Silks')

    await wrapper.findComponent(ComboBox).vm.$emit('update:modelValue', 'Shanghai Factory')
    await flushPromises()
    expect(wrapper.findComponent(ComboBox).props('modelValue')).toBe('Shanghai Factory')

    // A brand-new supplier can still be typed freely.
    await wrapper.findComponent(ComboBox).vm.$emit('update:modelValue', 'A Brand New Supplier')
    expect(wrapper.findComponent(ComboBox).props('modelValue')).toBe('A Brand New Supplier')
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
    expect(store.statusLabel('arrived_shipping_center')).toBe('Shipped from shipping center')
    expect(store.statusIndex('received')).toBe(3)
  })

  it('archiving a dress drops it from the currently loaded list', async () => {
    const store = useInventoryStore()
    store.dresses = [DRESS]
    await store.archiveDress(1)
    expect(store.dresses).toHaveLength(0)
  })
})
