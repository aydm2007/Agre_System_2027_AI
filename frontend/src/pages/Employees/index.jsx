import { Routes, Route } from 'react-router-dom'
import EmployeeList from './EmployeeList'

export default function EmployeesPage() {
    return (
        <Routes>
            <Route path="/" element={<EmployeeList />} />
        </Routes>
    )
}
