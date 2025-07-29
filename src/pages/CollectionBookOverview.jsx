import React, { useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";
import { collection, getDocs } from "firebase/firestore";
import { db } from "../firebase";
import { useNavigate } from "react-router-dom";
import subcategoryCounts from "../utils/subcategoryCounts";

const CATEGORY_GROUPS = {
  International: ["World Cup", "UEFA", "CONMEBOL", "CONCACAF", "CAF", "AFC", "OFC"],
  Leagues: [
    "Premier League",
    "La Liga",
    "Serie A",
    "Bundesliga",
    "Ligue 1",
    "MLS",
    "Rest of World",
  ],
  "Club Competitions": [
    "UEFA Champions League",
    "UEFA Europa League",
    "UEFA Conference League",
    "Domestic Cups",
    "Club World Cup",
  ],
  Transfers: ["Transfer Fees", "Transfer Facts", "Market Value", "Career Paths"],
  "Time Periods": [
    "2020s",
    "2010s",
    "2000s",
    "1990s",
    "1980s",
    "1970s or Earlier",
  ],
};

const CollectionBookOverview = () => {
  const { currentUser } = useAuth();
  const [seenBySubcategory, setSeenBySubcategory] = useState({});
  const [loading, setLoading] = useState(true);
  const [sortMethod, setSortMethod] = useState("alphabetical");
  const [sortOrder, setSortOrder] = useState("asc");
  const navigate = useNavigate();

  useEffect(() => {
    const fetchSeen = async () => {
      if (!currentUser) return;

      const colRef = collection(db, "users", currentUser.uid, "collectionBook");
      const snapshot = await getDocs(colRef);

      const counts = {};

      snapshot.forEach((docSnap) => {
        const data = docSnap.data();
        const sub = data.subcategory;
        if (!counts[sub]) {
          counts[sub] = 0;
        }
        counts[sub] += 1;
      });

      setSeenBySubcategory(counts);
      setLoading(false);
    };

    fetchSeen();
  }, [currentUser]);

  const getSortedSubcategories = (subList) => {
    return [...subList].sort((a, b) => {
      const seenA = seenBySubcategory[a] || 0;
      const seenB = seenBySubcategory[b] || 0;
      const totalA = subcategoryCounts[a] || 1;
      const totalB = subcategoryCounts[b] || 1;
      const percentA = seenA / totalA;
      const percentB = seenB / totalB;

      let result = 0;
      if (sortMethod === "alphabetical") {
        result = a.localeCompare(b);
      } else if (sortMethod === "progress") {
        result = percentA - percentB;
      }

      return sortOrder === "asc" ? result : -result;
    });
  };

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 text-white">
      <h1 className="text-3xl font-bold mb-6 text-center">📚 Collection Book</h1>

      <div className="mb-6 flex flex-wrap justify-end items-center gap-3">
        <label className="text-sm font-medium">Sort by:</label>
        <select
          value={sortMethod}
          onChange={(e) => setSortMethod(e.target.value)}
          className="bg-zinc-800 border border-zinc-600 text-sm px-2 py-1 rounded-md"
        >
          <option value="alphabetical">Alphabetical</option>
          <option value="progress">Progress %</option>
        </select>
        <select
          value={sortOrder}
          onChange={(e) => setSortOrder(e.target.value)}
          className="bg-zinc-800 border border-zinc-600 text-sm px-2 py-1 rounded-md"
        >
          <option value="asc">⬆ Ascending</option>
          <option value="desc">⬇ Descending</option>
        </select>
      </div>

      {loading ? (
        <p className="text-center">Loading your collection progress...</p>
      ) : (
        <div className="space-y-8">
          {Object.entries(CATEGORY_GROUPS).map(([category, subList]) => {
            const sortedSubs = getSortedSubcategories(subList);
            return (
              <div key={category}>
                <h2 className="text-xl font-semibold mb-3 border-b border-zinc-600 pb-1">
                  {category}
                </h2>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {sortedSubs.map((sub) => {
                    const seen = seenBySubcategory[sub] || 0;
                    const total = subcategoryCounts[sub] || 1;
                    const percent = Math.round((seen / total) * 100);

                    return (
                      <div
                        key={sub}
                        onClick={() => navigate(`/collection-book/${sub}`)}
                        className="bg-zinc-800 p-4 rounded-lg cursor-pointer hover:bg-zinc-700 transition border border-zinc-600"
                      >
                        <div className="flex justify-between mb-1 text-sm font-semibold">
                          <span>{sub}</span>
                          <span>
                            {seen} / {total} ({percent}%)
                          </span>
                        </div>
                        <div className="w-full bg-zinc-700 rounded h-2 overflow-hidden">
                          <div
                            className="bg-green-500 h-full"
                            style={{ width: `${percent}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default CollectionBookOverview;
