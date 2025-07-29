import React from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { Home, User, BookOpenCheck, LogIn } from "lucide-react";

const BottomNav = () => {
  const { currentUser } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  // ✅ Routes where BottomNav should be hidden
  const hiddenPaths = [
    "/login",
    "/signup",
    "/quiz/",
  ];

  const hideBottomNav = hiddenPaths.some((path) =>
    location.pathname.startsWith(path)
  );

  if (hideBottomNav) return null;

  const tabs = currentUser
    ? [
        { name: "Play", path: "/", icon: Home },
        { name: "Collection", path: "/collection-book", icon: BookOpenCheck },
        { name: "Profile", path: "/profile", icon: User },
      ]
    : [
        { name: "Play", path: "/", icon: Home },
        { name: "Login", path: "/login", icon: LogIn },
      ];

  const isActive = (path) => location.pathname === path;

  return (
    <nav className="fixed bottom-0 w-full bg-zinc-900 border-t border-zinc-700 flex justify-around items-center py-2 z-50 shadow-inner">
      {tabs.map((tab) => {
        const Icon = tab.icon;
        return (
          <button
            key={tab.name}
            onClick={() => navigate(tab.path)}
            className={`flex flex-col items-center gap-1 px-2 py-1 text-xs font-medium transition-colors duration-150 ${
              isActive(tab.path) ? "text-green-400" : "text-zinc-400"
            }`}
          >
            <Icon size={22} />
            <span>{tab.name}</span>
          </button>
        );
      })}
    </nav>
  );
};

export default BottomNav;
