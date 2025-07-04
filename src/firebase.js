// src/firebase.js
import { initializeApp } from "firebase/app";
import { getFirestore } from "firebase/firestore";

const firebaseConfig = {
  apiKey: "AIzaSyDb386zNhseuqEBdmPlj1KMoHLwgHueS78",
  authDomain: "soccer-trivia-app-39f82.firebaseapp.com",
  projectId: "soccer-trivia-app-39f82",
  storageBucket: "soccer-trivia-app-39f82.firebasestorage.app",
  messagingSenderId: "468100308703",
  appId: "1:468100308703:web:884278e86847dd0663536a"
};

const app = initializeApp(firebaseConfig);
export const db = getFirestore(app);

