import { useEffect, lazy, Suspense } from 'react'
import { Routes, Route } from 'react-router-dom'
import { useAuthStore } from './store/authStore'
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'
import Toast from './components/Toast'
import NetworkStatus from './components/NetworkStatus'
import LoadingIndicator from './components/LoadingIndicator'
import Login from './pages/Login'

// Route-level code splitting: each page loads on demand, so Chart.js and
// secondary views stay out of the initial bundle.
const Dashboard = lazy(() => import('./pages/Dashboard'))
const CustomerList = lazy(() => import('./pages/customers/CustomerList'))
const CustomerForm = lazy(() => import('./pages/customers/CustomerForm'))
const CustomerDetail = lazy(() => import('./pages/customers/CustomerDetail'))
const OrderList = lazy(() => import('./pages/orders/OrderList'))
const OrderForm = lazy(() => import('./pages/orders/OrderForm'))
const OrderDetail = lazy(() => import('./pages/orders/OrderDetail'))
const ContractList = lazy(() => import('./pages/contracts/ContractList'))
const ContractForm = lazy(() => import('./pages/contracts/ContractForm'))
const ContractDetail = lazy(() => import('./pages/contracts/ContractDetail'))
const InvoiceList = lazy(() => import('./pages/invoices/InvoiceList'))
const InvoiceForm = lazy(() => import('./pages/invoices/InvoiceForm'))
const InvoiceDetail = lazy(() => import('./pages/invoices/InvoiceDetail'))
const LeadList = lazy(() => import('./pages/leads/LeadList'))
const LeadForm = lazy(() => import('./pages/leads/LeadForm'))
const Tasks = lazy(() => import('./pages/Tasks'))
const Calendar = lazy(() => import('./pages/Calendar'))
const TimeTracking = lazy(() => import('./pages/TimeTracking'))
const ExpenseList = lazy(() => import('./pages/expenses/ExpenseList'))
const ExpenseForm = lazy(() => import('./pages/expenses/ExpenseForm'))
const Euer = lazy(() => import('./pages/Euer'))
const Kanban = lazy(() => import('./pages/Kanban'))
const Analytics = lazy(() => import('./pages/Analytics'))
const Documents = lazy(() => import('./pages/Documents'))
const Compliance = lazy(() => import('./pages/Compliance'))
const Users = lazy(() => import('./pages/Users'))
const Settings = lazy(() => import('./pages/Settings'))
const RainmakerToday = lazy(() => import('./pages/rainmaker/Today'))
const RainmakerPipeline = lazy(() => import('./pages/rainmaker/Pipeline'))
const RainmakerLeadForm = lazy(() => import('./pages/rainmaker/LeadForm'))
const RainmakerLeadDetail = lazy(() => import('./pages/rainmaker/LeadDetail'))
const RainmakerStatistics = lazy(() => import('./pages/rainmaker/Statistics'))
const RainmakerSettingsPage = lazy(() => import('./pages/rainmaker/Settings'))

export default function App() {
  const initialize = useAuthStore((s) => s.initialize)

  useEffect(() => {
    initialize()
  }, [initialize])

  return (
    <>
      <Toast />
      <NetworkStatus />
      <Suspense fallback={<LoadingIndicator />}>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          element={
            <ProtectedRoute>
              <Layout />
            </ProtectedRoute>
          }
        >
          <Route path="/" element={<Dashboard />} />
          <Route path="/rainmaker" element={<RainmakerToday />} />
          <Route path="/rainmaker/pipeline" element={<RainmakerPipeline />} />
          <Route path="/rainmaker/statistik" element={<RainmakerStatistics />} />
          <Route path="/rainmaker/einstellungen" element={<RainmakerSettingsPage />} />
          <Route path="/rainmaker/leads/neu" element={<RainmakerLeadForm />} />
          <Route path="/rainmaker/leads/:id" element={<RainmakerLeadDetail />} />
          <Route path="/rainmaker/leads/:id/bearbeiten" element={<RainmakerLeadForm />} />
          <Route path="/aufgaben" element={<Tasks />} />
          <Route path="/kalender" element={<Calendar />} />
          <Route path="/zeiterfassung" element={<TimeTracking />} />
          <Route path="/kunden" element={<CustomerList />} />
          <Route path="/kunden/neu" element={<CustomerForm />} />
          <Route path="/kunden/:id" element={<CustomerDetail />} />
          <Route path="/kunden/:id/bearbeiten" element={<CustomerForm />} />
          <Route path="/auftraege" element={<OrderList />} />
          <Route path="/auftraege/neu" element={<OrderForm />} />
          <Route path="/auftraege/:id" element={<OrderDetail />} />
          <Route path="/auftraege/:id/bearbeiten" element={<OrderForm />} />
          <Route path="/vertraege" element={<ContractList />} />
          <Route path="/vertraege/neu" element={<ContractForm />} />
          <Route path="/vertraege/:id" element={<ContractDetail />} />
          <Route path="/vertraege/:id/bearbeiten" element={<ContractForm />} />
          <Route path="/rechnungen" element={<InvoiceList />} />
          <Route path="/rechnungen/neu" element={<InvoiceForm />} />
          <Route path="/rechnungen/:id" element={<InvoiceDetail />} />
          <Route path="/rechnungen/:id/bearbeiten" element={<InvoiceForm />} />
          <Route path="/vorgemerkt" element={<LeadList />} />
          <Route path="/vorgemerkt/neu" element={<LeadForm />} />
          <Route path="/vorgemerkt/:id/bearbeiten" element={<LeadForm />} />
          <Route path="/ausgaben" element={<ExpenseList />} />
          <Route path="/ausgaben/neu" element={<ExpenseForm />} />
          <Route path="/ausgaben/:id/bearbeiten" element={<ExpenseForm />} />
          <Route path="/euer" element={<Euer />} />
          <Route path="/kanban" element={<Kanban />} />
          <Route path="/analyse" element={<Analytics />} />
          <Route path="/dokumente" element={<Documents />} />
          <Route path="/rechtsdokumente" element={<Compliance />} />
          <Route path="/benutzer" element={<Users />} />
          <Route path="/einstellungen" element={<Settings />} />
        </Route>
      </Routes>
      </Suspense>
    </>
  )
}
