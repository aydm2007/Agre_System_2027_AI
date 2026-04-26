import Sales from './pages/Sales.jsx'
import { Routes, Route } from 'react-router-dom'

export default function AppMinimal() {
  return (
    <Routes>
      <Route path="/sales" element={<Sales />} />
    </Routes>
  )
}
