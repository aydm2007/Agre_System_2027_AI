import { Routes, Route } from 'react-router-dom';

import SalesList from '../../components/Sales/SalesList';
import SalesForm from '../../components/Sales/SalesForm';
import CustomersList from '../../components/Sales/CustomersList';
import CustomerForm from '../../components/Sales/CustomerForm';
import SalesInvoicePreview from '../../components/Sales/SalesInvoicePreview';
import InvoicePrint from './InvoicePrint';

export default function SalesPage() {
  return (
    <Routes>
      <Route path="/" element={<SalesList />} />
      <Route path="/new" element={<SalesForm />} />
      <Route path="/customers" element={<CustomersList />} />
      <Route path="/customers/new" element={<CustomerForm />} />
      <Route path="/customers/:id" element={<CustomerForm />} />
      <Route path="/:id" element={<SalesInvoicePreview />} />
      <Route path="/:id/print" element={<InvoicePrint />} />
    </Routes>
  );
}
