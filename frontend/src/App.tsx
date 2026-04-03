import { useEffect } from 'react'
import { Routes, Route } from 'react-router-dom'
import { useAuthStore } from './store/authStore'
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'
import Toast from './components/Toast'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import CustomerList from './pages/customers/CustomerList'
import CustomerForm from './pages/customers/CustomerForm'
import CustomerDetail from './pages/customers/CustomerDetail'
import OrderList from './pages/orders/OrderList'
import OrderForm from './pages/orders/OrderForm'
import OrderDetail from './pages/orders/OrderDetail'
import ContractList from './pages/contracts/ContractList'
import ContractForm from './pages/contracts/ContractForm'
import ContractDetail from './pages/contracts/ContractDetail'
import InvoiceList from './pages/invoices/InvoiceList'
import InvoiceForm from './pages/invoices/InvoiceForm'
import InvoiceDetail from './pages/invoices/InvoiceDetail'
import LeadList from './pages/leads/LeadList'
import LeadForm from './pages/leads/LeadForm'
import Tasks from './pages/Tasks'
import Calendar from './pages/Calendar'
import TimeTracking from './pages/TimeTracking'
import ExpenseList from './pages/expenses/ExpenseList'
import ExpenseForm from './pages/expenses/ExpenseForm'
import Euer from './pages/Euer'
import Kanban from './pages/Kanban'
import Analytics from './pages/Analytics'
import Documents from './pages/Documents'
import Settings from './pages/Settings'

export default function App() {
  const initialize = useAuthStore((s) => s.initialize)

  useEffect(() => {
    initialize()
  }, [initialize])

  return (
    <>
      <Toast />
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
          <Route path="/einstellungen" element={<Settings />} />
        </Route>
      </Routes>
    </>
  )
}
