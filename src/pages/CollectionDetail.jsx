import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import {
  collection,
  doc,
  getDoc,
  getDocs,
  query,
  where,
} from "firebase/firestore";
import { db } from "../firebase";
import subcategoryCounts from "../utils/subcategoryCounts"; // ✅ Add this import

const CollectionDetail = () => {
  const { subcategory } = useParams();
  const { currentUser } = useAuth();
  const [questionStats, setQuestionStats] = useState([]);
  const [loading, setLoading] = useState(true);
  const [sortMethod, setSortMethod] = useState("lastSeen");
  const [sortOrder, setSortOrder] = useState("desc");
  const [viewMode, setViewMode] = useState("grid");

  useEffect(() => {
    const fetchQuestionStats = async () => {
      if (!currentUser) return;
      setLoading(true);

      try {
        const colRef = collection(db, "users", currentUser.uid, "collectionBook");
        const q = query(colRef, where("subcategory", "==", subcategory));
        const snapshot = await getDocs(q);

        const data = [];

        for (const docSnap of snapshot.docs) {
          const userStats = docSnap.data();
          const questionId = docSnap.id;

          const questionRef = doc(db, "triviaQuestions", questionId);
          const questionSnap = await getDoc(questionRef);

          if (questionSnap.exists()) {
            const { question } = questionSnap.data();
            const correct = userStats.correctCount || 0;
            const incorrect = userStats.incorrectCount || 0;
            const total = correct + incorrect;
            const correctPercent =
              total > 0 ? ((correct / total) * 100).toFixed(1) : "0.0";

            data.push({
              questionId,
              question,
              correct,
              incorrect,
              total,
              correctPercent: parseFloat(correctPercent),
              lastSeen: userStats.lastSeen?.toDate() || null,
            });
          }
        }

        setQuestionStats(data);
      } catch (err) {
        console.error("Error fetching collection detail:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchQuestionStats();
  }, [subcategory, currentUser]);

  const sortedStats = [...questionStats].sort((a, b) => {
    let result = 0;
    switch (sortMethod) {
      case "correctPercent":
        result = a.correctPercent - b.correctPercent;
        break;
      case "total":
        result = a.total - b.total;
        break;
      case "lastSeen":
        result = (a.lastSeen?.getTime() || 0) - (b.lastSeen?.getTime() || 0);
        break;
      default:
        break;
    }
    return sortOrder === "asc" ? result : -result;
  });

  // ✅ Progress bar data
  const totalInSubcategory = subcategoryCounts[subcategory] || 1;
  const seenCount = questionStats.length;
  const progressPercent = Math.round((seenCount / totalInSubcategory) * 100);

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 text-white">
      <h1 className="text-3xl font-bold mb-4 text-center">
        📘 {subcategory} – Collection
      </h1>

      {/* ✅ Progress Bar */}
      <div className="max-w-md mx-auto mb-6">
        <div className="flex justify-between text-sm text-zinc-300 mb-1">
          <span>{seenCount} / {totalInSubcategory} questions seen</span>
          <span>{progressPercent}%</span>
        </div>
        <div className="w-full bg-zinc-700 h-2 rounded overflow-hidden">
          <div
            className="bg-green-500 h-full"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
      </div>

      {/* 🔁 Controls */}
      <div className="mb-6 flex flex-wrap justify-between items-center gap-4">
        <div className="flex items-center gap-2">
          <label className="text-sm font-medium">Sort by:</label>
          <select
            value={sortMethod}
            onChange={(e) => setSortMethod(e.target.value)}
            className="bg-zinc-800 border border-zinc-600 text-sm px-2 py-1 rounded-md"
          >
            <option value="lastSeen">Last Seen</option>
            <option value="correctPercent">Correct %</option>
            <option value="total">Times Seen</option>
          </select>

          <select
            value={sortOrder}
            onChange={(e) => setSortOrder(e.target.value)}
            className="bg-zinc-800 border border-zinc-600 text-sm px-2 py-1 rounded-md"
          >
            <option value="desc">⬇ Descending</option>
            <option value="asc">⬆ Ascending</option>
          </select>
        </div>

        <button
          onClick={() => setViewMode(viewMode === "grid" ? "list" : "grid")}
          className="text-sm px-3 py-1 border border-zinc-600 rounded-md bg-zinc-800 hover:bg-zinc-700"
        >
          {viewMode === "grid" ? "🔃 Switch to List View" : "🔳 Switch to Grid View"}
        </button>
      </div>

      {loading ? (
        <p className="text-center">Loading your questions...</p>
      ) : sortedStats.length === 0 ? (
        <p className="text-center">No questions tracked yet for this subcategory.</p>
      ) : viewMode === "grid" ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {sortedStats.map((q) => (
            <div
              key={q.questionId}
              className="bg-zinc-800 p-4 rounded-xl border border-zinc-700 shadow-sm"
            >
              <p className="text-xs text-zinc-400 mb-1">
                Last Seen: {q.lastSeen ? q.lastSeen.toLocaleDateString() : "N/A"}
              </p>
              <p className="text-sm font-medium mb-2">{q.question}</p>
              <p className="text-xs text-zinc-300">
                ✅ {q.correct} | ❌ {q.incorrect} | 🎯{" "}
                <span className="font-semibold">{q.correctPercent}%</span> accuracy
              </p>
            </div>
          ))}
        </div>
      ) : (
        <div className="space-y-3">
          {sortedStats.map((q) => (
            <div
              key={q.questionId}
              className="bg-zinc-800 p-4 rounded-xl border border-zinc-700 shadow-sm"
            >
              <div className="flex justify-between text-xs text-zinc-400 mb-1">
                <span>
                  Last Seen: {q.lastSeen ? q.lastSeen.toLocaleDateString() : "N/A"}
                </span>
                <span>Seen: {q.total}x</span>
              </div>
              <p className="text-sm font-medium mb-2">{q.question}</p>
              <p className="text-xs text-zinc-300">
                ✅ {q.correct} | ❌ {q.incorrect} | 🎯{" "}
                <span className="font-semibold">{q.correctPercent}%</span> accuracy
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default CollectionDetail;
