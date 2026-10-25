import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import type { AnalysisResult } from '../api/schema'
import { parseResult } from '../api/client'
import { ResultsContext, type ResultsStore } from './results-context'

const KEY = 'exolens.analysis-results.v1'
function readRecords(): AnalysisResult[] {
  try {
    const raw = localStorage.getItem(KEY)
    if (!raw) return []
    const value: unknown = JSON.parse(raw)
    return Array.isArray(value) ? value.map(parseResult) : []
  } catch { return [] }
}

export function ResultsProvider({ children }: { children: ReactNode }) {
  const [records, setRecords] = useState<AnalysisResult[]>(readRecords)
  useEffect(() => {
    try { localStorage.setItem(KEY, JSON.stringify(records)) } catch { /* Keep this session usable when browser storage is full or disabled. */ }
  }, [records])
  const add = useCallback((result: AnalysisResult) => {
    setRecords(current => [result, ...current.filter(item => item.analysis_id !== result.analysis_id)].slice(0, 5))
  }, [])
  const remove = useCallback((id: string) => setRecords(current => current.filter(item => item.analysis_id !== id)), [])
  const store = useMemo<ResultsStore>(() => ({ records, add, remove }), [records, add, remove])
  return <ResultsContext.Provider value={store}>{children}</ResultsContext.Provider>
}
