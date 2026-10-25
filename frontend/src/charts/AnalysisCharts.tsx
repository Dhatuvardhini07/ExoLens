import { Activity, BarChart3, Orbit } from 'lucide-react'
import type { AnalysisResult } from '../api/schema'
import { EmptyState } from '../components/Primitives'

type Data = NonNullable<AnalysisResult['chart_data']>
type ObservationPoint = { time: number; flux: number }
type PeriodogramPoint = { period_days: number; power: number }
type PhasePoint = { phase: number; flux: number }
type ChartKind = 'curve' | 'periodogram' | 'phase'
type ChartPoint = ObservationPoint | PeriodogramPoint | PhasePoint

type Range = { min: number; max: number }
const WIDTH = 1000
const MARGIN = { left: 82, right: 26, top: 24, bottom: 62 }

function xValue(point: ChartPoint, kind: ChartKind): number {
  if (kind === 'curve') return (point as ObservationPoint).time
  if (kind === 'periodogram') return (point as PeriodogramPoint).period_days
  return (point as PhasePoint).phase
}

function yValue(point: ChartPoint, kind: ChartKind): number {
  return kind === 'periodogram'
    ? (point as PeriodogramPoint).power
    : (point as ObservationPoint | PhasePoint).flux
}

function finitePoint(point: ChartPoint, kind: ChartKind): boolean {
  return Number.isFinite(xValue(point, kind)) && Number.isFinite(yValue(point, kind))
}

function range(values: number[]): Range {
  let min = values.reduce((current, value) => Math.min(current, value), Number.POSITIVE_INFINITY)
  let max = values.reduce((current, value) => Math.max(current, value), Number.NEGATIVE_INFINITY)
  if (min === max) {
    const pad = Math.max(Math.abs(min) * 0.02, 1e-6)
    min -= pad
    max += pad
  }
  const pad = (max - min) * 0.04
  return { min: min - pad, max: max + pad }
}

function formatTick(value: number): string {
  return Number(value.toPrecision(6)).toString()
}

