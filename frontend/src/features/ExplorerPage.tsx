import { useState, type FormEvent } from 'react'
import { useMutation } from '@tanstack/react-query'
import { ArrowRight, Search, SlidersHorizontal, Telescope } from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'
import { startAnalysis } from '../api/client'
import { EmptyState, ErrorState, PageHeading, StatusPill } from '../components/Primitives'
import { useResults } from './results-context'

export function ExplorerPage() {
  const [tic, setTic] = useState('')
  const [sector, setSector] = useState('')
  const [author, setAuthor] = useState('')
  const [pmin, setPmin] = useState('0.5')
  const [pmax, setPmax] = useState('20')
  const [dmin, setDmin] = useState('0.5')
  const [dmax, setDmax] = useState('6')
  const [searched, setSearched] = useState(false)
  const [formError, setFormError] = useState('')
  const { records } = useResults()
  const navigate = useNavigate()
  const mutation = useMutation({ mutationFn: startAnalysis, onSuccess: job => navigate(`/analysis/${encodeURIComponent(job.analysis_id)}`) })
  const normalizedTic = tic.trim().replace(/^TIC\s*/i, '')
  const matched = searched && normalizedTic ? records.filter(r => r.target.tic_id?.replace(/^TIC\s*/i, '').toLowerCase() === normalizedTic.toLowerCase()) : []

  function validateInput() {
    setFormError('')
    if (!/^\d+$/.test(normalizedTic)) { setFormError('Enter a numeric TIC identifier, for example 39728879.'); return false }
    const [periodLow, periodHigh, durationLow, durationHigh] = [pmin, pmax, dmin, dmax].map(Number)
    if (![periodLow, periodHigh, durationLow, durationHigh].every(Number.isFinite) || periodLow <= 0 || periodHigh <= periodLow) { setFormError('The period maximum must be greater than a positive minimum.'); return false }
    if (durationLow <= 0 || durationHigh <= durationLow || durationHigh >= periodLow * 24) { setFormError('Duration settings must be positive, increasing, and shorter than the minimum period.'); return false }
    if (sector && (!Number.isInteger(Number(sector)) || Number(sector) < 1)) { setFormError('Sector must be a positive whole number.'); return false }
    return true
  }
  function submit(event: FormEvent) {
    event.preventDefault()
    if (!validateInput()) return
    setSearched(true)
    mutation.reset()
  }
  function launch() {
    if (!validateInput()) return
    setSearched(true)
    mutation.mutate({ tic_id: `TIC ${normalizedTic}`, sector: sector ? Number(sector) : undefined, author: author || undefined, period_min_days: Number(pmin), period_max_days: Number(pmax), duration_min_hours: Number(dmin), duration_max_hours: Number(dmax) })
  }

  return <>
    <PageHeading eyebrow="TARGET CATALOG / ANALYSIS" title="Target explorer" description="Look up a TIC target, review browser-local records, or analyze a matching cached TESS product before querying MAST." />
    <div className="explorer-layout"><form className="panel explorer-form" onSubmit={submit}>
      <div className="form-title"><div className="form-icon"><Search size={18} /></div><div><h2>Search a TESS target</h2><p>Enter a target identifier and choose the search window.</p></div></div>
      <div className="form-grid">
        <label className="field field-wide"><span>TIC identifier</span><div className="input-wrap"><Search size={16} /><input value={tic} onChange={event => setTic(event.target.value)} placeholder="e.g. 39728879" inputMode="numeric" /></div><small>Use the numeric TIC ID. The prefix is optional.</small></label>
        <label className="field"><span>Sector <i>optional</i></span><input value={sector} onChange={event => setSector(event.target.value)} placeholder="Any sector" type="number" min="1" step="1" /></label>
        <label className="field"><span>Product author <i>optional</i></span><select value={author} onChange={event => setAuthor(event.target.value)}><option value="">Select if known</option><option>TESS-SPOC</option><option>SPOC</option><option>QLP</option></select></label>
      </div>
      <div className="search-config"><div className="config-head"><SlidersHorizontal size={15} /><span>BOX LEAST SQUARES SEARCH</span><span className="config-note">Settings sent to API</span></div>
        <div className="form-grid config-grid">
          <label className="field"><span>Period minimum <i>days</i></span><input type="number" min="0.01" step="0.1" value={pmin} onChange={event => setPmin(event.target.value)} /></label>
          <label className="field"><span>Period maximum <i>days</i></span><input type="number" min="0.1" step="0.5" value={pmax} onChange={event => setPmax(event.target.value)} /></label>
          <label className="field"><span>Duration minimum <i>hours</i></span><input type="number" min="0.01" step="0.1" value={dmin} onChange={event => setDmin(event.target.value)} /></label>
          <label className="field"><span>Duration maximum <i>hours</i></span><input type="number" min="0.1" step="0.5" value={dmax} onChange={event => setDmax(event.target.value)} /></label>
        </div>
      </div>
      {formError && <div className="form-error" role="alert">{formError}</div>}
      <div className="form-footer"><span>Analysis runs save their search settings; local-history lookup filters by TIC ID.</span><div className="form-actions"><button type="submit" className="button button-secondary"><Search size={15} /> Find saved results</button><button type="button" className="button button-primary" onClick={launch}><Telescope size={16} /> Run analysis <ArrowRight size={14} /></button></div></div>
    </form><aside className="catalog-rail"><div className="catalog-rail-head"><span className="eyebrow">OBSERVATION CATALOG</span><span className="catalog-mark"><Search size={17}/></span></div><h2>Find a signal<br/>worth examining.</h2><p>Search this browser’s imported result history by TIC ID. The API checks the local TESS cache first, then uses Lightkurve to query MAST.</p><div className="catalog-facts"><div><span>LOCAL RECORDS</span><strong>{records.length}</strong></div><div><span>ARCHIVE SEARCH</span><strong>CACHE / MAST</strong></div></div><div className="catalog-source"><span className="source-dot"/><div><strong>TESS archive</strong><small>External archive · opens in new tab</small></div><a href="https://archive.stsci.edu/tess/" target="_blank" rel="noreferrer" aria-label="Open TESS archive"><ArrowRight size={15}/></a></div><div className="catalog-note">A TIC identifier alone does not guarantee that a usable light-curve product is available for the selected sector or author.</div></aside></div>
    {mutation.isError && <div className="panel error-wrap"><ErrorState message={mutation.error.message} retry={launch} /><p className="api-note">The API request failed. Review the message above; no result was fabricated.</p></div>}
    {mutation.isPending && <div className="panel loading-panel"><span className="spinner" /><div><strong>Requesting analysis…</strong><p>Waiting for the ExoLens API to create an analysis job.</p></div></div>}
    {searched && !mutation.isPending && <section className="results-section"><div className="list-heading"><div><span className="eyebrow">MATCHING LOCAL RECORDS</span><h2>{`TIC ${normalizedTic}`}</h2></div><span className="record-count">{matched.length} available</span></div>{matched.length === 0 ? <div className="panel"><EmptyState icon={Telescope} title="No saved result for this target" text="No matching JSON result has been imported into this browser. Starting a new archive analysis requires the API service." /></div> : <div className="record-list">{matched.map(result => <Link className="record-row" key={result.analysis_id} to={`/analysis/${encodeURIComponent(result.analysis_id)}`}><div className="record-icon"><Telescope size={16} /></div><div className="record-main"><strong>{result.target.tic_id}</strong><span>{result.provenance.source_type.replaceAll('_', ' ')}{result.provenance.sector != null ? ` · Sector ${result.provenance.sector}` : ''}</span></div><div className="record-period"><span>{result.event?.period_days?.toFixed(4) ?? '—'} d</span><small>BLS period</small></div><StatusPill status={result.validation.status} /><ArrowRight size={15} /></Link>)}</div>}</section>}
    <div className="explorer-foot"><strong>Not connected yet</strong><span>History is browser-local. The Analysis API is planned but not part of the current backend.</span><Link to="/methods">See integration requirements <ArrowRight size={13} /></Link></div>
  </>
}


