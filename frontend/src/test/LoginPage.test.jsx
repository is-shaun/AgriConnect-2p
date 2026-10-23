import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('../services/api', () => ({
  endpoints: { me: vi.fn(), login: vi.fn(), logout: vi.fn(), register: vi.fn() },
  setUnauthorizedHandler: vi.fn(),
}))

import { AuthProvider } from '../context/AuthContext'
import { LoginPage } from '../pages/Auth'
import { endpoints } from '../services/api'

function renderLogin() {
  return render(
    <MemoryRouter initialEntries={['/login']}>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/dashboard" element={<p>Dashboard page</p>} />
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  )
}

describe('LoginPage', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    endpoints.me.mockRejectedValue({ status: 401 })
  })

  it('shows validation errors without calling the API', async () => {
    renderLogin()
    await userEvent.click(screen.getByRole('button', { name: 'Log in' }))
    expect(await screen.findByText('Enter your email address.')).toBeInTheDocument()
    expect(screen.getByText('Enter your password.')).toBeInTheDocument()
    expect(endpoints.login).not.toHaveBeenCalled()
  })

  it('shows the server message for wrong credentials', async () => {
    endpoints.login.mockRejectedValue({ code: 'invalid_credentials', message: 'Invalid email or password.' })
    renderLogin()
    await userEvent.type(screen.getByLabelText('Email'), 'farmer@example.com')
    await userEvent.type(screen.getByLabelText('Password'), 'wrongpass1')
    await userEvent.click(screen.getByRole('button', { name: 'Log in' }))
    expect(await screen.findByText('Invalid email or password.')).toBeInTheDocument()
  })

  it('logs in and goes to the dashboard', async () => {
    endpoints.login.mockResolvedValue({ user: { id: 1, name: 'Asha', email: 'farmer@example.com' } })
    renderLogin()
    await userEvent.type(screen.getByLabelText('Email'), 'farmer@example.com')
    await userEvent.type(screen.getByLabelText('Password'), 'harvest2026')
    await userEvent.click(screen.getByRole('button', { name: 'Log in' }))
    expect(await screen.findByText('Dashboard page')).toBeInTheDocument()
    expect(endpoints.login).toHaveBeenCalledWith({ email: 'farmer@example.com', password: 'harvest2026' })
  })
})