function Chart({ title, subtitle, icon: Icon, points, kind, data }: {
  title: string
  subtitle: string
  icon: typeof Activity
  points: ChartPoint[] | undefined
  kind: ChartKind
  data?: Data | null
}) {
  const validPoints = points?.filter(point => finitePoint(point, kind)) ?? []
  const xTitle = kind === 'curve'
    ? `Time${data?.time_system ? ` (${data.time_system})` : ''}`
    : kind === 'periodogram' ? 'Trial period (days)' : 'Orbital phase'
  const yTitle = kind === 'periodogram' ? 'BLS power (search statistic)' : 'Normalized flux'
  const height = kind === 'curve' ? 390 : 330
  const plotWidth = WIDTH - MARGIN.left - MARGIN.right
  const plotHeight = height - MARGIN.top - MARGIN.bottom
  const xRange = validPoints.length ? range(validPoints.map(point => xValue(point, kind))) : null
  const model = kind === 'curve'
    ? data?.model_curve?.filter(point => Number.isFinite(point.time) && Number.isFinite(point.flux)) ?? []
    : []
  const allY = [...validPoints.map(point => yValue(point, kind)), ...model.map(point => point.flux)]
  const yRange = allY.length ? range(allY) : null
  const xScale = (value: number) => MARGIN.left + ((value - xRange!.min) / (xRange!.max - xRange!.min)) * plotWidth
  const yScale = (value: number) => MARGIN.top + (1 - (value - yRange!.min) / (yRange!.max - yRange!.min)) * plotHeight
  const pathFor = (items: Array<{ x: number; y: number }>) => items.map((point, index) => `${index ? 'L' : 'M'}${xScale(point.x).toFixed(2)},${yScale(point.y).toFixed(2)}`).join(' ')
  const unavailable = kind === 'curve' ? data?.unavailable_reasons?.model_curve : undefined
  const arraysPresent = Boolean(points?.length)
  const clipId = `plot-clip-${kind}`

  return <section className={`panel chart-panel ${kind === 'curve' ? 'chart-primary' : ''}`}>
    <div className="panel-heading"><div className="panel-title"><span className="chart-icon"><Icon size={16}/></span><div><h2>{title}</h2><p>{subtitle}</p></div></div><span className="chart-label">{validPoints.length ? `${validPoints.length.toLocaleString()} POINTS` : 'AWAITING ARRAYS'}</span></div>
    {validPoints.length && xRange && yRange ? <div className="plot-frame">
      <svg className="science-plot" viewBox={`0 0 ${WIDTH} ${height}`} role="img" aria-label={`${title}: ${validPoints.length} data points`}>
        <title>{title}</title>
        <defs><clipPath id={clipId}><rect x={MARGIN.left} y={MARGIN.top} width={plotWidth} height={plotHeight}/></clipPath></defs>
        {Array.from({ length: 5 }, (_, index) => {
          const fraction = index / 4
          const x = MARGIN.left + fraction * plotWidth
          const y = MARGIN.top + fraction * plotHeight
          const xTick = xRange.min + fraction * (xRange.max - xRange.min)
          const yTick = yRange.max - fraction * (yRange.max - yRange.min)
          return <g key={index}>
            <line x1={x} x2={x} y1={MARGIN.top} y2={MARGIN.top + plotHeight} stroke="#273345" strokeWidth="1"/>
            <line x1={MARGIN.left} x2={MARGIN.left + plotWidth} y1={y} y2={y} stroke="#273345" strokeWidth="1"/>
            <text x={x} y={height - MARGIN.bottom + 20} fill="#aebbc9" fontSize="12" textAnchor="middle">{formatTick(xTick)}</text>
            <text x={MARGIN.left - 12} y={y + 4} fill="#aebbc9" fontSize="12" textAnchor="end">{formatTick(yTick)}</text>
          </g>
        })}
        <g clipPath={`url(#${clipId})`}>
          {kind === 'periodogram' && <path d={pathFor(validPoints.map(point => ({ x: xValue(point, kind), y: yValue(point, kind) })))} fill="none" stroke="#a998ed" strokeWidth="2" vectorEffect="non-scaling-stroke"/>}
          {validPoints.map((point, index) => <circle key={index} cx={xScale(xValue(point, kind))} cy={yScale(yValue(point, kind))} r={kind === 'periodogram' ? 2 : 2.2} fill={kind === 'curve' ? '#8ed9e4' : '#cebaf7'} opacity=".82"><title>{`${xTitle}: ${formatTick(xValue(point, kind))}; ${yTitle}: ${formatTick(yValue(point, kind))}`}</title></circle>)}
          {kind === 'curve' && model.length > 1 && <path d={pathFor(model.map(point => ({ x: point.time, y: point.flux })))} fill="none" stroke="#f3a76a" strokeWidth="2" vectorEffect="non-scaling-stroke"><title>BLS fitted box model</title></path>}
        </g>
        <line x1={MARGIN.left} x2={MARGIN.left + plotWidth} y1={MARGIN.top + plotHeight} y2={MARGIN.top + plotHeight} stroke="#526178"/>
        <line x1={MARGIN.left} x2={MARGIN.left} y1={MARGIN.top} y2={MARGIN.top + plotHeight} stroke="#526178"/>
        <text x={MARGIN.left + plotWidth / 2} y={height - 12} fill="#b4c0ce" fontSize="13" textAnchor="middle">{xTitle}</text>
        <text x="18" y={MARGIN.top + plotHeight / 2} fill="#b4c0ce" fontSize="13" textAnchor="middle" transform={`rotate(-90 18 ${MARGIN.top + plotHeight / 2})`}>{yTitle}</text>
      </svg>
    </div> : <EmptyState icon={Icon} title={arraysPresent ? 'Chart values are invalid' : 'Chart arrays are not available'} text={arraysPresent ? 'This result has no finite values for this chart, so no graph is drawn.' : unavailable ?? 'This result contains no observed arrays for this chart. No curve or periodogram is synthesized here.'}/>}
    {validPoints.length > 0 && unavailable && kind === 'curve' && <p className="chart-unavailable-note">BLS model not shown: {unavailable}</p>}
  </section>
}

export function AnalysisCharts({ data }: { data?: Data | null }) {
  return <div className="chart-grid"><Chart title="Light curve" subtitle="Observed flux versus time · orange line is the fitted box model" icon={Activity} points={data?.observations} kind="curve" data={data}/><Chart title="BLS periodogram" subtitle="Search power across trial periods · not a probability" icon={BarChart3} points={data?.periodogram} kind="periodogram" data={data}/><div className="chart-wide"><Chart title="Phase-folded light curve" subtitle="Same observations folded at the reported BLS period" icon={Orbit} points={data?.phase_folded} kind="phase" data={data}/></div></div>
}