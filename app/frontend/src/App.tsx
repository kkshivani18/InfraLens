import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { SignedIn, SignedOut, RedirectToSignIn } from '@clerk/clerk-react';
import MainLayout from './layouts/MainLayout';
import ChatPage from './pages/chatPage';
import AddRepo from './pages/addRepo';
import ClonedRepos from './pages/clonedRepos';
import SignInPage from './features/auth/pages/SignInPage';
import SignUpPage from './features/auth/pages/SignUpPage'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* public route */}
        <Route path="/sign-in/*" element={<SignInPage />} />
        <Route path="/sign-up/*" element={<SignUpPage />} />

        {/* protected route */}
        <Route element={<MainLayout />}>
          <Route path="/" element={
              <>
                <SignedIn>
                  <Navigate to="/add" replace />
                </SignedIn>
                <SignedOut>
                  <RedirectToSignIn />
                </SignedOut>
              </>
            } 
          />
          <Route path="/chat" element={
              <>
                <SignedIn>
                  <ChatPage />
                </SignedIn>
                <SignedOut>
                  <RedirectToSignIn />
                </SignedOut>
              </>
            } 
          />
          <Route path="/add" element={
              <>
                <SignedIn>
                  <AddRepo />
                </SignedIn>
                <SignedOut>
                  <RedirectToSignIn />
                </SignedOut>
              </>
            } 
          />
          <Route path="/repos" element={
              <>
                <SignedIn>
                  <ClonedRepos />
                </SignedIn>
                <SignedOut>
                  <RedirectToSignIn />
                </SignedOut>
              </>
            } 
          />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;