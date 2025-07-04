import React from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";

import CategorySelection from "./components/CategorySelection";
import SubcategorySelection from "./components/SubcategorySelection";
import DifficultySelection from "./components/DifficultySelection";
import QuizGame from "./components/QuizGame";

function App() {
  return (
    <Router>
      {/* Background wrapper */}
      <div
        className="min-h-screen bg-cover bg-center bg-no-repeat"
        style={{ backgroundImage: "url('/images/background.png')" }}
      >
        {/* Optional overlay for contrast */}
        <div className="bg-black bg-opacity-20 min-h-screen text-white">
          <div className="px-4 py-6">
            <Routes>
              <Route path="/" element={<CategorySelection />} />
              <Route path="/quiz/:category" element={<SubcategorySelection />} />
              <Route path="/quiz/:category/:subcategory" element={<DifficultySelection />} />
              <Route path="/quiz/:category/:subcategory/:difficulty" element={<QuizGame />} />
            </Routes>
          </div>
        </div>
      </div>
    </Router>
  );
}

export default App;
