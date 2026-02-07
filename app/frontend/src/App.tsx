import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import MainLayout from './layouts/MainLayout';
import ChatPage from './pages/chatPage';
import AddRepo from './pages/addRepo';
import ClonedRepos from './pages/clonedRepos';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<MainLayout />}>
          <Route path="/" element={<Navigate to="/chat" replace />} />
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/add" element={<AddRepo />} />
          <Route path="/repos" element={<ClonedRepos />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;