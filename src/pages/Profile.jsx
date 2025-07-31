// === START OF FILE ===
import React, { useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";
import { doc, getDoc, collection, getDocs } from "firebase/firestore";
import { db } from "../firebase";
import { useNavigate } from "react-router-dom";
import ContactForm from "../components/ContactForm";

const getPerformanceColor = (percentage) => {
  if (percentage >= 80) return "text-green-500";
  if (percentage >= 50) return "text-yellow-400";
  return "text-red-500";
};

const Profile = () => {
  const { currentUser } = useAuth();
  const navigate = useNavigate();
  const [overallStats, setOverallStats] = useState(null);
  const [categoryStats, setCategoryStats] = useState([]);
  const [showPercentages, setShowPercentages] = useState(false);

  useEffect(() => {
    const fetchStats = async () => {
      if (!currentUser) return;

      const overallRef = doc(db, "users", currentUser.uid, "stats", "overall");
      const categoryStatsRef = collection(db, "users", currentUser.uid, "categoryStats");

      const overallSnap = await getDoc(overallRef);
      const categoryStatsSnap = await getDocs(categoryStatsRef);

      if (overallSnap.exists()) {
        setOverallStats(overallSnap.data());
      }

      const catStats = [];
      categoryStatsSnap.forEach((doc) => {
        catStats.push({ id: doc.id, ...doc.data() });
      });

      setCategoryStats(catStats);
    };

    fetchStats();
  }, [currentUser]);

  if (!currentUser || !overallStats) {
    return <div className="text-center mt-10">Loading your profile...</div>;
  }

  const scoreDistribution = overallStats.scoreDistribution || {};

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 text-white">
      <h1 className="text-3xl font-bold mb-6 text-center">Your Profile</h1>

      <div className="bg-zinc-800 p-6 rounded-2xl shadow-lg mb-8">
        <h2 className="text-xl font-semibold mb-4">👤 Account Info</h2>
        <p><span className="font-semibold">Email:</span> {currentUser.email}</p>
      </div>

      <div className="bg-zinc-800 p-6 rounded-2xl shadow-lg mb-8">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold">📊 Overall Stats</h2>
          <button
            onClick={() => setShowPercentages(!showPercentages)}
            className="text-sm text-blue-300 underline"
          >
            {showPercentages ? "Hide %" : "Show %"}
          </button>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 text-center mb-6">
          <Stat label="Quizzes Played" value={overallStats.totalQuizzes} />
          <Stat label="Correct Answers" value={overallStats.correctAnswers} />
          <Stat label="Incorrect Answers" value={overallStats.incorrectAnswers} />
          <Stat
            label="Correct %"
            value={`${parseFloat(overallStats.correctPercentage)?.toFixed(1)}%`}
            hidden={!showPercentages}
            color={getPerformanceColor(parseFloat(overallStats.correctPercentage))}
          />
          <Stat label="Perfect Quizzes" value={overallStats.totalPerfectQuizzes} />
          <Stat
            label="Perfect %"
            value={`${parseFloat(overallStats.perfectQuizPercentage)?.toFixed(1)}%`}
            hidden={!showPercentages}
            color={getPerformanceColor(parseFloat(overallStats.perfectQuizPercentage))}
          />
          <Stat label="Longest Streak ✅" value={overallStats.longestStreakCorrect} />
          <Stat label="Longest Streak ❌" value={overallStats.longestStreakWrong} />
          <Stat label="Yellow Cards" value={overallStats.yellowCards} />
          <Stat label="Red Cards" value={overallStats.redCards} />
          <Stat
            label="Yellow Card Rate"
            value={`${parseFloat(overallStats.yellowCardRate)?.toFixed(1)}%`}
            hidden={!showPercentages}
            color={getPerformanceColor(100 - parseFloat(overallStats.yellowCardRate))}
          />
          <Stat
            label="Red Card Rate"
            value={`${parseFloat(overallStats.redCardRate)?.toFixed(1)}%`}
            hidden={!showPercentages}
            color={getPerformanceColor(100 - parseFloat(overallStats.redCardRate))}
          />
        </div>

        {/* ✅ Score Distribution Section */}
        {Object.keys(scoreDistribution).length > 0 && (
          <div className="mt-6">
            <h3 className="text-lg font-semibold mb-2">📈 Score Distribution</h3>
            <div className="space-y-1 text-sm font-mono">
              {[...Array(11).keys()].map((score) => {
                const count = scoreDistribution[score] || 0;
                const bar = "█".repeat(Math.min(count, 30)); // Limit bar length
                return (
                  <div key={score}>
                    {score}/10: <span className="text-blue-300">{bar}</span> ({count})
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      <div className="bg-zinc-800 p-6 rounded-2xl shadow-lg">
        <h2 className="text-xl font-semibold mb-4">📚 Subcategory Stats</h2>
        <p
          onClick={() => navigate("/collection-book")}
          className="text-sm text-blue-300 underline cursor-pointer hover:text-blue-400 mb-4"
        >
          View Full Collection Book →
        </p>
        <div className="grid sm:grid-cols-2 gap-4">
          {categoryStats.map((cat) => (
            <div
              key={cat.id}
              className="border border-zinc-600 p-4 rounded-xl cursor-pointer hover:bg-zinc-700 transition"
              onClick={() => navigate(`/collection-book/${cat.id}`)}
            >
              <h3 className="font-semibold text-lg mb-2">{cat.id}</h3>
              <p><span className="font-medium">Quizzes:</span> {cat.quizzesPlayed}</p>
              <p><span className="font-medium">Correct:</span> {cat.correctAnswers}</p>
              <p>
                <span className="font-medium">Correct %:</span>{" "}
                <span className={getPerformanceColor(parseFloat(cat.correctPercentage))}>
                  {parseFloat(cat.correctPercentage)?.toFixed(1)}%
                </span>
              </p>
            </div>
          ))}
        </div>
      </div>

      <div className="text-center text-xs text-zinc-400 mt-10 space-x-4">
        <a href="/about" className="hover:underline">About</a>
        <a href="/privacy" className="hover:underline">Privacy Policy</a>
      </div>

      <ContactForm titleColor="text-white" />
    </div>
  );
};

const Stat = ({ label, value, hidden = false, color = "text-white" }) => {
  if (hidden) return null;
  return (
    <div>
      <p className="text-sm text-zinc-400">{label}</p>
      <p className={`text-xl font-bold ${color}`}>{value}</p>
    </div>
  );
};

export default Profile;
// === END OF FILE ===
