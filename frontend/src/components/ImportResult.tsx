import { useRef, useState } from 'react'
import { FileUp, Check, AlertCircle } from 'lucide-react'
import { parseResult } from '../api/client'
import { useResults } from '../features/results-context'
export function ImportResult() {
  const ref = useRef<HTMLInputElement>(null); const [notice, setNotice] = useState(''); const [isError, setIsError] = useState(false); const { add } = useResults()
  async function handle(file?: File) { if (!file) return; try { const result = parseResult(JSON.parse(await file.text())); add(result); setNotice(`Imported ${result.target.tic_id ?? 'analysis'} · ${result.analysis_id.slice(0, 8)}`); setIsError(false) } catch (error) { setNotice(error instanceof Error ? error.message : 'File does not match output schema 1.0.'); setIsError(true) } }
  return <div className="import-control"><input ref={ref} type="file" accept=".json,application/json" hidden onChange={event => { void handle(event.target.files?.[0]); event.target.value = '' }} /><button className="button button-quiet" onClick={() => ref.current?.click()}><FileUp size={16}/> Import result JSON</button>{notice && <span className={isError ? 'inline-notice error-text' : 'inline-notice'}>{isError ? <AlertCircle size={14}/> : <Check size={14}/>} {notice}</span>}</div>
}

