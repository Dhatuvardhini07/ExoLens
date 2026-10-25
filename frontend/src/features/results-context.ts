import { createContext, useContext } from 'react'
import type { AnalysisResult } from '../api/schema'

export type ResultsStore = {
  records: AnalysisResult[]
  add: (result: AnalysisResult) => void
  remove: (id: string) => void
}

export const ResultsContext = createContext<ResultsStore | null>(null)

export function useResults() {
  const value = useContext(ResultsContext)
  if (!value) throw new Error('useResults must be used within ResultsProvider')
  return value
}
