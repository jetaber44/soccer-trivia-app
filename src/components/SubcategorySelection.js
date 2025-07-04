import React from "react";
import { useNavigate, useParams } from "react-router-dom";
import { SUBCATEGORIES } from "../utils/constants";

const SubcategorySelection = () => {
  const navigate = useNavigate();
  const { category } = useParams();

  const handleSubcategoryClick = (subcategory) => {
    navigate(`/quiz/${category}/${subcategory}`);
  };

  const subcategories = SUBCATEGORIES[category] || [];

  return (
    <div className="min-h-screen px-4 py-6 text-center">
      {/* Page Title */}
      <h1 className="text-4xl font-extrabold mb-2">⚽ Soccer Trivia</h1>

      {/* Subtitle */}
      <h2 className="text-2xl font-semibold mb-6">Choose a Subcategory</h2>

      {/* Subcategory Buttons */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-md mx-auto">
        {subcategories.map((subcategory) => (
          <button
            key={subcategory}
            onClick={() => handleSubcategoryClick(subcategory)}
            className="bg-white text-black p-4 rounded-xl shadow hover:shadow-lg transition"
          >
            {subcategory}
          </button>
        ))}
      </div>
    </div>
  );
};

export default SubcategorySelection;
