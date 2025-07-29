import React from "react";
import { useNavigate } from "react-router-dom";
import { CATEGORIES } from "../utils/constants";

const CategorySelection = () => {
  const navigate = useNavigate();

  const handleCategoryClick = (category) => {
    navigate(`/quiz/${category}`);
  };

  return (
    <div className="text-center px-4 py-6">
      {/* App Title - centered at top */}
      <h1 className="text-4xl font-extrabold mb-2">Quizlazo</h1>

      {/* Subtitle */}
      <h2 className="text-2xl font-semibold mb-6">Choose a Category</h2>

      {/* Category Buttons in centered grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-md mx-auto">
        {CATEGORIES.map((category) => (
          <button
            key={category}
            onClick={() => handleCategoryClick(category)}
            className="bg-white text-black p-4 rounded-xl shadow hover:shadow-lg transition"
          >
            {category}
          </button>
        ))}
      </div>
    </div>
  );
};

export default CategorySelection;
