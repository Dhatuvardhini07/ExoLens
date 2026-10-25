import { Navigate, Route, Routes } from 'react-router-dom'
import { AppShell } from '../components/AppShell'
import { AnalysisPage } from '../features/AnalysisPage'
import { DashboardPage } from '../features/DashboardPage'
import { ExplorerPage } from '../features/ExplorerPage'
import { HomePage } from '../features/HomePage'
import { MethodsPage } from '../features/MethodsPage'
export function App(){return <Routes><Route element={<AppShell/>}><Route index element={<HomePage/>}/><Route path="dashboard" element={<DashboardPage/>}/><Route path="explore" element={<ExplorerPage/>}/><Route path="analysis/:analysisId" element={<AnalysisPage/>}/><Route path="methods" element={<MethodsPage/>}/><Route path="*" element={<Navigate to="/" replace/>}/></Route></Routes>}
