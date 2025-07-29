// src/utils/constants.js

export const CATEGORIES = [
  "International",
  "Domestic Leagues",
  "Transfers",
  "Time Periods",
  "Cup Competitions"
];

export const SUBCATEGORIES = {
  "International": ["All", "World Cup", "UEFA", "CONMEBOL", "CONCACAF", "CAF", "AFC", "OFC"],
  "Domestic Leagues": ["All", "Premier League", "La Liga", "Serie A", "Bundesliga", "Ligue 1", "MLS", "Rest of World"],
  "Transfers": ["All", "Transfer Fees", "Market Value", "Career Paths"],
  "Time Periods": ["All", "2020s", "2010s", "2000s", "1990s", "1980s", "1970s or Earlier"],
  "Cup Competitions": ["All", "FIFA Club World Cup", "UEFA Champions League", "UEFA Europa League", "UEFA Conference League", "Domestic Cups", "Continental Rest of World"]
};

export const NO_EASY_OR_HARD_MODE = [
  // International regions with only Default mode
  "CONCACAF", "CAF", "AFC", "OFC",

  // Domestic leagues with only Default mode
  "MLS", "Rest of World",

  // Historical time periods with only Default mode
  "2000s", "1990s", "1980s", "1970s or Earlier"
];
