import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import type { AnalysisResult } from '../src/api/schema'
import { AnalysisCharts } from '../src/charts/AnalysisCharts'

afterEach(cleanup)

const chartData: NonNullable<AnalysisResult['chart_data']> = {
  time_system: 'BTJD',
  observations: [{ time: 1468.25, flux: 1.0002 }, { time: 1468.27, flux: 0.9998 }],
  periodogram: [{ period_days: 0.5, power: 2.1 }, { period_days: 8.005, power: 12.63 }],
  phase_folded: [{ phase: -0.25, flux: 1.0002 }, { phase: 0, flux: 0.9998 }],
  model_curve: [{ time: 1468.25, flux: 1 }, { time: 1468.27, flux: 0.9993 }],
  unavailable_reasons: {},
}

describe('AnalysisCharts', () => {
  it('renders the observed time/flux points and returned BLS model in the light curve', () => {
    const { container } = render(<AnalysisCharts data={chartData}/>);
    const plots = container.querySelectorAll('svg.science-plot')
    const lightCurve = plots[0]
    expect(lightCurve.getAttribute('aria-label')).toBe('Light curve: 2 data points')
    const points = lightCurve.querySelectorAll('circle')
    expect(points).toHaveLength(2)
    expect(points[0].querySelector('title')?.textContent).toContain('1468.25')
    expect(points[0].querySelector('title')?.textContent).toContain('1.0002')
    expect(lightCurve.querySelector('path[stroke="#f3a76a"]')).toBeTruthy()
    expect(screen.getByText('Time (BTJD)')).toBeTruthy()
  })

  it('plots the actual trial-period and BLS-power pairs, labeled as a search statistic', () => {
    const { container } = render(<AnalysisCharts data={chartData}/>);
    const periodogram = container.querySelectorAll('svg.science-plot')[1]
    expect(periodogram.querySelector('path[stroke="#a998ed"]')?.getAttribute('d')).toMatch(/^M/)
    const points = periodogram.querySelectorAll('circle')
    expect(points).toHaveLength(2)
    expect(points[1].querySelector('title')?.textContent).toContain('8.005')
    expect(points[1].querySelector('title')?.textContent).toContain('12.63')
    expect(screen.getByText('BLS power (search statistic)')).toBeTruthy()
    expect(screen.getByText(/not a probability/)).toBeTruthy()
  })

  it('keeps the working phase-folded view and maps phase to normalized flux', () => {
    const { container } = render(<AnalysisCharts data={chartData}/>);
    const phasePlot = container.querySelectorAll('svg.science-plot')[2]
    expect(phasePlot.getAttribute('aria-label')).toBe('Phase-folded light curve: 2 data points')
    const point = phasePlot.querySelector('circle')
    expect(point?.querySelector('title')?.textContent).toContain('-0.25')
    expect(point?.querySelector('title')?.textContent).toContain('1.0002')
  })

  it('shows an honest unavailable state for missing arrays', () => {
    const { container } = render(<AnalysisCharts data={{ observations: [], periodogram: [], phase_folded: [] }}/>);
    expect(container.querySelectorAll('svg.science-plot')).toHaveLength(0)
    expect(screen.getAllByText('Chart arrays are not available')).toHaveLength(3)
  })

  it('filters invalid values without fabricating chart points', () => {
    const invalid = {
      ...chartData,
      observations: [{ time: Number.NaN, flux: 1 }],
      periodogram: [{ period_days: 8, power: Number.POSITIVE_INFINITY }],
      phase_folded: [{ phase: 0, flux: 1 }],
      model_curve: null,
    } as unknown as NonNullable<AnalysisResult['chart_data']>
    const { container } = render(<AnalysisCharts data={invalid}/>);
    expect(container.querySelectorAll('svg.science-plot')).toHaveLength(1)
    expect(screen.getAllByText('Chart values are invalid')).toHaveLength(2)
    expect(screen.getByText('1 POINTS')).toBeTruthy()
  })
})