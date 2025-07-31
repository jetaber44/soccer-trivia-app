// src/App.jsx
import React from "react";
import { BrowserRouter as Router, Routes, Route, useLocation } from "react-router-dom";

import CategorySelection from "./components/CategorySelection";
import SubcategorySelection from "./components/SubcategorySelection";
import DifficultySelection from "./components/DifficultySelection";
import QuizGame from "./components/QuizGame";
import Login from "./pages/Login";
import Profile from "./pages/Profile";
import CollectionDetail from "./pages/CollectionDetail";
import CollectionBookOverview from "./pages/CollectionBookOverview";
import ProtectedRoute from "./components/ProtectedRoute";
import { AuthProvider } from "./context/AuthContext";
import { useAuth } from "./context/AuthContext";
import { signOut } from "firebase/auth";
import { auth } from "./firebase";
import BottomNav from "./components/BottomNav"; // ✅ NEW
import About from "./pages/About";
import PrivacyPolicy from "./pages/PrivacyPolicy";
import NotFound from "./pages/NotFound";


function AppContent() {
  const { currentUser } = useAuth();
  const location = useLocation();

  const hideBottomNavOn = ["/login"];
  const showBottomNav = !hideBottomNavOn.includes(location.pathname);

  return (
    <>
      {currentUser && (
        <div className="flex justify-end p-4">
          <button
            onClick={() => signOut(auth)}
            className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700 text-sm"
          >
            Log Out
          </button>
        </div>
      )}

      <div
        className="relative min-h-screen overflow-x-hidden bg-cover bg-center bg-no-repeat pb-20 w-screen max-w-full"
        style={{ backgroundImage: "url('/Images/background.png')" }}
      >
        <div className="bg-black bg-opacity-20 min-h-screen text-white">
          <div className="px-4 py-6">
            <Routes>
              <Route path="/" element={<CategorySelection />} />
              <Route path="/quiz/:category" element={<SubcategorySelection />} />
              <Route path="/quiz/:category/:subcategory" element={<DifficultySelection />} />
              <Route path="/quiz/:category/:subcategory/:difficulty" element={<QuizGame />} />
              <Route path="/login" element={<Login />} />
              <Route path="/collection-book/:subcategory" element={<CollectionDetail />} />
              <Route path="/collection-book" element={<CollectionBookOverview />} />
              <Route path="/about" element={<About />} />
              <Route path="/privacy" element={<PrivacyPolicy />} />
              <Route
                path="/profile"
                element={
                  <ProtectedRoute>
                    <Profile />
                  </ProtectedRoute>
                }
              />
              <Route path="*" element={<NotFound />} />
            </Routes>
          </div>
        </div>
      </div>

      {/* ✅ Bottom Nav always visible except on login */}
      {showBottomNav && <BottomNav />}
    </>
  );
}

function App() {
  return (
    <AuthProvider>
      <Router>
        <AppContent />
      </Router>
    </AuthProvider>
  );
}

export default App;
