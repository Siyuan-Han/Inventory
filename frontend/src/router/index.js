import { createRouter, createWebHistory } from 'vue-router'

import DashboardView from '../views/DashboardView.vue'
import DressListView from '../views/DressListView.vue'
import DressDetailView from '../views/DressDetailView.vue'
import AddDressView from '../views/AddDressView.vue'
import AddSecondhandDressView from '../views/AddSecondhandDressView.vue'

const routes = [
  { path: '/', name: 'dashboard', component: DashboardView },
  {
    path: '/dresses',
    name: 'dresses',
    component: DressListView,
    props: { category: 'new' },
  },
  { path: '/dresses/new', name: 'dress-new', component: AddDressView },
  { path: '/dresses/:id', name: 'dress-detail', component: DressDetailView, props: true },
  { path: '/dresses/:id/edit', name: 'dress-edit', component: AddDressView, props: true },
  {
    path: '/secondhand',
    name: 'secondhand',
    component: DressListView,
    props: { category: 'secondhand' },
  },
  { path: '/secondhand/new', name: 'secondhand-new', component: AddSecondhandDressView },
  { path: '/secondhand/:id', name: 'secondhand-detail', component: DressDetailView, props: true },
  { path: '/secondhand/:id/edit', name: 'secondhand-edit', component: AddDressView, props: true },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

export default createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})
