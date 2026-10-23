import { Route, Routes } from 'react-router-dom'
import ProtectedRoute, { GuestOnlyRoute } from './components/ProtectedRoute'
import { useAuth } from './context/AuthContext'
import AppLayout from './layouts/AppLayout'
import PublicLayout from './layouts/PublicLayout'
import { LoginPage, RegisterPage } from './pages/Auth'
import { CropDetail, CropsList } from './pages/Crops'
import Dashboard from './pages/Dashboard'
import Explorer from './pages/Explorer'
import { About, Contact, NotFound, Privacy, Terms } from './pages/Info'
import Landing from './pages/Landing'
import Predict from './pages/Predict'
import Profile from './pages/Profile'

/** Public data pages use the app shell for signed-in users and the website shell otherwise. */
function AdaptiveLayout() {
  const { isAuthenticated } = useAuth()
  return isAuthenticated ? <AppLayout /> : <PublicLayout />
}

function PublicPage({ children }) {
  return <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6">{children}</div>
}

function MaybeWrapped({ children }) {
  const { isAuthenticated } = useAuth()
  return isAuthenticated ? children : <PublicPage>{children}</PublicPage>
}

export default function App() {
  return (
    <Routes>
      <Route element={<PublicLayout />}>
        <Route index element={<Landing />} />
        <Route path="about" element={<About />} />
        <Route path="contact" element={<Contact />} />
        <Route path="privacy" element={<Privacy />} />
        <Route path="terms" element={<Terms />} />
      </Route>

      <Route element={<GuestOnlyRoute />}>
        <Route path="login" element={<LoginPage />} />
        <Route path="register" element={<RegisterPage />} />
      </Route>

      <Route element={<AdaptiveLayout />}>
        <Route path="markets" element={<MaybeWrapped><Explorer /></MaybeWrapped>} />
        <Route path="crops" element={<MaybeWrapped><CropsList /></MaybeWrapped>} />
        <Route path="crops/:id" element={<MaybeWrapped><CropDetail /></MaybeWrapped>} />
      </Route>

      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="predict" element={<Predict />} />
          <Route path="profile" element={<Profile />} />
        </Route>
      </Route>

      <Route element={<PublicLayout />}>
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  )
}
