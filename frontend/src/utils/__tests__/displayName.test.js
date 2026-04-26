import { describe, expect, it } from 'vitest'

import {
  resolveDisplayName,
  resolvePermissionDisplayName,
  resolveSecondaryIdentity,
} from '../displayName'

describe('displayName helpers', () => {
  it('prefers Arabic-oriented full names over usernames', () => {
    const user = {
      full_name_ar: 'أحمد المشرف',
      full_name: 'Ahmed Supervisor',
      username: 'ahmad',
      email: 'ahmad@example.com',
    }

    expect(resolveDisplayName(user)).toBe('أحمد المشرف')
    expect(resolveSecondaryIdentity(user)).toBe('ahmad@example.com')
  })

  it('falls back to available composite names when Arabic name is absent', () => {
    const user = {
      first_name: 'فاطمة',
      last_name: 'المحاسبة',
      username: 'fatima_finance',
      email: 'fatima@example.com',
    }

    expect(resolveDisplayName(user)).toBe('فاطمة المحاسبة')
    expect(resolveSecondaryIdentity(user)).toBe('fatima@example.com')
  })

  it('resolves permission labels from Arabic fields first', () => {
    const permission = {
      name_arabic: 'عرض التقارير',
      name: 'Can view reports',
      codename: 'view_reports',
    }

    expect(resolvePermissionDisplayName(permission)).toBe('عرض التقارير')
  })
})
