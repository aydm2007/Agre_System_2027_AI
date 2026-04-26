import { Navigate } from 'react-router-dom'

export default function DailyLogHarvestLaunch() {
  return (
    <Navigate
      to="/daily-log"
      replace
      state={{
        launchpadData: {
          requestedTaskName: 'حصاد',
          launchSurface: 'harvest-entry',
        },
      }}
    />
  )
}
