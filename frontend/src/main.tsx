import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ResultsProvider } from './features/results-store'
import { App } from './app/App'
import './styles/tokens.css'
import './styles/global.css'
import './styles/components.css'
const queryClient = new QueryClient({ defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false, staleTime: 15_000 } } })
createRoot(document.getElementById('root')!).render(<QueryClientProvider client={queryClient}><ResultsProvider><BrowserRouter><App/></BrowserRouter></ResultsProvider></QueryClientProvider>)
