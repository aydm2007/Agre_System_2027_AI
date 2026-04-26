import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'

import DailyLogHarvestLaunch from '../DailyLogHarvestLaunch.jsx'

function DailyLogProbe() {
  const location = useLocation()
  return (
    <div>
      <div data-testid="daily-log-path">{location.pathname}</div>
      <div data-testid="daily-log-task">
        {location.state?.launchpadData?.requestedTaskName || ''}
      </div>
      <div data-testid="daily-log-surface">
        {location.state?.launchpadData?.launchSurface || ''}
      </div>
    </div>
  )
}

describe('DailyLogHarvestLaunch', () => {
  it('redirects to DailyLog with harvest launchpad context', async () => {
    render(
      <MemoryRouter initialEntries={['/daily-log/harvest']}>
        <Routes>
          <Route path="/daily-log/harvest" element={<DailyLogHarvestLaunch />} />
          <Route path="/daily-log" element={<DailyLogProbe />} />
        </Routes>
      </MemoryRouter>,
    )

    expect((await screen.findByTestId('daily-log-path')).textContent).toContain('/daily-log')
    expect(screen.getByTestId('daily-log-task').textContent).toContain('حصاد')
    expect(screen.getByTestId('daily-log-surface').textContent).toContain('harvest-entry')
  })
})
