import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { SignedIn, SignedOut, RedirectToSignIn } from '@clerk/clerk-react';
import MainLayout from './layouts/MainLayout';
import ChatPage from './pages/chatPage';
import AddRepo from './pages/addRepo';
import ClonedRepos from './pages/clonedRepos';
import SignInPage from './features/auth/pages/SignInPage';
import SignUpPage from './features/auth/pages/SignUpPage';
import LandingPage from './pages/LandingPage';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* public route */}
        <Route path="/sign-in/*" element={<SignInPage />} />
        <Route path="/sign-up/*" element={<SignUpPage />} />

        {/* homepage */}
        <Route path="/" element={
          <>
            <SignedIn>
              <Navigate to="/chat" replace />
            </SignedIn>
            <SignedOut>
              <LandingPage />
            </SignedOut>
          </>
        } />

        {/* protected app route */}
        <Route
          element={
            <>
              <SignedIn>
                <MainLayout />
              </SignedIn>
              <SignedOut>
                <RedirectToSignIn />
              </SignedOut>
            </>
          }
        >
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/add" element={<AddRepo />} />
          <Route path="/repos" element={<ClonedRepos />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;