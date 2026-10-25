import { ArrowDown, ArrowRight, ArrowUpRight, Database, Telescope } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useResults } from './results-context'

const workflow = [
  { num: '01', title: 'Choose an observation', text: 'Bring a local light-curve file or select a TESS target when archive retrieval is connected.' },
  { num: '02', title: 'Search for repetition', text: 'Preprocess flux, then search a configured period and duration grid with Box Least Squares.' },
  { num: '03', title: 'Review the evidence', text: 'Inspect measured parameters, data provenance, warnings, and the limits of the result.' },
]

export function HomePage() {
  const { records } = useResults()
  return <div className="overview-page">
    <section className="immersive-hero">
      <img className="hero-image" src="{`${import.meta.env.BASE_URL}nasa-exoplanet-concept.jpg`}" alt="" />
      <div className="hero-shade" />
      <div className="hero-topline"><span><i/> EXOLENS OBSERVATORY</span><span>OPEN SCIENCE · TESS PHOTOMETRY</span></div>
      <div className="hero-content">
        <div className="hero-copyline">LIGHT CURVES / TRANSIT SEARCH</div>
        <h1>Every dip<br/><em>tells a story.</em></h1>
        <p>Trace subtle changes in starlight. Examine periodic signals with a reproducible workflow built to keep the evidence—and its uncertainty—in view.</p>
        <div className="hero-actions"><Link className="button button-primary" to="/explore"><Telescope size={16}/> Explore a target <ArrowRight size={15}/></Link><Link className="hero-secondary" to="/methods">Explore the methods <ArrowUpRight size={15}/></Link></div>
      </div>
      <div className="hero-annotation"><span className="annotation-line"/><div><span>VISUAL REFERENCE</span><strong>GJ 9827d · Artist’s concept</strong><small>NASA / ESA / Leah Hustak (STScI) / Ralf Crawford</small></div></div>
      <div className="hero-bottom"><span>01 — OBSERVE</span><span>PERIODICITY IS A CLUE, NOT A CONFIRMATION</span><ArrowDown size={15}/></div>
    </section>

    <section className="overview-strip" aria-label="Workspace status">
      <div className="strip-intro"><span className="eyebrow">YOUR WORKSPACE</span><strong>Evidence, organized.</strong></div>
      <div className="strip-stat"><span>LOCAL ANALYSES</span><strong>{records.length.toString().padStart(2, '0')}</strong><small>Imported in this browser</small></div>
      <div className="strip-stat"><span>ANALYSIS ENGINE</span><strong className="strip-state"><i/> CLI READY</strong><small>API connection not configured</small></div>
      <Link className="strip-link" to="/dashboard">Open analytics <ArrowRight size={15}/></Link>
    </section>

    <section className="mission-section">
      <div className="section-heading"><div><span className="eyebrow">FROM PHOTONS TO A PERIODIC MODEL</span><h2>A deliberate path through<br/>a noisy signal.</h2></div><p>Each stage records its choices so that a result can be revisited and understood.</p></div>
      <div className="workflow-grid">{workflow.map((step, index) => <article className="workflow-card" key={step.num}><span className="workflow-index">{step.num}<span> / 0{workflow.length}</span></span><div className="workflow-node"><i/>{index < workflow.length - 1 && <b/>}</div><h3>{step.title}</h3><p>{step.text}</p></article>)}</div>
    </section>

    <section className="overview-bottom">
      <div className="principle-panel"><span className="eyebrow">THE EXOLENS PRINCIPLE</span><h2>Search is the beginning<br/>of the investigation.</h2><p>BLS power describes how well a trial box fits the data. It is not a probability, calibrated significance, or proof of a planet.</p><Link className="text-link" to="/methods">Read the scientific limits <ArrowUpRight size={14}/></Link></div>
      <Link to="/explore" className="explore-panel"><span className="explore-symbol"><Database size={19}/></span><span className="eyebrow">START WITH YOUR DATA</span><strong>Open target explorer</strong><small>Search a TIC ID, import an analysis, and inspect what is available.</small><span className="explore-arrow"><ArrowRight size={16}/></span></Link>
    </section>
    <p className="art-credit">Hero artwork: NASA/ESA artist’s concept of GJ 9827d, used as editorial illustration. It is not a result produced by ExoLens. <a href="https://science.nasa.gov/asset/hubble/exoplanet-gj-9827d-artists-concept/" target="_blank" rel="noreferrer">Image source ↗</a></p>
  </div>
}
